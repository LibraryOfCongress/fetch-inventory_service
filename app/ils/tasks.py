import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.logger import inventory_logger
from app.models.owners import Owner
from app.models.buildings import Building
from app.models.building_ils_service_points import BuildingILSServicePoint
from app.models.ils_configurations import ILSConfiguration
from app.models.items import Item, ILSSyncState
from app.models.non_tray_items import NonTrayItem
from app.models.ils_sync_errors import ILSSyncError, WorkflowActionEnum, ILSSyncStatusEnum
from app.database.session import session_manager
from app.ils.factory import get_ils_adapter


def _resolve_building_service_point(
    session: Session, building_id: Optional[int], ils_configuration_id: Optional[uuid.UUID]
) -> Optional[str]:
    """
    Looks up the FOLIO service point mapped to this physical Building for
    this specific ILSConfiguration, if any. Used to override that
    ILSConfiguration's single Owner-level default service point for instances
    where there are multiple buildings and/or multiple ILS integrations.
    """
    if not building_id or not ils_configuration_id:
        return None
    mapping = session.execute(
        select(BuildingILSServicePoint).filter_by(
            building_id=building_id, ils_configuration_id=ils_configuration_id
        )
    ).scalars().first()
    return mapping.ils_service_point_id if mapping else None

def validate_accessioned_item_async(barcode_value: str, owner_id: int, is_non_tray: bool = False):
    """
    Background worker task to validate an accessioned item's barcode against the
    Owner's configured ILS. Follows the BaseILSAdapter contract.
    If the ILS returns False, tracks the error in the ILSSyncError table.
    """
    with session_manager() as session:
        owner = session.get(Owner, owner_id)
        if not owner:
             inventory_logger.error(f"Cannot validate item {barcode_value}: Owner {owner_id} not found.")
             return

        # Phase 1 setup guaranteed an ILS Configuration resolver on Owner if inherited
        config_id = owner.resolved_ils_configuration_id
        if not config_id:
             return # No integration configured, skip
            
        config = session.get(ILSConfiguration, config_id)
        if not config or not config.is_active or not config.enable_accession_hook:
             return # Not active for this hook
             
        try:
             # Instantiate our adapter via Factory
             adapter = get_ils_adapter(config)
             
             # Call the contract
             is_valid = adapter.validate_item(barcode_value)
             
             # Find our targeted entity based on the scanner context
             model_class = NonTrayItem if is_non_tray else Item
             
             # Locate target record to update sync state
             from app.models.barcodes import Barcode
             record = session.execute(
                 select(model_class).join(Barcode, model_class.barcode_id == Barcode.id)
                 .filter(Barcode.value == barcode_value)
             ).scalars().first()
             
             if not record:
                  inventory_logger.error(f"Failed to locate internal record for accession validation. Barcode: {barcode_value}")
                  return
             
             if is_valid:
                 # Update state to SYNCED
                 record.ils_sync_state = ILSSyncState.IN_SYNC
                 session.add(record)
                 session.commit()
             else:
                 # Update state to ERROR
                 record.ils_sync_state = ILSSyncState.SYNC_ERROR
                 session.add(record)
                 
                 # Create ILSSyncError log for the dashboard
                 error_log = ILSSyncError(
                     workflow_action=WorkflowActionEnum.ACCESSION,
                     item_barcode=barcode_value,
                     error_message=f"ILS reported barcode {barcode_value} is invalid or not mapped to this location.",
                     status=ILSSyncStatusEnum.ACTIVE
                 )
                 session.add(error_log)
                 session.commit()
                 
                 inventory_logger.warning(f"ILS Validation failed for Accession on Barcode: {barcode_value}")

        except Exception as e:
             inventory_logger.error(f"Critical Adapter Exception during Accession Validation for {barcode_value}: {str(e)}")
             # It might be wise to set a SYNC_ERROR state here as well if the API crashed
             # leaving that for Phase 3 error dashboard expansion if needed.
             pass

