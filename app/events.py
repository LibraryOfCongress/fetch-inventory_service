# /code/app/events.py - FULL REFACRORED TO SQLALCHEMY V2

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import event, select, update

from app.database.session import commit_record, engine
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.shelving_jobs import ShelvingJob
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.shelf_types import ShelfType

"""
These events only observe triggers where SQLAlchemy is the session manager.
Otherwise they are called on demand in background threads in some places.
"""




# This only triggers if validation passed. Otherwise discrepancies are created in exceptions.
@event.listens_for(Tray, "after_insert")
def check_for_tray_shelving_discrepancy(mapper, connection, target):
    """Update the shelf location after the object has been inserted into the database."""
    with Session(bind=connection) as session:
        refreshed_target = session.execute(select(Tray).filter_by(id=target.id)).scalars().one()
        if refreshed_target.shelving_job_id and not refreshed_target.withdrawn_barcode_id:
            if refreshed_target.shelf_position_id:
                ## Is Shelved - check for discrepancies
                # Get Shelf and Position
                actual_shelf_position = session.execute(select(ShelfPosition).filter_by(id=refreshed_target.shelf_position_id)).scalars().one()
                shelf = session.execute(select(Shelf).filter_by(id=actual_shelf_position.shelf_id)).scalars().one()
                # get shelf_type for size_class
                shelf_type = session.execute(select(ShelfType).filter_by(id=shelf.shelf_type_id)).scalars().one()
                # get shelving_job for user
                shelving_job = session.execute(select(ShelvingJob).filter_by(id=refreshed_target.shelving_job_id)).scalars().one()
                # LOCATION Discrepancy
                if refreshed_target.shelf_position_proposed_id:
                    if refreshed_target.shelf_position_proposed_id != refreshed_target.shelf_position_id:
                        # get proposed position for location
                        proposed_position = session.execute(select(ShelfPosition).filter_by(
                            id=refreshed_target.shelf_position_proposed_id
                        )).scalars().one()
                        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                            shelving_job_id=refreshed_target.shelving_job_id,
                            tray_id=refreshed_target.id,
                            assigned_user_id=shelving_job.assigned_user_id,
                            error=f"""Location Discrepancy -
                            Proposed: {proposed_position.location} -
                            Actual: {actual_shelf_position.location}"""
                        )
                        new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)
                # OWNER Discrepancy
                if refreshed_target.owner_id != shelf.owner_id:
                    new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                        shelving_job_id=refreshed_target.shelving_job_id,
                        tray_id=refreshed_target.id,
                        assigned_user_id=shelving_job.assigned_user_id,
                        error=f"""Owner Discrepancy -
                        Tray owner_id: {refreshed_target.owner_id} -
                        Shelf owner_id: {shelf.owner_id}"""
                    )
                    new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)
                # SIZE Discrepancy
                if shelf_type.size_class_id != refreshed_target.size_class_id:
                    new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                        shelving_job_id=refreshed_target.shelving_job_id,
                        tray_id=refreshed_target.id,
                        assigned_user_id=shelving_job.assigned_user_id,
                        error=f"""Size Discrepancy -
                        Tray size_class_id: {refreshed_target.size_class_id} -
                        Shelf size_class_id: {shelf_type.size_class_id}"""
                    )
                    new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)


