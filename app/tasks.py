# /code/app/tasks.py - FINAL DEBUG VERSION

import time

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from sqlalchemy.exc import OperationalError
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any
import traceback # Added for debugging

from app.config.exceptions import NotFound
from app.logger import inventory_logger


_BG_RETRY_MAX_ATTEMPTS = 3
_BG_RETRY_BACKOFF_SEC = 2
from app.events import update_shelf_space_after_tray, update_shelf_space_after_non_tray
from app.models.accession_jobs import AccessionJob
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.shelving_jobs import ShelvingJob
from app.models.shelves import Shelf
from app.models.size_class import SizeClass
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.models.trays import Tray
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem, NonTrayItemStatus
from app.models.items import Item, ItemStatus
from app.models.barcodes import Barcode
from app.models.workflows import Workflow
from app.database.session import commit_record, session_manager
from app.schemas.verification_jobs import VerificationJobInput
from app.utilities import start_session_with_audit_info
from app.services.audit_service import log_audit_event, AuditEventType
from app.ils.tasks import check_in_shelved_item_async, validate_accession_job_batch


def complete_accession_job(accession_job_id: int, original_status: str, audit_info: dict):
    """
    Upon accession job completion:
        - Generate a related verification job
        - Associate accessioned entities to the new verification job
        - Set accessioned entity ownership to accession job owner
        - Updates accession job run time

    Retries on transient DB connection failures (SQLAlchemy OperationalError,
    e.g. an SSL connection drop) by re-running the whole operation. Each attempt
    re-fetches the AJ, and verification-job creation is guarded by an existence
    check, so a retry will not double-create. (FETCH-1619, re-applied on the
    community-edition implementation.)
    """
    last_exc = None
    for attempt in range(1, _BG_RETRY_MAX_ATTEMPTS + 1):
        try:
            _complete_accession_job_once(accession_job_id, original_status, audit_info)
            return
        except OperationalError as e:
            last_exc = e
            inventory_logger.warning(
                f"complete_accession_job: AJ {accession_job_id} attempt "
                f"{attempt}/{_BG_RETRY_MAX_ATTEMPTS} failed with OperationalError: {e}"
            )
            if attempt < _BG_RETRY_MAX_ATTEMPTS:
                time.sleep(_BG_RETRY_BACKOFF_SEC * attempt)

    inventory_logger.error(
        f"complete_accession_job: AJ {accession_job_id} exhausted "
        f"{_BG_RETRY_MAX_ATTEMPTS} retries; verification job not created. "
        f"Last error: {last_exc}"
    )


