from sqlmodel import Session, select
from datetime import datetime

from app.config.exceptions import NotFound
from app.logger import inventory_logger
from app.models.accession_jobs import AccessionJob
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.size_class import SizeClass
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.items import Item
from app.models.barcodes import Barcode
from app.models.workflows import Workflow
from app.database.session import commit_record
from app.schemas.verification_jobs import VerificationJobInput


def complete_accession_job(session, accession_job: AccessionJob, original_status):
    """
    Upon accession job completion:
        - Generate a related verification job
        - Associate accessioned entities to the new verification job
        - Set accessioned entity ownership to accession job owner
        - Updates accession job run time

    This task allows us to auto-create verification jobs in queue,
    and to support job ownership change efficiently.
    """
    # update accession job run_time and last_transition
    if original_status == "Running":
        time_difference = datetime.utcnow() - accession_job.last_transition
        accession_job.run_time += time_difference

    accession_job.last_transition = datetime.utcnow()
    commit_record(session, accession_job)

    verification_job_input = VerificationJobInput(
        accession_job_id=accession_job.id,
        workflow_id=accession_job.workflow_id,
        trayed=accession_job.trayed,
        owner_id=accession_job.owner_id,
        size_class_id=accession_job.size_class_id,
        media_type_id=accession_job.media_type_id,
        container_type_id=accession_job.container_type_id,
        user_id=accession_job.user_id,
        created_by_id=accession_job.created_by_id,
        status="Created",
    )

    new_verification_job = VerificationJob(**verification_job_input.model_dump())

    # Create a new verification job record
    new_verification_job = commit_record(session, new_verification_job)

    # Update Tray Records
    tray_query = select(Tray).where(Tray.accession_job_id == accession_job.id)
    trays = session.exec(tray_query)
    if trays:
        updated_trays = []
        new_verification_changes = []
        for tray in trays:
            tray.verification_job_id = new_verification_job.id
            tray.owner_id = accession_job.owner_id
            tray.scanned_for_accession = True
            updated_trays.append(tray)

            tray_barcode = session.get(Barcode, tray.barcode_id)
            items = tray.items
            for item in items:
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(VerificationChange(
                        workflow_id=accession_job.workflow_id,
                        tray_barcode_value=tray_barcode.value,
                        item_barcode_value=item_barcode.value,
                        change_type="Added",
                        completed_by_id=accession_job.user_id
                    ))

        session.add_all(updated_trays)
        session.add_all(new_verification_changes)

    # Update Non Tray Item Records
    non_tray_query = select(NonTrayItem).where(
        NonTrayItem.accession_job_id == accession_job.id
    )
    non_trays_items = session.exec(non_tray_query)
    if non_trays_items:
        updated_non_trays_items = []
        new_verification_changes = []
        for non_tray_item in non_trays_items:
            non_tray_item.verification_job_id = new_verification_job.id
            non_tray_item.owner_id = accession_job.owner_id
            non_tray_item.scanned_for_accession = True
            updated_non_trays_items.append(non_tray_item)

            item_barcode = session.get(Barcode, non_tray_item.barcode_id)
            new_verification_changes.append(VerificationChange(
                workflow_id=accession_job.workflow_id,
                item_barcode_value=item_barcode.value,
                change_type="Added",
                completed_by_id=accession_job.user_id
            ))

        session.add_all(updated_non_trays_items)
        session.add_all(new_verification_changes)

    # Update Item Records
    item_query = select(Item).where(Item.accession_job_id == accession_job.id)
    items = session.exec(item_query)
    if items:
        updated_items = []
        for item in items:
            item.verification_job_id = new_verification_job.id
            item.owner_id = accession_job.owner_id
            item.scanned_for_accession = True
            updated_items.append(item)

        session.add_all(updated_items)

    session.commit()