# V2 FIX
@event.listens_for(NonTrayItem, "after_insert")
def check_for_non_tray_shelving_discrepancy(mapper, connection, target):
    """Update the shelf location after the object has been inserted into the database."""
    with Session(bind=connection) as session:
        refreshed_target = session.execute(select(NonTrayItem).filter_by(id=target.id)).scalars().one()
        if refreshed_target.shelving_job_id and not refreshed_target.withdrawn_barcode_id:
            if refreshed_target.shelf_position_id:
                ## Is Shelved - check for discrepancies
                # Get Shelf and Position
                actual_shelf_position = session.execute(select(ShelfPosition).filter_by(id=refreshed_target.shelf_position_id)).scalars().one()
                shelf = session.execute(select(Shelf).filter_by(id=actual_shelf_position.shelf_id)).scalars().one()
                # get shelf_type for size_class
                shelf_type = session.execute(select(ShelfType).filter_by(id=shelf.shelf_type_id)).scalars().one()
                # get shelving_job for user
                shelving_job = session.execute(select(ShelvingJob).filter_by(id=refreshed_target.shelving_job_id)).scalars().one()
                # LOCATION Discrepancy
                if refreshed_target.shelf_position_proposed_id:
                    if refreshed_target.shelf_position_proposed_id != refreshed_target.shelf_position_id:
                        # get proposed position for location
                        proposed_position = session.execute(select(ShelfPosition).filter_by(
                            id=refreshed_target.shelf_position_proposed_id
                        )).scalars().one()
                        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                            shelving_job_id=refreshed_target.shelving_job_id,
                            non_tray_item_id=refreshed_target.id,
                            assigned_user_id=shelving_job.assigned_user_id,
                            error=f"""Location Discrepancy -
                            Proposed: {proposed_position.location} -
                            Actual: {actual_shelf_position.location}"""
                        )
                        new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)
                # OWNER Discrepancy
                if refreshed_target.owner_id != shelf.owner_id:
                    new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                        shelving_job_id=refreshed_target.shelving_job_id,
                        non_tray_item_id=refreshed_target.id,
                        assigned_user_id=shelving_job.assigned_user_id,
                        error=f"""Owner Discrepancy -
                        Tray owner_id: {refreshed_target.owner_id} -
                        Shelf owner_id: {shelf.owner_id}"""
                    )
                    new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)
                # SIZE Discrepancy
                if shelf_type.size_class_id != refreshed_target.size_class_id:
                    new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                        shelving_job_id=refreshed_target.shelving_job_id,
                        non_tray_item_id=refreshed_target.id,
                        assigned_user_id=shelving_job.assigned_user_id,
                        error=f"""Size Discrepancy -
                        Tray size_class_id: {refreshed_target.size_class_id} -
                        Shelf size_class_id: {shelf_type.size_class_id}"""
                    )
                    new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)


def update_shelf_space_after_tray(
    session: Session,
    tray: Optional[Tray],
    current_shelf_position_id: Optional[int],
    old_shelf_position_id: Optional[int]
):
    """
    Synchronously updates the available_space using delta math (+1 or -1)
    within the same transaction.
    """
    if tray and not current_shelf_position_id:
        new_position_id = tray.shelf_position_id
    elif tray and current_shelf_position_id:
        new_position_id = current_shelf_position_id
    else:
        new_position_id = None

    old_position_id = old_shelf_position_id

    if new_position_id and new_position_id != old_position_id:
        # Decrement space on the new shelf
        shelf_id = session.scalar(select(ShelfPosition.shelf_id).where(ShelfPosition.id == new_position_id))
        if shelf_id:
            session.execute(update(Shelf).where(Shelf.id == shelf_id).values(available_space=Shelf.available_space - 1))

    if old_position_id and old_position_id != new_position_id:
        # Increment space on the old shelf
        shelf_id = session.scalar(select(ShelfPosition.shelf_id).where(ShelfPosition.id == old_position_id))
        if shelf_id:
            session.execute(update(Shelf).where(Shelf.id == shelf_id).values(available_space=Shelf.available_space + 1))


def update_shelf_space_after_non_tray(
    session: Session,
    non_tray_item: Optional[NonTrayItem],
    current_shelf_position_id: Optional[int],
    old_shelf_position_id: Optional[int]
):
    """
    Synchronously updates the available_space using delta math (+1 or -1)
    within the same transaction.
    """
    if non_tray_item and not current_shelf_position_id:
        new_position_id = non_tray_item.shelf_position_id
    elif non_tray_item and current_shelf_position_id:
        new_position_id = current_shelf_position_id
    else:
        new_position_id = None

    old_position_id = old_shelf_position_id

    if new_position_id and new_position_id != old_position_id:
        # Decrement space on the new shelf
        shelf_id = session.scalar(select(ShelfPosition.shelf_id).where(ShelfPosition.id == new_position_id))
        if shelf_id:
            session.execute(update(Shelf).where(Shelf.id == shelf_id).values(available_space=Shelf.available_space - 1))

    if old_position_id and old_position_id != new_position_id:
        # Increment space on the old shelf
        shelf_id = session.scalar(select(ShelfPosition.shelf_id).where(ShelfPosition.id == old_position_id))
        if shelf_id:
            session.execute(update(Shelf).where(Shelf.id == shelf_id).values(available_space=Shelf.available_space + 1))