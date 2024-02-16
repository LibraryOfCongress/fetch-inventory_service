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
        status="Created",
    )

    new_verification_job = VerificationJob(**verification_job_input.model_dump())

    # Create a new verification job record
    new_verification_job = commit_record(session, new_verification_job)

    # Update Tray Record with Verification Job id
    tray = select(Tray).where(Tray.accession_job_id == accession_job.id)
    existing_tray = session.exec(tray).first()

    if existing_tray:
        existing_tray.verification_job_id = new_verification_job.id
        # Update Tray Record
        session.add(existing_tray)

    # Update Non Tray Item Record with Verification Job ID
    non_tray_item = select(NonTrayItem).where(
        NonTrayItem.accession_job_id == accession_job.id
    )
    existing_non_tray_item = session.exec(non_tray_item).first()

    if existing_non_tray_item:
        existing_non_tray_item.verification_job_id = new_verification_job.id
        # Update Non Tray Item Record
        session.add(existing_non_tray_item)

    # Update Item Record with Verification Job_ID
    item = select(Item).where(Item.accession_job_id == accession_job.id)
    existing_item = session.exec(item).first()

    if existing_item:
        existing_item.verification_job_id = new_verification_job.id
        # Update Item Record
        session.add(existing_item)

    session.commit()
    session.refresh()