def _complete_accession_job_once(accession_job_id: int, original_status: str, audit_info: dict):
    """One attempt of complete_accession_job. Re-fetches the AJ in this session
    so the attempt does not depend on detached/stale in-memory state. Transient
    DB errors (OperationalError) propagate so the wrapper can retry; any other
    error is logged and swallowed as before."""
    print(f"--- STARTING BACKGROUND TASK: Complete Accession Job {accession_job_id} ---")
    try:
        with session_manager() as session:
            start_session_with_audit_info(audit_info, session)

            # Re-fetch the object
            accession_job = session.get(AccessionJob, accession_job_id)
            if not accession_job:
                inventory_logger.error(f"Background Task Error: AccessionJob {accession_job_id} not found.")
                return

            # Update run_time
            if original_status == "Running":
                if accession_job.last_transition:
                    time_difference = datetime.now(timezone.utc) - accession_job.last_transition
                    accession_job.run_time += time_difference

            accession_job.last_transition = datetime.now(timezone.utc)
            commit_record(session, accession_job)

            # Check if Verification Job already exists for a given accession job
            existing_verification_job_query = select(VerificationJob).where(
                VerificationJob.accession_job_id == accession_job.id
            )
            existing_verification_job = session.execute(existing_verification_job_query).scalars().first()
            
            if existing_verification_job:
               inventory_logger.warning(
                   f"Verification Job already exists for Accession Job {accession_job.id}. Skipping creation."
               )
               return

            validate_accession_job_batch(session, accession_job)

            # Create Verification Job
            verification_job_input = VerificationJobInput(
                accession_job_id=accession_job.id,
                workflow_id=accession_job.workflow_id,
                trayed=accession_job.trayed,
                owner_id=accession_job.owner_id,
                size_class_id=accession_job.size_class_id,
                media_type_id=accession_job.media_type_id,
                container_type_id=accession_job.container_type_id,
                assigned_user_id=None,
                created_by_id=accession_job.created_by_id,
                status="Created",
            )

            # Dump model to dict
            vj_data = verification_job_input.model_dump()
            
            # Create Model
            new_verification_job = VerificationJob(**vj_data)
            
            # Commit Verification Job
            new_verification_job = commit_record(session, new_verification_job)
            print(f"--- Verification Job Created: ID {new_verification_job.id} ---")

            # Update Tray Records
            tray_query = select(Tray).where(Tray.accession_job_id == accession_job.id)
            trays = session.execute(tray_query).scalars().all()
            
            if trays:
                for tray in trays:
                    tray.verification_job_id = new_verification_job.id
                    tray.owner_id = accession_job.owner_id
                    tray.scanned_for_accession = True
                    session.add(tray)

            # Update Non Tray Item Records
            non_tray_query = select(NonTrayItem).where(
                NonTrayItem.accession_job_id == accession_job.id
            )
            non_trays_items = session.execute(non_tray_query).scalars().all()
            
            if non_trays_items:
                for non_tray_item in non_trays_items:
                    non_tray_item.verification_job_id = new_verification_job.id
                    non_tray_item.owner_id = accession_job.owner_id
                    non_tray_item.scanned_for_accession = True
                    session.add(non_tray_item)

            # Update Item Records
            item_query = select(Item).where(Item.accession_job_id == accession_job.id)
            items = session.execute(item_query).scalars().all()
            
            if items:
                for item in items:
                    item.verification_job_id = new_verification_job.id
                    item.owner_id = accession_job.owner_id
                    item.scanned_for_accession = True
                    session.add(item)

            session.commit()

            log_audit_event(
                session,
                AuditEventType.JOB_COMPLETED,
                f"Accession Job {accession_job_id} completed — Verification Job {new_verification_job.id} auto-created",
                job_type="accession_jobs",
                job_id=accession_job_id,
            )
            session.commit()

            print(f"--- BACKGROUND TASK COMPLETE: Accession Job {accession_job_id} ---")

    except OperationalError:
        # Transient DB connection failure (e.g. SSL drop) -- let it propagate so
        # complete_accession_job's retry loop can re-run this attempt.
        raise
    except Exception as e:
        # This will print the exact error to your Docker logs
        print(f"CRITICAL ERROR IN BACKGROUND TASK: {str(e)}")
        print(traceback.format_exc())
        inventory_logger.error(f"Error completing accession job {accession_job_id}: {e}")


def complete_verification_job(verification_job_id: int, original_status: str, audit_info: dict):
    # Updated to accept ID for safety, though VJ completion is less complex usually
    try:
        with session_manager() as session:
            start_session_with_audit_info(audit_info, session)

            verification_job = session.get(VerificationJob, verification_job_id)
            if not verification_job:
                 return

            # FETCH-1628: accumulate run_time when leaving a Running state, mirroring
            # complete_accession_job (verification jobs weren't timing correctly).
            if original_status == "Running":
                if verification_job.last_transition:
                    time_difference = datetime.now(timezone.utc) - verification_job.last_transition
                    if verification_job.run_time is None:
                        verification_job.run_time = timedelta(0)
                    verification_job.run_time += time_difference

            verification_job.last_transition = datetime.now(timezone.utc)
            session.add(verification_job)

            tray_query = select(Tray).where(Tray.verification_job_id == verification_job.id)
            trays = session.execute(tray_query).scalars().all()
            if trays:
                for tray in trays:
                    tray.owner_id = verification_job.owner_id
                    session.add(tray)

            non_tray_query = select(NonTrayItem).where(
                NonTrayItem.verification_job_id == verification_job.id
            )
            non_trays_items = session.execute(non_tray_query).scalars().all()
            if non_trays_items:
                for non_tray_item in non_trays_items:
                    non_tray_item.owner_id = verification_job.owner_id
                    if non_tray_item.status == NonTrayItemStatus.Accessioned:
                         non_tray_item.status = NonTrayItemStatus.Verified
                    session.add(non_tray_item)

            item_query = select(Item).where(Item.verification_job_id == verification_job.id)
            items = session.execute(item_query).scalars().all()
            if items:
                for item in items:
                    item.owner_id = verification_job.owner_id
                    if item.status == ItemStatus.Accessioned:
                         item.status = ItemStatus.Verified
                    session.add(item)

            session.commit()

            log_audit_event(
                session,
                AuditEventType.JOB_COMPLETED,
                f"Verification Job {verification_job_id} completed",
                job_type="verification_jobs",
                job_id=verification_job_id,
            )
            session.commit()
    except Exception as e:
        inventory_logger.error(f"Error in complete_verification_job: {e}")