def complete_verification_job(session, verification_job: VerificationJob):
    """
    Upon verification job completion:
        - Set verification entity ownership to verification job owner

    This task allows us to support job ownership change efficiently.
    """
    # Update Tray Records
    tray_query = select(Tray).where(Tray.verification_job_id == verification_job.id)
    trays = session.exec(tray_query)
    if trays:
        for tray in trays:
            tray.owner_id = verification_job.owner_id
            session.add(tray)

    # Update Non Tray Item Records
    non_tray_query = select(NonTrayItem).where(
        NonTrayItem.verification_job_id == verification_job.id
    )
    non_trays_items = session.exec(non_tray_query)
    if non_trays_items:
        for non_tray_item in non_trays_items:
            non_tray_item.owner_id = verification_job.owner_id
            session.add(non_tray_item)

    # Update Item Records
    item_query = select(Item).where(Item.verification_job_id == verification_job.id)
    items = session.exec(item_query)
    if items:
        for item in items:
            item.owner_id = verification_job.owner_id
            session.add(item)

    session.commit()
    # session.refresh()


def manage_accession_job_transition(
    session, accession_job: AccessionJob, original_status
):
    """
    Task manages transition logic for an accession job's running state.
        - updates run_time
        - tracks last_transition
        - If job cancelled, rolls back accessioned entities
        - Rolls back barcodes used by deleted entities
    """
    # Compute time delta before changing last_transition
    if original_status == "Running":
        if accession_job.status != "Running":
            # calc time delta last transition to now
            time_difference = datetime.utcnow() - accession_job.last_transition
            accession_job.run_time += time_difference
    # update last_transition
    if original_status != accession_job.status:
        accession_job.last_transition = datetime.utcnow()
    commit_record(session, accession_job)

    if accession_job.status == "Cancelled":
        defunct_barcodes = []

        # Delete Accessioned Items
        item_query = select(Item).where(Item.accession_job_id == accession_job.id)
        items = session.exec(item_query)
        if items:
            for item in items:
                defunct_barcodes.append(item.barcode_id)
                session.delete(item)
        # Delete Accessioned Trays
        tray_query = select(Tray).where(Tray.accession_job_id == accession_job.id)
        trays = session.exec(tray_query)
        if trays:
            for tray in trays:
                defunct_barcodes.append(tray.barcode_id)
                session.delete(tray)
        # Delete Accessioned Non-Trays
        non_tray_query = select(NonTrayItem).where(
            NonTrayItem.accession_job_id == accession_job.id
        )
        non_trays_items = session.exec(non_tray_query)
        if non_trays_items:
            for non_tray_item in non_trays_items:
                defunct_barcodes.append(non_tray_item.barcode_id)
                session.delete(non_tray_item)

        # clear unused barcodes
        for barcode_id in defunct_barcodes:
            barcode_query = select(Barcode).where(Barcode.id == barcode_id)
            barcode = session.exec(barcode_query).first()
            session.delete(barcode)

    session.commit()
    session.refresh()


def manage_verification_job_transition(
    session, verification_job: VerificationJob, original_status
):
    """
    Task manages transition logic for an verification job's running state.
        - updates run_time
        - tracks last_transition

    Verification jobs do not get cancelled, so no item rollback needed.
    """
    # Compute time delta before changing last_transition
    if original_status == "Running":
        if verification_job.status != "Running":
            # calc time delta last transition to now
            time_difference = datetime.utcnow() - verification_job.last_transition
            verification_job.run_time += time_difference
    # update last_transition
    if original_status != verification_job.status:
        verification_job.last_transition = datetime.utcnow()
    commit_record(session, verification_job)

