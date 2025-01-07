from sqlmodel import Session
from sqlalchemy import event

from app.database.session import commit_record
from app.models.shelf_positions import ShelfPosition
from app.models.shelves import Shelf
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.shelving_jobs import ShelvingJob
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.shelf_types import ShelfType


@event.listens_for(ShelfPosition, "after_insert")
def generate_location(mapper, connection, target):
    """Update the shelf position location after the object has been inserted into the database."""
    with Session(bind=connection) as session:
        refreshed_target = session.query(ShelfPosition).filter_by(id=target.id).one()
        refreshed_target.update_position_address(session=session)
        session.add(refreshed_target)
        session.commit()

@event.listens_for(Shelf, "after_insert")
def generate_shelf_location(mapper, connection, target):
    """Update the shelf location after the object has been inserted into the database."""
    with Session(bind=connection) as session:
        refreshed_target = session.query(Shelf).filter_by(id=target.id).one()
        refreshed_target.update_shelf_address(session=session)
        session.add(refreshed_target)
        session.commit()


# This only triggers if validation passed. Otherwise discrepancies are created in exceptions.
@event.listens_for(Tray, "after_insert")
def check_for_tray_shelving_discrepancy(mapper, connection, target):
    """Update the shelf location after the object has been inserted into the database."""
    with Session(bind=connection) as session:
        refreshed_target = session.query(Tray).filter_by(id=target.id).one()
        if refreshed_target.shelving_job_id and not refreshed_target.withdrawn_barcode_id:
            if refreshed_target.shelf_position_id:
                ## Is Shelved - check for discrepancies
                # Get Shelf and Position
                actual_shelf_position = session.query(ShelfPosition).filter_by(id=refreshed_target.shelf_position_id).one()
                shelf = session.query(Shelf).filter_by(id=actual_shelf_position.id).one()
                # get shelf_type for size_class
                shelf_type = session.query(ShelfType).filter_by(id=shelf.shelf_type_id).one()
                # get shelving_job for user
                shelving_job = session.query(ShelvingJob).filter_by(id=refreshed_target.shelving_job_id).one()
                # LOCATION Discrepancy
                if refreshed_target.shelf_position_proposed_id:
                    if refreshed_target.shelf_position_proposed_id != refreshed_target.shelf_position_id:
                        # get proposed position for location
                        proposed_position = session.query(ShelfPosition).filter_by(
                            id=refreshed_target.shelf_position_proposed_id
                        ).one()
                        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                            shelving_job_id=refreshed_target.shelving_job_id,
                            tray_id=refreshed_target.id,
                            assigned_user_id=shelving_job.user_id,
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
                        assigned_user_id=shelving_job.user_id,
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
                        assigned_user_id=shelving_job.user_id,
                        error=f"""Size Discrepancy -
                        Tray size_class_id: {refreshed_target.size_class_id} -
                        Shelf size_class_id: {shelf_type.size_class_id}"""
                    )
                    new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)


# This only triggers if validation passed. Otherwise discrepancies are created in exceptions.
@event.listens_for(NonTrayItem, "after_insert")
def check_for_non_tray_shelving_discrepancy(mapper, connection, target):
    """Update the shelf location after the object has been inserted into the database."""
    with Session(bind=connection) as session:
        refreshed_target = session.query(NonTrayItem).filter_by(id=target.id).one()
        if refreshed_target.shelving_job_id and not refreshed_target.withdrawn_barcode_id:
            if refreshed_target.shelf_position_id:
                ## Is Shelved - check for discrepancies
                # Get Shelf and Position
                actual_shelf_position = session.query(ShelfPosition).filter_by(id=refreshed_target.shelf_position_id).one()
                shelf = session.query(Shelf).filter_by(id=actual_shelf_position.id).one()
                # get shelf_type for size_class
                shelf_type = session.query(ShelfType).filter_by(id=shelf.shelf_type_id).one()
                # get shelving_job for user
                shelving_job = session.query(ShelvingJob).filter_by(id=refreshed_target.shelving_job_id).one()
                # LOCATION Discrepancy
                if refreshed_target.shelf_position_proposed_id:
                    if refreshed_target.shelf_position_proposed_id != refreshed_target.shelf_position_id:
                        # get proposed position for location
                        proposed_position = session.query(ShelfPosition).filter_by(
                            id=refreshed_target.shelf_position_proposed_id
                        ).one()
                        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
                            shelving_job_id=refreshed_target.shelving_job_id,
                            non_tray_item_id=refreshed_target.id,
                            assigned_user_id=shelving_job.user_id,
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
                        assigned_user_id=shelving_job.user_id,
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
                        assigned_user_id=shelving_job.user_id,
                        error=f"""Size Discrepancy -
                        Tray size_class_id: {refreshed_target.size_class_id} -
                        Shelf size_class_id: {shelf_type.size_class_id}"""
                    )
                    new_shelving_job_discrepancy = commit_record(session, new_shelving_job_discrepancy)