def manage_accession_job_transition(
    accession_job_id: int, original_status: str, audit_info: dict
):
    try:
        with session_manager() as session:
            start_session_with_audit_info(audit_info, session)
            
            accession_job = session.get(AccessionJob, accession_job_id)
            if not accession_job:
                return

            if original_status == "Running":
                if accession_job.status != "Running":
                    if accession_job.last_transition:
                        time_difference = datetime.now(timezone.utc) - accession_job.last_transition
                        accession_job.run_time += time_difference
            
            if original_status != accession_job.status:
                accession_job.last_transition = datetime.now(timezone.utc)

            commit_record(session, accession_job)

            if accession_job.status == "Cancelled":
                defunct_barcodes = []

                # Delete Accessioned Items
                item_query = select(Item).where(Item.accession_job_id == accession_job.id)
                items = session.execute(item_query).scalars().all()
                if items:
                    for item in items:
                        defunct_barcodes.append(item.barcode_id)
                        session.delete(item)
                
                # Delete Accessioned Trays
                tray_query = select(Tray).where(Tray.accession_job_id == accession_job.id)
                trays = session.execute(tray_query).scalars().all()
                if trays:
                    for tray in trays:
                        defunct_barcodes.append(tray.barcode_id)
                        session.delete(tray)
                
                # Delete Accessioned Non-Trays
                non_tray_query = select(NonTrayItem).where(
                    NonTrayItem.accession_job_id == accession_job.id
                )
                non_trays_items = session.execute(non_tray_query).scalars().all()
                if non_trays_items:
                    for non_tray_item in non_trays_items:
                        defunct_barcodes.append(non_tray_item.barcode_id)
                        session.delete(non_tray_item)

                for barcode_id in defunct_barcodes:
                    barcode_query = select(Barcode).where(Barcode.id == barcode_id)
                    barcode = session.execute(barcode_query).scalars().first()
                    if barcode:
                        session.delete(barcode)

            if accession_job.status == "Cancelled":
                log_audit_event(
                    session,
                    AuditEventType.JOB_CANCELLED,
                    f"Accession Job {accession_job_id} cancelled — entities deleted",
                    job_type="accession_jobs",
                    job_id=accession_job_id,
                )

            session.commit()
    except Exception as e:
        print(f"Error in manage_accession_job_transition: {e}")


def manage_verification_job_transition(verification_job_id: int, original_status: str, audit_info: dict):
    # Updated to take ID
    try:
        with session_manager() as session:
            start_session_with_audit_info(audit_info, session)
            
            verification_job = session.get(VerificationJob, verification_job_id)
            if not verification_job:
                return

            if original_status == "Running":
                if verification_job.status != "Running":
                    time_difference = datetime.now(timezone.utc) - verification_job.last_transition
                    verification_job.run_time += time_difference
            if original_status != verification_job.status:
                verification_job.last_transition = datetime.now(timezone.utc)
            commit_record(session, verification_job)
    except Exception as e:
        print(f"Error in manage_verification_job_transition: {e}")


def process_tray_item_move(item: Item, source_tray: Tray, destination_tray: Tray):
    # NOTE: This function needs IDs passed to be fully safe in background tasks,
    # but for now we wrap it to prevent crashes.
    try:
        with session_manager() as session:
            # Re-attach objects to this session if possible, or assume they are passed from a valid context
            # Better approach: Fetch by ID. For now, we assume simple property access works or refactor logic.
            # To fix the "detached instance" error, we really need the IDs.
            # Assuming these are passed as objects from the main thread, they are detached.
            # We need to merge them or fetch them.
            
            # Proper fix: Use IDs. But without changing signature in router, we try merge.
            item = session.merge(item)
            source_tray = session.merge(source_tray)
            destination_tray = session.merge(destination_tray)

            item.tray_id = destination_tray.id
            item.size_class_id = destination_tray.size_class_id
            item.owner_id = destination_tray.owner_id
            item.media_type_id = destination_tray.media_type_id
            item.accession_job_id = destination_tray.accession_job_id
            item.accession_dt = destination_tray.accession_dt
            item.verification_job_id = destination_tray.verification_job_id

            update_dt = datetime.now(timezone.utc)
            item.update_dt = update_dt
            destination_tray.update_dt = update_dt

            session.add(item)
            session.add(destination_tray)
            session.commit()

            session.refresh(source_tray)
            session.refresh(destination_tray)

            updated_source_tray = session.execute(
                select(Tray).filter(Tray.id == source_tray.id)
            ).scalars().first()

            if updated_source_tray and len(updated_source_tray.items) == 0:
                session.execute(
                    update(Barcode)
                    .where(Barcode.id == source_tray.barcode_id)
                    .values(withdrawn=True, update_dt=update_dt)
                )
                session.execute(
                    update(Tray)
                    .where(Tray.id == source_tray.id)
                    .values(
                        shelf_position_id=None,
                        shelf_position_proposed_id=None,
                        withdrawal_dt=update_dt,
                        withdrawn_barcode_id=source_tray.barcode_id,
                        barcode_id=None,
                        update_dt=update_dt
                    )
                )
            update_shelf_space_after_tray(
                session, destination_tray, destination_tray.shelf_position_id,
                source_tray.shelf_position_id
            )
            session.commit()
    except Exception as e:
        print(f"Error in process_tray_item_move: {e}")


