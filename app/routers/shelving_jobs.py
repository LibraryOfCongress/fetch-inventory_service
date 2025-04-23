from fastapi import APIRouter, HTTPException, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy import func, text
from sqlmodel import Session, select
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, JobFilterParams
from app.logger import inventory_logger
from app.models.accession_jobs import AccessionJob, AccessionJobStatus
from app.models.users import User
from app.events import update_shelf_space_after_tray, update_shelf_space_after_non_tray
from app.sorting import ShelvingJobSorter
from app.utilities import (
    process_containers_for_shelving,
    manage_transition,
    start_session_with_audit_info,
)
from app.models.verification_jobs import VerificationJob, VerificationJobStatus
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.shelving_jobs import ShelvingJob
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.barcodes import Barcode
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.schemas.shelving_jobs import (
    ShelvingJobInput,
    ShelvingJobUpdateInput,
    ShelvingJobListOutput,
    ShelvingJobDetailOutput,
    ReAssignmentInput,
    ReAssignmentOutput, ProposedReAssignmentInput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
    BadRequest,
)

router = APIRouter(
    prefix="/shelving-jobs",
    tags=["shelving jobs"],
)


def get_shelving_position(session: Session, shelving_job: ShelvingJob):
    trays = shelving_job.trays
    non_tray_items = shelving_job.non_tray_items

    if trays:
        for index, tray in enumerate(trays):
            if not tray.shelf_position_id and tray.shelf_position_proposed_id:
                trays[index].shelf_position = (
                    session.query(ShelfPosition)
                    .where(tray.shelf_position_proposed_id == ShelfPosition.id)
                    .first()
                )
            else:
                continue

    if non_tray_items:
        for index, non_tray_item in enumerate(non_tray_items):
            if (
                not non_tray_item.shelf_position_id
                and non_tray_item.shelf_position_proposed_id
            ):
                non_tray_items[index].shelf_position = (
                    session.query(ShelfPosition)
                    .where(non_tray_item.shelf_position_proposed_id == ShelfPosition.id)
                    .first()
                )
            else:
                continue

    shelving_job.trays = trays
    shelving_job.non_tray_items = non_tray_items

    return shelving_job