def process_tray_item_move(
    session: Session, item: Item, source_tray: Tray, destination_tray: Tray
):
    """
    Task processes a tray item move
    """
    # Move the item to the destination tray and update the tray
    item.tray_id = destination_tray.id
    item.size_class_id = destination_tray.size_class_id
    item.owner_id = destination_tray.owner_id
    item.media_type_id = destination_tray.media_type_id
    item.accession_job_id = destination_tray.accession_job_id
    item.accession_dt = destination_tray.accession_dt
    item.verification_job_id = destination_tray.verification_job_id

    # update update_dt fields
    update_dt = datetime.utcnow()
    item.update_dt = update_dt
    destination_tray.update_dt = update_dt

    session.add(item)
    session.add(destination_tray)
    session.commit()
    session.refresh(item)
    session.refresh(source_tray)

    # check if tray is empty if it is empty, withdraw the tray
    updated_source_tray = session.query(Tray).filter(Tray.id == source_tray.id).first()

    if updated_source_tray and len(updated_source_tray.items) == 0:
        session.query(Barcode).filter(Barcode.id == source_tray.barcode_id).update(
            {"Withdrawn": True, "update_dt": update_dt},
            synchronize_session=False,
        )
        session.query(Tray).filter(Tray.id == source_tray.id).update(
            {
                "shelf_position_id": None,
                "shelf_position_proposed_id": None,
                "withdrawal_dt": update_dt,
                "withdrawn_barcode_id": source_tray.barcode_id,
                "barcode_id": None,
                "update_dt": update_dt
            }
        )

        source_shelf = (
            session.query(Shelf)
            .join(ShelfPosition, Shelf.id == ShelfPosition.shelf_id)
            .filter(ShelfPosition.id == source_tray.shelf_position_id)
            .first()
        )

        if source_shelf:
            session.query(Shelf).filter(Shelf.id == source_shelf.id).update(
                {"available_space": source_shelf.available_space + 1}
            )

        session.commit()


def process_tray_move(session: Session, tray: Tray, source_shelf: Shelf,
                      destination_shelf: Shelf, destination_shelf_position_id: int):
    """
    Task processes a tray move between shelves
    """
    update_dt = datetime.utcnow()
    tray.shelf_position_id = destination_shelf_position_id
    tray.update_dt = update_dt
    session.commit()
    session.refresh(tray)


def process_non_tray_item_move(session: Session, non_tray_item: NonTrayItem, source_shelf: Shelf,
                      destination_shelf: Shelf, destination_shelf_position_id: int):
    """
    Task processes a non tray item move between shelves
    """
    update_dt = datetime.utcnow()
    non_tray_item.shelf_position_id = destination_shelf_position_id
    non_tray_item.update_dt = update_dt
    session.commit()
    session.refresh(non_tray_item)
    return non_tray_item


def manage_verification_job_change_action(session: Session, verification_job: VerificationJob, update_input: str, value: int):
    new_verification_changes = []

    trays = verification_job.trays
    items = verification_job.items
    non_tray_items = verification_job.non_tray_items

    if trays:
        for tray in trays:
            barcode = session.query(Barcode).filter(
                Barcode.id == tray.barcode_id
            ).first()
            if update_input == "media_type_id":
                session.query(Tray).filter(Tray.id == tray.id).update({update_input: value})
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        tray_barcode_value=barcode.value,
                        change_type="MediaTypeEdit",
                        completed_by_id=verification_job.user_id
                    )
                )
            if update_input == "size_class_id":
                session.query(Tray).filter(Tray.id == tray.id).update({update_input: value})
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        tray_barcode_value=barcode.value,
                        change_type="SizeClassEdit",
                        completed_by_id=verification_job.user_id
                    )
                )
    if items:
        for item in items:
            barcode = session.query(Barcode).filter(
                Barcode.id == item.barcode_id
            )
            if update_input == "media_type_id":
                session.query(Item).filter(Item.id == item.id).update({update_input: value})
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        item_barcode_value=barcode.value,
                        change_type="MediaTypeEdit",
                        completed_by_id=verification_job.user_id
                    )
                )
            if update_input == "size_class_id":
                session.query(Item).filter(Item.id == item.id).update({update_input: value})
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        item_barcode_value=barcode.value,
                        change_type="SizeClassEdit",
                        completed_by_id=verification_job.user_id
                    )
                )
    if non_tray_items:
        for non_tray_item in non_tray_items:
            barcode = session.query(Barcode).filter(
                Barcode.id == non_tray_item.barcode_id
            )
            if update_input == "media_type_id":
                session.query(NonTrayItem).filter(
                    NonTrayItem.id == non_tray_item.id
                    ).update({update_input: value})
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        non_tray_item_barcode_value=barcode.value,
                        change_type="MediaTypeEdit",
                        completed_by_id=verification_job.user_id
                    )
                )
            if update_input == "size_class_id":
                session.query(NonTrayItem).filter(
                    NonTrayItem.id == non_tray_item.id
                    ).update({update_input: value})
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        non_tray_item_barcode_value=barcode.value,
                        change_type="SizeClassEdit",
                        completed_by_id=verification_job.user_id
                    )
                )