def process_tray_move(session: Session, tray: Tray, source_shelf: Shelf,
                      destination_shelf: Shelf, destination_shelf_position_id: int):
    # This function takes a session, so it is likely called synchronously.
    # No changes needed if session is active.
    update_dt = datetime.now(timezone.utc)
    old_position_id = tray.shelf_position_id
    tray.shelf_position_id = destination_shelf_position_id
    tray.update_dt = update_dt
    session.add(tray)
    update_shelf_space_after_tray(session, tray, destination_shelf_position_id, old_position_id)
    session.commit()
    session.refresh(tray)


def process_non_tray_item_move(session: Session, non_tray_item: NonTrayItem, source_shelf: Shelf,
                      destination_shelf: Shelf, destination_shelf_position_id: int):
    # This function takes a session, so it is likely called synchronously.
    update_dt = datetime.now(timezone.utc)
    old_position_id = non_tray_item.shelf_position_id
    non_tray_item.shelf_position_id = destination_shelf_position_id
    non_tray_item.update_dt = update_dt
    session.add(non_tray_item)
    update_shelf_space_after_non_tray(session, non_tray_item, destination_shelf_position_id, old_position_id)
    session.commit()
    session.refresh(non_tray_item)
    return non_tray_item


def manage_verification_job_change_action(verification_job: VerificationJob, update_input: str, value: Any, audit_info: dict):
    # This function likely needs to handle detached instances if passed from background tasks.
    try:
        with session_manager() as session:
            start_session_with_audit_info(audit_info, session)
            
            # Re-fetch verification_job if possible, or merge
            verification_job = session.merge(verification_job)
            
            new_verification_changes = []

            trays = verification_job.trays
            items = verification_job.items
            non_tray_items = verification_job.non_tray_items

            if trays:
                for tray in trays:
                    session.execute(update(Tray).where(Tray.id == tray.id).values({update_input: value}))
                    tray_barcode = session.execute(
                        select(Barcode).filter(Barcode.id == tray.barcode_id)
                    ).scalars().first()
                    
                    for item in tray.items:
                        item_barcode = session.execute(
                            select(Barcode).filter(Barcode.id == item.barcode_id)
                        ).scalars().first()
                        change_type = "MediaTypeEdit" if update_input == "media_type_id" else "SizeClassEdit"
                        session.execute(
                            update(Item).where(Item.id == item.id).values({update_input: value})
                        )
                        new_verification_changes.append(
                            VerificationChange(
                                workflow_id=verification_job.workflow_id,
                                tray_barcode_value=tray_barcode.value,
                                item_barcode_value=item_barcode.value,
                                change_type=change_type,
                                completed_by_id=verification_job.assigned_user_id
                            )
                        )
            
            if items:
                for item in items:
                    item_barcode = session.execute(
                        select(Barcode).filter(Barcode.id == item.barcode_id)
                    ).scalars().first()
                    tray_barcode = session.execute(
                        select(Barcode).join(Tray).filter(Tray.id == item.tray_id)
                    ).scalars().first()
                    change_type = "MediaTypeEdit" if update_input == "media_type_id" else "SizeClassEdit"
                    session.execute(
                        update(Item).where(Item.id == item.id).values({update_input: value})
                    )
                    new_verification_changes.append(
                        VerificationChange(
                            workflow_id=verification_job.workflow_id,
                            tray_barcode_value=tray_barcode.value,
                            item_barcode_value=item_barcode.value,
                            change_type=change_type,
                            completed_by_id=verification_job.user_id
                        )
                    )

            if non_tray_items:
                for non_tray_item in non_tray_items:
                    item_barcode = session.execute(
                        select(Barcode).filter(Barcode.id == non_tray_item.barcode_id)
                    ).scalars().first()
                    change_type = "MediaTypeEdit" if update_input == "media_type_id" else "SizeClassEdit"
                    session.execute(
                        update(NonTrayItem).where(NonTrayItem.id == non_tray_item.id).values({update_input: value})
                    )
                    new_verification_changes.append(
                        VerificationChange(
                            workflow_id=verification_job.workflow_id,
                            item_barcode_value=item_barcode.value,
                            change_type=change_type,
                            completed_by_id=verification_job.user_id
                        )
                    )

            if new_verification_changes:
                session.add_all(new_verification_changes)
            
            session.commit()
    except Exception as e:
        print(f"Error in manage_verification_job_change_action: {e}")