def validate_accession_job_batch(session: Session, accession_job) -> None:
    owner = session.get(Owner, accession_job.owner_id)
    if not owner:
        inventory_logger.error(
            f"Cannot batch-validate Accession Job {accession_job.id}: Owner "
            f"{accession_job.owner_id} not found."
        )
        return

    config_id = owner.resolved_ils_configuration_id
    inventory_logger.info(
        f"Accession Job {accession_job.id}: Owner {owner.id} resolved ILS "
        f"configuration = {config_id or 'None'}."
    )
    if not config_id:
        return  # No ILS configuration for this Owner (or its parent chain)

    config = session.get(ILSConfiguration, config_id)
    inventory_logger.info(
        f"Accession Job {accession_job.id}: ILSConfiguration {config_id} "
        f"is_active={bool(config and config.is_active)}, "
        f"enable_accession_hook={bool(config and config.enable_accession_hook)}."
    )
    if not config or not config.is_active or not config.enable_accession_hook:
        return  # ILS integration, or "Enable Accession Sync" specifically, is off

    records = list(accession_job.items) + list(accession_job.non_tray_items)
    records_by_barcode = {record.barcode.value: record for record in records if record.barcode}
    if not records_by_barcode:
        return

    try:
        adapter = get_ils_adapter(config)
        inventory_logger.info(
            f"Accession Job {accession_job.id}: performing ILS lookup "
            f"(validate_items_batch) for {len(records_by_barcode)} barcode(s) via "
            f"ILSConfiguration '{config.name}' ({type(adapter).__name__})."
        )
        results = adapter.validate_items_batch(list(records_by_barcode.keys()))
        inventory_logger.info(
            f"Accession Job {accession_job.id}: ILS lookup completed, "
            f"{sum(1 for v in results.values() if v)}/{len(results)} barcode(s) valid."
        )
    except Exception as e:
        inventory_logger.error(
            f"Critical Adapter Exception during Accession Job {accession_job.id} batch "
            f"validation: {str(e)}"
        )
        return

    for barcode_value, record in records_by_barcode.items():
        if results.get(barcode_value):
            record.ils_sync_state = ILSSyncState.IN_SYNC
            session.add(record)
        else:
            record.ils_sync_state = ILSSyncState.SYNC_ERROR
            session.add(record)
            session.add(ILSSyncError(
                workflow_action=WorkflowActionEnum.ACCESSION,
                item_barcode=barcode_value,
                error_message=f"ILS reported barcode {barcode_value} is invalid or not mapped to this location.",
                status=ILSSyncStatusEnum.ACTIVE,
            ))
            inventory_logger.warning(
                f"ILS Validation failed for Accession Job {accession_job.id} on Barcode: {barcode_value}"
            )

    session.commit()

def check_in_shelved_item_async(barcode_value: str, owner_id: int, is_non_tray: bool = False, shelving_job_id: int = None):
    """
    Background worker task to check in an item that was successfully shelved.
    """
    with session_manager() as session:
        owner = session.get(Owner, owner_id)
        if not owner:
             return

        config_id = owner.resolved_ils_configuration_id
        if not config_id: return
            
        config = session.get(ILSConfiguration, config_id)
        if not config or not config.is_active or not config.enable_shelving_hook:
             return
             
        try:
             from app.models.shelving_jobs import ShelvingJob
             building_id = None
             if shelving_job_id:
                 shelving_job = session.get(ShelvingJob, shelving_job_id)
                 building_id = shelving_job.building_id if shelving_job else None
             service_point_override = _resolve_building_service_point(session, building_id, config.id)

             adapter = get_ils_adapter(config)
             check_in_resp = adapter.check_in_item(barcode_value, service_point_override=service_point_override)

             model_class = NonTrayItem if is_non_tray else Item
             from app.models.barcodes import Barcode
             record = session.execute(
                 select(model_class).join(Barcode, model_class.barcode_id == Barcode.id)
                 .filter(Barcode.value == barcode_value)
             ).scalars().first()

             if not record: return

             if check_in_resp.success and check_in_resp.raw_status_string.strip().lower() == config.expected_shelved_status.strip().lower():
                 record.ils_sync_state = ILSSyncState.IN_SYNC
                 session.add(record)
             else:
                 record.ils_sync_state = ILSSyncState.SYNC_ERROR
                 session.add(record)
                 
                 error_msg = f"ILS reported barcode {barcode_value} is invalid or has wrong status '{check_in_resp.raw_status_string}'."
                 if not check_in_resp.success:
                     error_msg = f"ILS Check-In Failed entirely for {barcode_value}: {check_in_resp.error_message}"
                     
                 error_log = ILSSyncError(
                     workflow_action=WorkflowActionEnum.SHELVING,
                     item_barcode=barcode_value,
                     error_message=error_msg,
                     status=ILSSyncStatusEnum.ACTIVE
                 )
                 session.add(error_log)
                 
             session.commit()

        except Exception as e:
             inventory_logger.error(f"Critical Adapter Exception during Shelving validation for {barcode_value}: {str(e)}")

