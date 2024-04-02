from sqlmodel import Session, select

from app.models.accession_jobs import AccessionJob
from app.models.verification_jobs import VerificationJob
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.items import Item
from app.database.session import commit_record
from app.schemas.verification_jobs import VerificationJobInput


def complete_accession_job(session, accession_job: AccessionJob):
    """
    Upon accession job completion:
        - Generate a related verification job
        - Associate accessioned entities to the new verification job
        - Set accessioned entity ownership to accession job owner

    This task allows us to auto-create verification jobs in queue,
    and to support job ownership change efficiently.
    """
    verification_job_input = VerificationJobInput(
        accession_job_id=accession_job.id,
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
    session.refresh()

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