def manage_verification_job_transition(verification_job: VerificationJob, original_status: str, audit_info: dict):
    with session_manager() as session:
        start_session_with_audit_info(audit_info, session)
        if original_status == "Running":
            if verification_job.status != "Running":
                time_difference = datetime.now(timezone.utc) - verification_job.last_transition
                verification_job.run_time += time_difference
        if original_status != verification_job.status:
            verification_job.last_transition = datetime.now(timezone.utc)
        commit_record(session, verification_job)


def process_tray_item_move(item: Item, source_tray: Tray, destination_tray: Tray):
    with session_manager() as session:
        item.tray_id = destination_tray.id
        item.size_class_id = destination_tray.size_class_id
        item.owner_id = destination_tray.owner_id
        item.media_type_id = destination_tray.media_type_id
        item.accession_job_id = destination_tray.accession_job_id
        item.accession_dt = destination_tray.accession_dt
        item.verification_job_id = destination_tray.verification_job_id

        update_dt = datetime.now(timezone.utc)
        item.update_dt = update_dt
        destination_tray.update_dt = update_dt

        session.add(item)
        session.add(destination_tray)
        session.commit()

        session.refresh(source_tray)
        session.refresh(destination_tray)

        # FIX: session.query().filter().first() -> session.execute(select(...)).scalars().first()
        updated_source_tray = session.execute(
            select(Tray).filter(Tray.id == source_tray.id)
        ).scalars().first()

        if updated_source_tray and len(updated_source_tray.items) == 0:
            # FIX: Use session.execute(update(...))
            session.execute(
                update(Barcode)
                .where(Barcode.id == source_tray.barcode_id)
                .values(withdrawn=True, update_dt=update_dt)
            )
            session.execute(
                update(Tray)
                .where(Tray.id == source_tray.id)
                .values(
                    shelf_position_id=None,
                    shelf_position_proposed_id=None,
                    withdrawal_dt=update_dt,
                    withdrawn_barcode_id=source_tray.barcode_id,
                    barcode_id=None,
                    update_dt=update_dt
                )
            )
        update_shelf_space_after_tray(
            session, destination_tray, destination_tray.shelf_position_id,
            source_tray.shelf_position_id
        )
        session.commit()


def process_tray_move(session: Session, tray: Tray, source_shelf: Shelf,
                      destination_shelf: Shelf, destination_shelf_position_id: int):
    update_dt = datetime.now(timezone.utc)
    old_position_id = tray.shelf_position_id
    tray.shelf_position_id = destination_shelf_position_id
    tray.update_dt = update_dt
    session.add(tray)
    update_shelf_space_after_tray(session, tray, destination_shelf_position_id, old_position_id)
    session.commit()
    session.refresh(tray)


def process_non_tray_item_move(session: Session, non_tray_item: NonTrayItem, source_shelf: Shelf,
                      destination_shelf: Shelf, destination_shelf_position_id: int):
    update_dt = datetime.now(timezone.utc)
    old_position_id = non_tray_item.shelf_position_id
    non_tray_item.shelf_position_id = destination_shelf_position_id
    non_tray_item.update_dt = update_dt
    session.add(non_tray_item)
    update_shelf_space_after_non_tray(session, non_tray_item, destination_shelf_position_id, old_position_id)
    session.commit()
    session.refresh(non_tray_item)
    return non_tray_item


