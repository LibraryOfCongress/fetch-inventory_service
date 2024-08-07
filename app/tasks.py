from sqlmodel import Session, select
from datetime import datetime

from app.config.exceptions import NotFound
from app.models.accession_jobs import AccessionJob
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
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
        status="Created",
    )

    new_verification_job = VerificationJob(**verification_job_input.model_dump())

    # Create a new verification job record
    new_verification_job = commit_record(session, new_verification_job)

    # Update Tray Records
    tray_query = select(Tray).where(Tray.accession_job_id == accession_job.id)
    trays = session.exec(tray_query)
    if trays:
        for tray in trays:
            tray.verification_job_id = new_verification_job.id
            tray.owner_id = accession_job.owner_id
            session.add(tray)

    # Update Non Tray Item Records
    non_tray_query = select(NonTrayItem).where(
        NonTrayItem.accession_job_id == accession_job.id
    )
    non_trays_items = session.exec(non_tray_query)
    if non_trays_items:
        for non_tray_item in non_trays_items:
            non_tray_item.verification_job_id = new_verification_job.id
            non_tray_item.owner_id = accession_job.owner_id
            session.add(non_tray_item)

    # Update Item Records
    item_query = select(Item).where(Item.accession_job_id == accession_job.id)
    items = session.exec(item_query)
    if items:
        for item in items:
            item.verification_job_id = new_verification_job.id
            item.owner_id = accession_job.owner_id
            session.add(item)

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
    session.refresh()


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


def manage_shelf_position(session, item):
    """
    Task manages transition logic for an item's shelf position.
        - updates available_space
    """
    shelf_position = (
        session.query(ShelfPosition)
        .filter(ShelfPosition.id == item.shelf_position_id)
        .first()
    )

    if not shelf_position:
        raise NotFound(detail=f"Shelf Position ID {item.shelf_position_id} Not Found")

    shelf = session.query(Shelf).filter(Shelf.id == shelf_position.shelf_id).first()

    if not shelf:
        raise NotFound(detail=f"Shelf ID {shelf_position.shelf_id} Not Found")

    if item.shelf_position_id is None:
        shelf.available_space -= 1
    else:
        shelf.available_space += 1

    session.add(shelf)
    session.commit()
    session.refresh(shelf_position)