@router.get("/", response_model=Page[ShelvingJobListOutput])
def get_shelving_job_list(
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Retrieve a paginated list of shelving jobs.
    Default view filters out Completed jobs.

    **Parameters:**

    - params: The filter parameters.
        - queue: Filters out cancelled jobs
        - workflow_id: The ID of the workflow.
        - created_by_id: The ID of the user who created the shelving job list.
        - building_name: The name of the building.
        - user_id: The ID of the user.
        - assigned_user: The name of the assigned user.
        - status: The status of the shelving job.
        - from_dt: The start date.
        - to_dt: The end date.
    - sort_params: The sort parameters.
        - sort_by: The field to sort by.
        - sort_order: The order to sort by.

    **Returns:**
    - list: A paginated list of shelving jobs.
    """
    # Create a query to select all Shelving Job
    query = select(ShelvingJob)

    try:
        if params.queue:
            # used on job dashboard, not in search
            query = query.where(ShelvingJob.status != "Completed").where(
                ShelvingJob.status != "Cancelled"
            )
        if params.status and len(list(filter(None, params.status))) > 0:
            query = query.where(ShelvingJob.status.in_(params.status))
        if params.workflow_id:
            query = query.where(ShelvingJob.id == params.workflow_id)
        if params.user_id:
            query = query.where(ShelvingJob.user_id.in_(params.user_id))
        if params.assigned_user:
            assigned_user_subquery = (
                select(User.id)
                .where(
                    func.concat(User.first_name, " ", User.last_name).in_(
                        params.assigned_user
                    )
                )
                .distinct()
            )
            query = query.where(ShelvingJob.user_id.in_(assigned_user_subquery))
        if params.created_by_id:
            query = query.where(ShelvingJob.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(ShelvingJob.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(ShelvingJob.create_dt <= params.to_dt)

        # Validate and Apply sorting based on sort_params
        if sort_params.sort_by:
            # Apply sorting using RequestSorter
            sorter = ShelvingJobSorter(ShelvingJob)
            query = sorter.apply_sorting(query, sort_params)

        return paginate(session, query)

    except IntegrityError as e:
        raise InternalServerError(detail=f"{e}")


@router.get("/{id}", response_model=ShelvingJobDetailOutput)
def get_shelving_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the shelving job detail for the given ID.

    **Args:**
    - id: The ID of the shelving job.

    **Returns:**
    - Shelving Job Detail Output: The shelving job detail.

    **Raises:**
    - HTTPException: If the shelving job with the given ID is not found.
    """
    shelving_job = session.get(ShelvingJob, id)

    if shelving_job:
        return get_shelving_position(session, shelving_job)

    raise NotFound(detail=f"Shelving Job ID {id} Not Found")


@router.post("/", response_model=ShelvingJobDetailOutput, status_code=201)
def create_shelving_job(
    shelving_job_input: ShelvingJobInput,
    module_id: int | None = None,
    aisle_id: int | None = None,
    side_id: int | None = None,
    ladder_id: int | None = None,
    session: Session = Depends(get_session),
) -> ShelvingJob:
    """
    Create a new shelving job:

    **Args:**
    - Shelving Job Input: The input data for creating the
    shelving job.

    **Returns:**
    - Shelving Job: The created shelving job.

    **Raises:**
    - HTTPException: If there is an integrity error during the creation of the
    shelving job.
    """

    try:
        new_shelving_job = ShelvingJob(
            **shelving_job_input.model_dump(exclude={"verification_jobs"})
        )
        audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
        session.add(new_shelving_job)
        session.commit()
        session.refresh(new_shelving_job)

        if new_shelving_job.origin == "Verification":
            if not shelving_job_input.verification_jobs:
                raise ValidationException(
                    detail="verification_jobs are required when origin is 'Verification'."
                )
            # Assign verification jobs to shelving_job
            for verification_job_id in shelving_job_input.verification_jobs:
                verification_job = (
                    session.query(VerificationJob)
                    .filter(VerificationJob.id == verification_job_id)
                    .first()
                )
                # check for null and that ver job is complete
                if not verification_job:
                    raise ValidationException(
                        detail=f"verification_job_id {verification_job_id} not found."
                    )
                else:
                    if verification_job.status != "Completed":
                        raise ValidationException(
                            detail=f"verification_job_id {verification_job_id} 's job status must be 'Completed'."
                        )
                    if verification_job.shelving_job_id:
                        raise ValidationException(
                            detail=f"verification_job_id {verification_job_id} has already been shelved during shelving job {verification_job.shelving_job_id}"
                        )

                # Assign trays to shelving job and shelf positions
                if verification_job.trays:
                    process_containers_for_shelving(
                        session,
                        "Tray",
                        verification_job.trays,
                        new_shelving_job.id,
                        new_shelving_job.building_id,
                        module_id,
                        aisle_id,
                        side_id,
                        ladder_id,
                    )

                # Assign NonTrayItems to shelving job and shelf positions
                if verification_job.non_tray_items:
                    process_containers_for_shelving(
                        session,
                        "Non-Tray",
                        verification_job.non_tray_items,
                        new_shelving_job.id,
                        new_shelving_job.building_id,
                        module_id,
                        aisle_id,
                        side_id,
                        ladder_id,
                    )

                # set verification shelving job last, in case container errors
                verification_job.shelving_job_id = new_shelving_job.id
                session.add(verification_job)
                start_session_with_audit_info(audit_info, session)
                session.commit()

        # else, shelving_job.origin == "Direct", return shelving_job
        return get_shelving_position(session, new_shelving_job)

    except IntegrityError as e:
        session.delete(new_shelving_job)
        session.commit()
        raise ValidationException(detail=f"{e}")
    except ValidationException as e:
        session.delete(new_shelving_job)
        session.commit()
        # Pass through the original error
        raise ValidationException(detail=f"{e.detail}")
    except NotFound as e:
        session.delete(new_shelving_job)
        session.commit()
        # Pass through the original error
        raise NotFound(detail=f"{e.detail}")


@router.patch("/{id}", response_model=ShelvingJobDetailOutput)
def update_shelving_job(
    id: int,
    shelving_job: ShelvingJobUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Update an existing shelving job with the provided data.

    ***Parameters:**
    - id: The ID of the shelving job to be updated.
    - shelving job: The data to update the shelving job with.

    **Returns:**
    - HTTPException: If the shelving job is not found or if an error occurs during
    the update.
    """
    try:
        existing_shelving_job = session.get(ShelvingJob, id)

        if not existing_shelving_job:
            raise NotFound(detail=f"Shelving Job ID {id} Not Found")

        if shelving_job.status and shelving_job.run_timestamp:
            existing_shelving_job = manage_transition(
                existing_shelving_job, shelving_job
            )

        mutated_data = shelving_job.model_dump(
            exclude_unset=True, exclude={"run_timestamp"}
        )

        for key, value in mutated_data.items():
            setattr(existing_shelving_job, key, value)

        setattr(existing_shelving_job, "update_dt", datetime.now(timezone.utc))

        session.add(existing_shelving_job)
        session.commit()
        session.refresh(existing_shelving_job)

        return get_shelving_position(session, existing_shelving_job)

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}", status_code=204)
def delete_shelving_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a shelving job by its ID.
    **Args:**
    - id: The ID of the shelving job to be deleted.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    shelving_job = session.get(ShelvingJob, id)
    if shelving_job.status in ["Running", "Completed"]:
        raise ValidationException(
            detail=f"""Shelving Job ID {id} status is in "
                                         'Running' or 'Completed'"""
        )

    if shelving_job:
        trays = shelving_job.trays
        non_tray_items = shelving_job.non_tray_items
        update_dt = datetime.now(timezone.utc)

        if trays:
            tray_ids = [tray.id for tray in trays]
            if tray_ids:
                session.query(Tray).filter(Tray.id.in_(tray_ids)).update(
                    {
                        "shelving_job_id": None,
                        "shelf_position_id": None,
                        "shelf_position_proposed_id": None,
                        "shelved_dt": None,
                        "update_dt": update_dt,
                    }
                )

        if non_tray_items:
            non_tray_item_ids = [non_tray_item.id for non_tray_item in non_tray_items]
            if non_tray_item_ids:
                session.query(NonTrayItem).filter(
                    NonTrayItem.id.in_(non_tray_item_ids)
                ).update(
                    {
                        "shelving_job_id": None,
                        "shelf_position_id": None,
                        "shelf_position_proposed_id": None,
                        "shelved_dt": None,
                        "update_dt": update_dt,
                    }
                )

        # Updating Verifications Jobs
        existing_verification_jobs = (
            session.query(VerificationJob)
            .where(VerificationJob.shelving_job_id == id)
            .all()
        )

        if existing_verification_jobs:
            verification_job_ids = [
                verification_job.id for verification_job in existing_verification_jobs
            ]
            if verification_job_ids:
                session.query(VerificationJob).filter(
                    VerificationJob.id.in_(verification_job_ids)
                ).update({"shelving_job_id": None, "update_dt": update_dt})

        # Removing Shelving Job Discrepancies
        existing_shelving_job_discrepancies = (
            session.query(ShelvingJobDiscrepancy)
            .where(ShelvingJobDiscrepancy.shelving_job_id == id)
            .all()
        )

        if existing_shelving_job_discrepancies:
            discrepancy_ids = [
                discrepancy.id for discrepancy in existing_shelving_job_discrepancies
            ]
            if discrepancy_ids:
                session.query(ShelvingJobDiscrepancy).filter(
                    ShelvingJobDiscrepancy.id.in_(discrepancy_ids)
                ).delete()

        session.delete(shelving_job)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Shelving Job id {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Shelving Job ID {id} Not Found")


@router.post("/{id}/reassign-container-location", response_model=ReAssignmentOutput)
def reassign_container_location(
    id: int,
    reassignment_input: ReAssignmentInput,
    session: Session = Depends(get_session),
):
    """
    Re-Assign container shelf position, given a container id,
    shelf position number, and a shelf barcode or shelf id.

    This is used for both one-off re-assignments, and the direct
    to shelf workflow.

    Params:
      - id: Shelving Job Id
      - reassignment_input:
        - trayed: bool for Tray (false is NonTrayedItem)
        - container_id: Id of the container
        - container_barcode_value: barcode value of the container
        - shelf_id: Id of a shelf
        - shelf_barcode_value: raw barcode of new shelf
        - shelf_position_number: position number in relation to new shelf
        - scanned_for_shelving: bool. update scan status on container

    Updates container shelving job and shelf position.

    Returns a Tray or NonTrayItem
    """
    audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
    # get container
    if reassignment_input.container_id:
        if reassignment_input.trayed is not None:
            if reassignment_input.trayed:
                container = session.exec(
                    select(Tray).where(Tray.id == reassignment_input.container_id)
                ).first()
            else:
                container = session.exec(
                    select(NonTrayItem).where(
                        NonTrayItem.id == reassignment_input.container_id
                    )
                ).first()
        else:
            raise ValidationException(
                detail=f"If container_id is provided, 'trayed' value is also expected."
            )
    else:
        if not reassignment_input.container_barcode_value:
            raise ValidationException(
                detail=f"If container_id is not provided, 'container_barcode_value' is expected."
            )
        # We do not know if trayed or not. Check both
        tray_container = session.exec(
            select(Tray)
            .join(Barcode, Tray.barcode_id == Barcode.id)
            .where(Barcode.value == reassignment_input.container_barcode_value)
        ).first()
        if not tray_container:
            non_tray_container = session.exec(
                select(NonTrayItem)
                .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
                .where(Barcode.value == reassignment_input.container_barcode_value)
            ).first()
            if not non_tray_container:
                raise NotFound(
                    detail=f"No containers were found with barcode {reassignment_input.container_barcode_value}"
                )
            container = non_tray_container
        else:
            container = tray_container

    # get shelf
    if reassignment_input.shelf_id:
        shelf_id = reassignment_input.shelf_id
    elif reassignment_input.shelf_barcode_value:
        shelf_barcode_join = (
            select(Shelf, Barcode)
            .join(Barcode)
            .where(Barcode.value == reassignment_input.shelf_barcode_value)
        )
        shelf_barcode_join = session.exec(shelf_barcode_join).all()

        if not shelf_barcode_join:
            raise NotFound(
                detail=f"No shelves were found with barcode {reassignment_input.shelf_barcode_value}"
            )
        shelf_barcode_join = shelf_barcode_join[0]
        shelf_id = shelf_barcode_join.Shelf.id
    else:
        raise ValidationException(
            detail="Either shelf_id or shelf_barcode_value must be provided."
        )
    # get shelf position
    shelf_position_position_number_join = (
        select(ShelfPosition, ShelfPositionNumber)
        .join(ShelfPositionNumber)
        .where(ShelfPosition.shelf_id == shelf_id)
        .where(ShelfPositionNumber.number == reassignment_input.shelf_position_number)
    )
    shelf_position_position_number_join = session.exec(
        shelf_position_position_number_join
    ).first()

    if not shelf_position_position_number_join:
        raise ValidationException(
            detail=f"""Shelf Position Number {reassignment_input.shelf_position_number} does not exist on shelf {reassignment_input.shelf_id}"""
        )

    # Check for Availability
    shelf = shelf_position_position_number_join.ShelfPosition.shelf
    shelf_position = shelf_position_position_number_join.ShelfPosition

    # check if tray or non-tray
    if reassignment_input.trayed:
        tray_exists = (
            session.query(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id)
            .where(Tray.id != container.id)
            .first()
        )

        non_tray_exists = (
            session.query(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id)
            .first()
        )
    else:
        tray_exists = (
            session.query(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id)
            .first()
        )

        non_tray_exists = (
            session.query(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id)
            .where(NonTrayItem.id != container.id)
            .first()
        )
    # grab shelving job for user_id
    shelving_job = session.query(ShelvingJob).where(ShelvingJob.id == id).first()
    shelf_type = shelf.shelf_type
    pre_assigned_location = None
    if container.container_type_id == 1:
        discrepancy_tray_id = container.id
        discrepancy_non_tray_id = None
    else:
        discrepancy_tray_id = None
        discrepancy_non_tray_id = container.id

    if container.shelf_position_proposed_id:
        pre_assigned_location = (
            session.query(ShelfPosition)
            .where(ShelfPosition.id == container.shelf_position_proposed_id)
            .first()
        ).location

    accession_job = (session.query(AccessionJob)
                     .where(AccessionJob.id == container.accession_job_id).first())
    if (
        not container.scanned_for_accession or
        not accession_job or
        accession_job.status != AccessionJobStatus.Completed
    ):
        barcode = container.barcode

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Not Accessioned Discrepancy - Container barcode {barcode.value} has not been accessioned""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(detail=f"Container barcode {barcode.value} has not been accessioned")

    verification_job = (
        session.query(VerificationJob)
        .where(VerificationJob.id == container.verification_job_id).first()
    )
    if (
        not container.scanned_for_verification or
        not verification_job or
        verification_job.status != VerificationJobStatus.Completed
    ):
        barcode = container.barcode

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Not Accessioned Discrepancy - Container barcode {barcode.value} has not been verified""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(
            detail=f"Container barcode {barcode.value} has not been verified"
            )

    if shelf.available_space <= 0:
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Available Space Discrepancy - Shelf location {shelf.location}
                    has no available space""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(detail=f"Shelf ID {shelf.id} has no available space")

    if tray_exists or non_tray_exists:
        shelf_position_location = (
            shelf.location + "-" + str(reassignment_input.shelf_position_number)
        )
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf_position.location,
            pre_assigned_location=pre_assigned_location,
            error=f"""Shelf Position Discrepancy - Shelf Position {shelf_position_location}
                    is already occupied""",
        )
        commit_record(session, new_shelving_job_discrepancy)
        raise ValidationException(
            detail=f"""Shelf Position {shelf_position_location} is already occupied"""
        )

    # Check if the container owner and size class match to shelf
    if (
        container.size_class_id != shelf_type.size_class_id
        or container.owner_id != shelf.owner_id
    ):
        # Create a Discrepancy
        discrepancy_error = "Unknown"
        if container.container_type_id == 1:
            discrepancy_tray_id = container.id
            discrepancy_non_tray_id = None
        else:
            discrepancy_tray_id = None
            discrepancy_non_tray_id = container.id
        if container.size_class_id != shelf_type.size_class_id:
            discrepancy_error = f"""Size Discrepancy - Container size_id: {container.size_class_id} does not match Shelf size_id: {shelf_type.size_class_id}"""
        if container.owner_id != shelf.owner_id:
            discrepancy_error = f"""Owner Discrepancy does not match Container owner_id: {container.owner_id} does not match Shelf owner_id: {shelf.owner_id}"""

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf_position.location,
            pre_assigned_location=pre_assigned_location,
            error=f"{discrepancy_error}",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(
            detail=f"Container Barcode {reassignment_input.container_barcode_value} "
                   "does not match Shelf owner and size class."
        )

    # Checking and verifying Verification Job
    if container.verification_job_id:
        verification_job = session.get(VerificationJob, container.verification_job_id)

        if verification_job.shelving_job_id is None:
            verification_job.shelving_job_id = id
            session.add(verification_job)
            session.commit()
            session.refresh(verification_job)

    # only reassign actual, not proposed
    container.shelving_job_id = id
    old_shelf_position_id = container.shelf_position_id
    container.shelf_position_id = shelf_position.id

    if reassignment_input.shelved_dt is not None:
        container.shelved_dt = reassignment_input.shelved_dt

    # bool value, explicitly check if user sent value
    if reassignment_input.scanned_for_shelving is not None:
        container.scanned_for_shelving = reassignment_input.scanned_for_shelving

    session.add(container)
    start_session_with_audit_info(audit_info, session)
    session.commit()
    session.refresh(container)

    if container.container_type_id == 1:
        update_shelf_space_after_tray(
            container, container.shelf_position_id, old_shelf_position_id
        )
    else:
        update_shelf_space_after_non_tray(
            container, container.shelf_position_id, old_shelf_position_id
        )

    return container


@router.post(
    "/{id}/reassign-proposed-location",
    response_model=ReAssignmentOutput
)
def reassign_container_proposed_location(
    id: int,
    reassignment_input: ProposedReAssignmentInput,
    session: Session = Depends(get_session),
):
    # We do not know if trayed or not. Check both
    shelving_job = session.get(ShelvingJob, id)

    shelf_barcode_join = None
    shelf_position_position_number_join = None
    if reassignment_input.shelf_id:
        shelf_barcode_join = (
            select(Shelf)
            .where(Shelf.id == reassignment_input.shelf_id)
        )
        shelf_barcode_join = session.exec(shelf_barcode_join).first()

        if not shelf_barcode_join:
            raise NotFound(
                detail=f"No shelves were found with shelf ID {reassignment_input.shelf_id}"
            )
    elif reassignment_input.shelf_barcode_value:
        shelf_barcode_join = (
            select(Shelf, Barcode)
            .join(Barcode)
            .where(Barcode.value == reassignment_input.shelf_barcode_value)
        )
        shelf_barcode_join = session.exec(shelf_barcode_join).first()

        if not shelf_barcode_join:
            raise NotFound(
                detail=f"No shelves were found with barcode {reassignment_input.shelf_barcode_value}"
            )
    if shelf_barcode_join is not None:
        shelf_id = shelf_barcode_join.Shelf.id

        # get shelf position
        shelf_position_position_number_join = (
            select(ShelfPosition, ShelfPositionNumber)
            .join(ShelfPositionNumber)
            .where(ShelfPosition.shelf_id == shelf_id)
            .where(
                ShelfPositionNumber.number == reassignment_input.shelf_position_number
            )
        )
        shelf_position_position_number_join = session.exec(
            shelf_position_position_number_join
        ).first()

        if not shelf_position_position_number_join:
            raise ValidationException(
                detail=f"""Shelf Position Number {reassignment_input.shelf_position_number} does not exist on shelf"""

            )

    # Check for Availability
    shelf = shelf_position_position_number_join.ShelfPosition.shelf
    shelf_position = shelf_position_position_number_join.ShelfPosition
    non_tray_container = None

    tray_container = session.exec(
        select(Tray)
        .join(Barcode, Tray.barcode_id == Barcode.id)
        .where(Barcode.value == reassignment_input.container_barcode_value)
    ).first()
    if not tray_container:
        non_tray_container = session.exec(
            select(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .where(Barcode.value == reassignment_input.container_barcode_value)
        ).first()
        if not non_tray_container:
            raise NotFound(
                detail=f"No containers were found with barcode {reassignment_input.container_barcode_value}"
            )
        container = non_tray_container
        # Checking if position is already occupied by another container
        tray_exists = (
            session.query(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id)
            .first()
        )
        non_tray_exists = (
            session.query(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id)
            .where(NonTrayItem.id != container.id)
            .first()
        )
    else:
        container = tray_container
        # Checking if position is already occupied by another container
        tray_exists = (
            session.query(Tray)
            .filter(Tray.shelf_position_id == shelf_position.id)
            .where(Tray.id != container.id)
            .first()
        )
        non_tray_exists = (
            session.query(NonTrayItem)
            .join(Barcode, NonTrayItem.barcode_id == Barcode.id)
            .filter(NonTrayItem.shelf_position_id == shelf_position.id)
            .first()
        )

    shelf_type = shelf.shelf_type
    shelf_position_location = (
        shelf.location + "-" + str(reassignment_input.shelf_position_number)
    )
    # Check if position is not already occupied by another container
    if tray_exists or non_tray_exists:
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=tray_container.id,
            non_tray_item_id=non_tray_container.id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf_position.location,
            pre_assigned_location=shelf_position_location,
            error=f"""Shelf Position Discrepancy - Shelf Position {shelf_position_location} is already occupied""",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(
            detail=f"""Shelf Position {shelf_position_location} is already occupied"""
        )

    # Checking for available_space on shelf
    if shelf.available_space <= 0:
        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=tray_container.id,
            non_tray_item_id=non_tray_container.id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf.location,
            pre_assigned_location=shelf_position_location,
            error=f"""Available Space Discrepancy - Shelf location {shelf.location} has no available space""",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(detail=f"Shelf ID {shelf.id} has no available space")

    # Check if the container owner and size class match to shelf
    if (
        container.size_class_id != shelf_type.size_class_id
        or container.owner_id != shelf.owner_id
    ):
        # Create a Discrepancy
        discrepancy_error = "Unknown"
        if container.container_type_id == 1:
            discrepancy_tray_id = container.id
            discrepancy_non_tray_id = None
        else:
            discrepancy_tray_id = None
            discrepancy_non_tray_id = container.id
        if container.size_class_id != shelf_type.size_class_id:
            discrepancy_error = f"""Size Discrepancy - Container size_id: {container.size_class_id} does not match Shelf size_id: {shelf_type.size_class_id}"""
        if container.owner_id != shelf.owner_id:
            discrepancy_error = f"""Owner Discrepancy does not match Container owner_id: {container.owner_id} does not match Shelf owner_id: {shelf.owner_id}"""

        new_shelving_job_discrepancy = ShelvingJobDiscrepancy(
            shelving_job_id=id,
            tray_id=discrepancy_tray_id,
            non_tray_item_id=discrepancy_non_tray_id,
            assigned_user_id=shelving_job.user_id,
            owner_id=shelf.owner_id,
            size_class_id=shelf_type.size_class_id,
            assigned_location=shelf_position.location,
            pre_assigned_location=shelf_position_location,
            error=f"{discrepancy_error}",
        )
        commit_record(session, new_shelving_job_discrepancy)

        raise ValidationException(
            detail=f"Container Barcode {reassignment_input.container_barcode_value} does not match Shelf owner and size class."
        )

    setattr(
        container, "shelf_position_proposed_id",
        shelf_position.id
    )
    setattr(container, "update_dt", datetime.now(timezone.utc))

    # Checking container has already been shelved and shelving_job not Completed,
    # need to update the container shelf_position_id as well.
    if (
        container.shelf_position_id is not None and
        container.shelf_position_id != shelf_position.id and
        shelving_job.status != "Completed"
    ):
        old_shelf_position_id = container.shelf_position_id
        setattr(
            container, "shelf_position_id",
            shelf_position.id
        )
        if container.container_type_id == 1:
            update_shelf_space_after_tray(
                container, container.shelf_position_id, old_shelf_position_id
            )
        else:
            update_shelf_space_after_non_tray(
                container, container.shelf_position_id, old_shelf_position_id
            )

    session.add(container)
    session.commit()
    session.refresh(container)
    session.refresh(shelving_job)

    setattr(container, "shelf_position", shelf_position)
    return container