def manage_verification_job_change_action(verification_job: VerificationJob, update_input: str, value: Any, audit_info: dict):
    with session_manager() as session:
        start_session_with_audit_info(audit_info, session)
        new_verification_changes = []

        trays = verification_job.trays
        items = verification_job.items
        non_tray_items = verification_job.non_tray_items

        if trays:
            for tray in trays:
                # FIX: session.query().update() -> session.execute(update(...))
                session.execute(update(Tray).where(Tray.id == tray.id).values({update_input: value}))
                # FIX: session.query().first() -> session.execute(select(...)).scalars().first()
                tray_barcode = session.execute(
                    select(Barcode).filter(Barcode.id == tray.barcode_id)
                ).scalars().first()
                
                for item in tray.items:
                    item_barcode = session.execute(
                        select(Barcode).filter(Barcode.id == item.barcode_id)
                    ).scalars().first()
                    change_type = "MediaTypeEdit" if update_input == "media_type_id" else "SizeClassEdit"
                    session.execute(
                        update(Item).where(Item.id == item.id).values({update_input: value})
                    )
                    new_verification_changes.append(
                        VerificationChange(
                            workflow_id=verification_job.workflow_id,
                            tray_barcode_value=tray_barcode.value,
                            item_barcode_value=item_barcode.value,
                            change_type=change_type,
                            completed_by_id=verification_job.user_id
                        )
                    )
        
        if items:
            for item in items:
                item_barcode = session.execute(
                    select(Barcode).filter(Barcode.id == item.barcode_id)
                ).scalars().first()
                tray_barcode = session.execute(
                    select(Barcode).join(Tray).filter(Tray.id == item.tray_id)
                ).scalars().first()
                change_type = "MediaTypeEdit" if update_input == "media_type_id" else "SizeClassEdit"
                session.execute(
                    update(Item).where(Item.id == item.id).values({update_input: value})
                )
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        tray_barcode_value=tray_barcode.value,
                        item_barcode_value=item_barcode.value,
                        change_type=change_type,
                        completed_by_id=verification_job.user_id
                    )
                )

        if non_tray_items:
            for non_tray_item in non_tray_items:
                item_barcode = session.execute(
                    select(Barcode).filter(Barcode.id == non_tray_item.barcode_id)
                ).scalars().first()
                change_type = "MediaTypeEdit" if update_input == "media_type_id" else "SizeClassEdit"
                session.execute(
                    update(NonTrayItem).where(NonTrayItem.id == non_tray_item.id).values({update_input: value})
                )
                new_verification_changes.append(
                    VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        item_barcode_value=item_barcode.value,
                        change_type=change_type,
                        completed_by_id=verification_job.user_id
                    )
                )

        if new_verification_changes:
            session.add_all(new_verification_changes)
        
        session.commit()


def complete_shelving_job(shelving_job_id: int, audit_info: dict):
    try:
        items_to_sync = []
        with session_manager() as session:
            start_session_with_audit_info(audit_info, session)
            
            shelving_job = session.get(ShelvingJob, shelving_job_id)
            if not shelving_job:
                 return

            session.execute(
                update(ShelvingJob)
                .where(ShelvingJob.id == shelving_job.id)
                .values(last_transition=datetime.now(timezone.utc))
            )
            
            if shelving_job.trays:
                for tray in shelving_job.trays:
                    for item in tray.items:
                        item.status = ItemStatus.In
                        session.add(item)
                        if getattr(item, 'barcode', None):
                            items_to_sync.append((item.barcode.value, item.owner_id, False))
            
            if shelving_job.non_tray_items:
                for non_tray_item in shelving_job.non_tray_items:
                    non_tray_item.status = NonTrayItemStatus.In
                    session.add(non_tray_item)
                    if getattr(non_tray_item, 'barcode', None):
                        items_to_sync.append((non_tray_item.barcode.value, non_tray_item.owner_id, True))

            log_audit_event(
                session,
                AuditEventType.JOB_COMPLETED,
                f"Shelving Job {shelving_job_id} completed — item statuses set to In",
                job_type="shelving_jobs",
                job_id=shelving_job_id,
            )

            session.commit()
            
        # Fire off ILS check-ins after the commit is successful
        for barcode_value, owner_id, is_non_tray in items_to_sync:
            check_in_shelved_item_async(
                barcode_value=barcode_value,
                owner_id=owner_id,
                is_non_tray=is_non_tray,
                shelving_job_id=shelving_job_id
            )

    except Exception as e:
        inventory_logger.error(f"Error in complete_shelving_job: {e}")
