from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import exists

from app.database.session import get_session
from app.filter_params import JobFilterParams
from app.logger import inventory_logger
from app.utilities import process_containers_for_shelving, manage_transition
from app.models.verification_jobs import VerificationJob
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.shelving_jobs import ShelvingJob, ShelvingJobStatus
from app.models.shelves import Shelf
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.barcodes import Barcode
from app.schemas.shelving_jobs import (
    ShelvingJobInput,
    ShelvingJobUpdateInput,
    ShelvingJobListOutput,
    ShelvingJobDetailOutput,
    ReAssignmentInput,
    ReAssignmentOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/shelving-jobs",
    tags=["shelving jobs"],
)


@router.get("/", response_model=Page[ShelvingJobListOutput])
def get_shelving_job_list(
    queue: bool = Query(default=False),
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    status: ShelvingJobStatus | None = None
) -> list:
    """
    Retrieve a paginated list of shelving jobs.
    Default view filters out Completed jobs.

    **Returns:**
    - list: A paginated list of shelving jobs.
    """
    query = select(ShelvingJob).distinct()

    try:
        if queue:
            # used on job dashboard, not in search
            query = query.where(
                ShelvingJob.status != "Completed"
            ).where(
                ShelvingJob.status != "Cancelled"
            )
        if params.workflow_id:
            query = query.where(ShelvingJob.id == params.workflow_id)
        if params.user_id:
            query = query.where(ShelvingJob.user_id == params.user_id)
        if params.created_by_id:
            query = query.where(ShelvingJob.created_by_id == params.created_by_id)
        if params.from_dt:
            query = query.where(ShelvingJob.create_dt >= params.from_dt)
        if params.to_dt:
            query = query.where(ShelvingJob.create_dt <= params.to_dt)
        if status:
            query = query.where(ShelvingJob.status == status.value)

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
        return shelving_job

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
        session.add(new_shelving_job)
        session.commit()
        session.refresh(new_shelving_job)

        if new_shelving_job.origin == "Verification":
            if not shelving_job_input.verification_jobs:
                raise ValidationException(
                    detail=f"verification_jobs are required when origin is 'Verification'."
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
            session.commit()

        # else, shelving_job.origin == "Direct", return shelving_job
        session.refresh(new_shelving_job)

        return new_shelving_job

    except IntegrityError as e:
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

        setattr(existing_shelving_job, "update_dt", datetime.utcnow())

        session.add(existing_shelving_job)
        session.commit()
        session.refresh(existing_shelving_job)

        return existing_shelving_job

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
    if shelving_job:
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
            .join(Barcode)
            .where(Barcode.value == reassignment_input.container_barcode_value)
        ).first()
        if not tray_container:
            non_tray_container = session.exec(
                select(NonTrayItem)
                .join(Barcode)
                .where(Barcode.value == reassignment_input.container_barcode_value)
            ).first()
            if not non_tray_container:
                raise NotFound(
                    detail=f"No containers were found with barcode {reassignment_input.container_barcode_value}"
                )
            container = non_tray_container
        else:
            container = tray_container

        # Checking and verifying Verification Job
        if container.verification_job_id:
            verification_job_shelved = True
            verification_job = session.get(
                VerificationJob, container.verification_job_id
            )

            if verification_job:
                trays = verification_job.trays
                non_tray_items = verification_job.non_tray_items

                if trays:
                    for tray in trays:
                        if (
                            tray.id != container.id
                            and not verification_job.shelving_job_id
                        ):
                            verification_job_shelved = False
                if non_tray_items:
                    for non_tray_item in non_tray_items:
                        if (
                            non_tray_item.id != container.id
                            and not verification_job.shelving_job_id
                        ):
                            verification_job_shelved = False
                if verification_job_shelved:
                    verification_job.shelving_job_id = id
                    session.add(verification_job)
                    session.commit()
                    session.refresh(verification_job)
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
            detail=f"Either shelf_id or shelf_barcode_value must be provided."
        )

    # get shelf position
    shelf_position_position_number_join = (
        select(ShelfPosition, ShelfPositionNumber)
        .join(ShelfPositionNumber)
        .where(ShelfPosition.shelf_id == shelf_id)
        .where(ShelfPositionNumber.number == reassignment_input.shelf_position_number)
    )
    shelf_position_position_number_join = session.exec(
        shelf_position_position_number_join).all()

    if not shelf_position_position_number_join:
        raise ValidationException(
            detail=f"Shelf Position Number {reassignment_input.shelf_position_number} "
            f"does not exist on shelf {reassignment_input.shelf_id}"
        )

    shelf_position_position_number_join = shelf_position_position_number_join[0]

    # Check for Availability
    shelf = shelf_position_position_number_join.ShelfPosition.shelf
    if shelf.available_space == 0:
        raise ValidationException(
            detail=f"Shelf ID {shelf.id} has no available space"
        )

    # check if tray or non-tray
    if reassignment_input.trayed:
        tray_exists = (
            session.query(Tray)
            .filter(
                Tray.shelf_position_id
                == shelf_position_position_number_join.ShelfPosition.id
            )
            .where(Tray.id != container.id)
            .first()
        )

        non_tray_exists = (
            session.query(NonTrayItem)
            .join(Barcode)
            .filter(
                NonTrayItem.shelf_position_id
                == shelf_position_position_number_join.ShelfPosition.id
            )
            .first()
        )
    else:
        tray_exists = (
            session.query(Tray)
            .filter(
                Tray.shelf_position_id
                == shelf_position_position_number_join.ShelfPosition.id
            )
            .first()
        )

        non_tray_exists = (
            session.query(NonTrayItem)
            .join(Barcode)
            .filter(
                NonTrayItem.shelf_position_id
                == shelf_position_position_number_join.ShelfPosition.id
            )
            .where(NonTrayItem.id != container.id)
            .first()
        )

    if tray_exists or non_tray_exists:
        raise ValidationException(
            detail=f"Shelf Position {reassignment_input.shelf_position_number} "
            f"assigned."
        )

    updated_shelf_position_id = shelf_position_position_number_join.ShelfPosition.id
    shelf_position = (
        session.query(ShelfPosition)
        .where(ShelfPosition.id == updated_shelf_position_id)
        .first()
    )
    updated_shelf = (
        session.query(Shelf).where(Shelf.id == shelf_position.shelf_id).first()
    )

    if updated_shelf.available_space <= 0:
        raise ValidationException(
            detail=f"Shelf ID {updated_shelf.id} has no available space."
        )

    else:
        if container.shelf_position_id != updated_shelf_position_id:
            previous_shelf_position = (
                session.query(ShelfPosition)
                .where(ShelfPosition.id == container.shelf_position_id)
                .first()
            )

            if previous_shelf_position and (
                previous_shelf_position.shelf_id != updated_shelf.id
            ):
                session.query(Shelf).where(
                    Shelf.id == previous_shelf_position.shelf_id
                ).update({"available_space": Shelf.available_space + 1})

        session.query(Shelf).where(Shelf.id == shelf_position.shelf_id).update(
            {"available_space": Shelf.available_space - 1}
        )

    shelf_type = updated_shelf.shelf_type
    # Check if the container owner and size class match to shelf
    if (
        container.size_class_id != shelf_type.size_class_id
        or container.owner_id != updated_shelf.owner_id
    ):
        raise ValidationException(
            detail=f"Container Barcode {reassignment_input.container_barcode_value}  "
            f"does not match Shelf owner and size class."
        )

    # only reassign actual, not proposed
    container.shelving_job_id = id
    container.shelf_position_id = shelf_position_position_number_join.ShelfPosition.id

    # bool value, explicitly check if user sent value
    if reassignment_input.scanned_for_shelving is not None:
        container.scanned_for_shelving = reassignment_input.scanned_for_shelving

    session.add(container)
    session.commit()
    session.refresh(container)

    return container
