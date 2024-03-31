from sqlmodel import Session, select

from app.models.accession_jobs import AccessionJob
from app.models.verification_jobs import VerificationJob
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.items import Item
from app.database.session import commit_record
from app.schemas.verification_jobs import VerificationJobInput


def generate_verification_job(session, accession_job: AccessionJob):
    """
    Generates a verification job from the given tray, item, and non-tray item.
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

    # Update Tray Records with Verification Job id
    tray_query = select(Tray).where(Tray.accession_job_id == accession_job.id)
    trays = session.exec(tray_query)
    if trays:
        for tray in trays:
            tray.verification_job_id = new_verification_job.id
            session.add(tray)

    # Update Non Tray Item Records with Verification Job ID
    non_tray_query = select(NonTrayItem).where(
        NonTrayItem.accession_job_id == accession_job.id
    )
    non_trays_items = session.exec(non_tray_query)
    if non_trays_items:
        for non_tray_item in non_trays_items:
            non_tray_item.verification_job_id = new_verification_job.id
            session.add(non_tray_item)

    # Update Item Records with Verification Job_ID
    item_query = select(Item).where(Item.accession_job_id == accession_job.id)
    items = session.exec(item_query).first()
    if items:
        for item in items:
            item.verification_job_id = new_verification_job.id
            session.add(item)

    session.commit()
    session.refresh()