def check_in_picklist_item_async(barcode_value: str, owner_id: int, is_non_tray: bool = False, pick_list_id: int = None):
    """
    Background worker task to check in an item that was successfully picked from the shelf.
    """
    with session_manager() as session:
        owner = session.get(Owner, owner_id)
        if not owner:
             return

        config_id = owner.resolved_ils_configuration_id
        if not config_id: return
            
        config = session.get(ILSConfiguration, config_id)
        if not config or not config.is_active or not config.enable_picklist_hook:
             return
             
        try:
             from app.models.pick_lists import PickList
             building_id = None
             if pick_list_id:
                 pick_list = session.get(PickList, pick_list_id)
                 building_id = pick_list.building_id if pick_list else None
             service_point_override = _resolve_building_service_point(session, building_id, config.id)

             adapter = get_ils_adapter(config)
             check_in_resp = adapter.check_in_item(barcode_value, service_point_override=service_point_override)

             model_class = NonTrayItem if is_non_tray else Item
             from app.models.barcodes import Barcode
             record = session.execute(
                 select(model_class).join(Barcode, model_class.barcode_id == Barcode.id)
                 .filter(Barcode.value == barcode_value)
             ).scalars().first()

             if not record: return

             if check_in_resp.success and check_in_resp.raw_status_string.strip().lower() == config.expected_picklist_status.strip().lower():
                 record.ils_sync_state = ILSSyncState.IN_SYNC
                 session.add(record)
             else:
                 record.ils_sync_state = ILSSyncState.SYNC_ERROR
                 session.add(record)
                 
                 error_msg = f"ILS reported barcode {barcode_value} has wrong status '{check_in_resp.raw_status_string}'."
                 if not check_in_resp.success:
                     error_msg = f"ILS Check-In Failed entirely for Picklist item {barcode_value}: {check_in_resp.error_message}"
                     
                 error_log = ILSSyncError(
                     workflow_action=WorkflowActionEnum.PICKLIST,
                     item_barcode=barcode_value,
                     error_message=error_msg,
                     status=ILSSyncStatusEnum.ACTIVE
                 )
                 session.add(error_log)
                 
             session.commit()

        except Exception as e:
             inventory_logger.error(f"Critical Adapter Exception during Picklist check-in for {barcode_value}: {str(e)}")

def sync_requests_async(config_id: uuid.UUID):
    """
    Background worker task to poll an ILS for pending requests and ingest
    them into the FETCH ecosystem.
    """
    inventory_logger.info(f"Starting async request sync for ILS Configuration: {config_id}")
    with session_manager() as session:
        config = session.get(ILSConfiguration, config_id)
        if not config or not config.is_active or not config.enable_requests_hook:
            inventory_logger.warning("Aborted sync_requests_async: Configuration not found or inactive.")
            return
            
        try:
             from app.models.delivery_locations import DeliveryLocation
             from app.models.requests import Request
             
             adapter = get_ils_adapter(config)
             ils_requests = adapter.fetch_pending_requests()
             
             if not ils_requests: return
             
             # Fallback default delivery location if mapping fails
             default_delivery_location = session.execute(
                 select(DeliveryLocation).limit(1)
             ).scalars().first()
             
             for ils_req in ils_requests:
                 # See if request already exists based on external_request_id
                 existing_req = session.execute(
                     select(Request).filter(Request.external_request_id == ils_req.request_id)
                 ).scalars().first()
                 
                 if existing_req:
                     continue # Already synced
                     
                 # Map Barcode
                 from app.models.barcodes import Barcode
                 barcode_obj = session.execute(
                     select(Barcode).where(Barcode.value == ils_req.item_barcode)
                 ).scalars().first()
                 
                 if not barcode_obj:
                     # Log sync error: missing barcode
                     error_log = ILSSyncError(
                         workflow_action=WorkflowActionEnum.REQUEST_SYNC,
                         item_barcode=ils_req.item_barcode,
                         error_message=f"ILS requested item {ils_req.item_barcode} but it is not accessioned in FETCH.",
                         status=ILSSyncStatusEnum.ACTIVE
                     )
                     session.add(error_log)
                     continue
                     
                 # Map to Item or NonTrayItem
                 item = session.execute(select(Item).where(Item.barcode_id == barcode_obj.id)).scalars().first()
                 non_tray_item = session.execute(select(NonTrayItem).where(NonTrayItem.barcode_id == barcode_obj.id)).scalars().first()
                 
                 # Map Delivery Location loosely based on destination string
                 # (in a real app this might use a mapping table, here we try a soft text match or default)
                 delivery_loc = session.execute(
                     select(DeliveryLocation).filter(DeliveryLocation.name.ilike(f"%{ils_req.destination}%"))
                 ).scalars().first()
                 
                 if not delivery_loc:
                     delivery_loc = default_delivery_location
                     
                 new_request = Request(
                     external_request_id=ils_req.request_id,
                     requestor_name=f"ILS Patron {ils_req.patron_id}",
                     delivery_location_id=delivery_loc.id if delivery_loc else None,
                     item_id=item.id if item else None,
                     non_tray_item_id=non_tray_item.id if non_tray_item else None,
                     status="New"
                 )
                 session.add(new_request)
                 
             session.commit()
             inventory_logger.info(f"Completed async request sync for ILS Configuration: {config_id}")
             
        except Exception as e:
             inventory_logger.error(f"Critical Adapter Exception during Request Sync for {config_id}: {str(e)}")

