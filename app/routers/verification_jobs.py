from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlmodel import Session, select
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, JobFilterParams
from app.models.barcodes import Barcode
from app.models.container_types import ContainerType
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.trays import Tray
from app.models.users import User
from app.models.verification_changes import VerificationChange
from app.sorting import BaseSorter
from app.tasks import (
    complete_verification_job,
    manage_verification_job_transition, manage_verification_job_change_action,
)
from app.models.verification_jobs import VerificationJob
from app.models.accession_jobs import AccessionJob
from app.schemas.verification_jobs import (
    VerificationJobInput,
    VerificationJobUpdateInput,
    VerificationJobListOutput,
    VerificationJobDetailOutput,
    VerificationJobAddInput,
    VerificationJobRemoveInput
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/verification-jobs",
    tags=["verification jobs"],
)


@router.get("/", response_model=Page[VerificationJobListOutput])
def get_verification_job_list(
    unshelved: bool | None = False,
    session: Session = Depends(get_session),
    params: JobFilterParams = Depends(),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a paginated list of verification jobs.

    **Parameters:**
    - unshelved: Filters out shelved verification jobs.
    - params: The filter parameters.
        - queue: Filters out cancelled verification jobs.
        - workflow_id: The ID of the workflow.
        - created_by_id: The ID of the user who created the pick list.
        - user_id: The ID of the user.
        - assigned_user: The name of the assigned user.
        - status: The status of the verification job.
        - from_dt: The start date.
        - to_dt: The end date.

    - sort_params: The sort parameters.
        - sort_by: The field to sort by.
        - sort_order: The order to sort by.

    **Returns:**
    - Verification Job List Output: The paginated list of verification jobs.
    """
    # Create a query to select all Verification Job from the database
    query = select(VerificationJob).distinct()

    if unshelved:
        # retrieve completed verification jobs that haven't been shelved
        query = query.where(VerificationJob.shelving_job_id == None).where(
            VerificationJob.status == "Completed"
        )
    if params.queue:
        # filter out completed.  maybe someday hide cancelled.
        query = query.where(VerificationJob.status != "Completed")
    if params.status and len(list(filter(None, params.status))) > 0:
        query = query.where(VerificationJob.status.in_(params.status))
    if params.workflow_id:
        query = query.where(VerificationJob.workflow_id == params.workflow_id)
    if params.user_id:
        query = query.where(VerificationJob.user_id.in_(params.user_id))
    if params.assigned_user:
        assigned_user_subquery = (
            select(User.id)
            .where(
                func.concat(User.first_name, ' ', User.last_name).in_(
                    params.assigned_user
                )
            )
            .distinct()
        )
        query = query.where(VerificationJob.user_id.in_(assigned_user_subquery))
    if params.container_type:
        subquery = (
            select(ContainerType.id)
            .where(ContainerType.type == params.container_type)
            .distinct()
        )
        query = query.where(VerificationJob.container_type_id == subquery)
    if params.trayed is not None:
        query = query.where(VerificationJob.trayed == params.trayed)
    if params.created_by_id:
        query = query.where(VerificationJob.created_by_id == params.created_by_id)
    if params.from_dt:
        query = query.where(VerificationJob.create_dt >= params.from_dt)
    if params.to_dt:
        query = query.where(VerificationJob.create_dt <= params.to_dt)

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        sorter = BaseSorter(VerificationJob)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=VerificationJobDetailOutput)
def get_verification_job_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the verification job detail for the given ID.

    **Args:**
    - ID: The ID of the verification job.

    **Returns:**
    - Verification Job Detail Output: The verification job detail.

    **Raises:**
    - HTTPException: If the verification job with the given ID is not found.
    """
    verification_job = session.get(VerificationJob, id)

    if verification_job:
        return verification_job

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.get("/workflow/{id}", response_model=VerificationJobDetailOutput)
def get_verification_job_detail_by_workflow(
    id: int, session: Session = Depends(get_session)
):
    """
    Retrieves the verification job detail for the given workflow ID.

    **Args:**
    - ID: The ID of the verification job workflow.

    **Returns:**
    - Verification Job Detail Output: The verification job detail.

    **Raises:**
    - HTTPException: If the verification job with the given ID is not found.
    """
    verification_job = session.exec(
        select(VerificationJob).where(VerificationJob.workflow_id == id)
    ).first()

    if verification_job:
        return verification_job

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.post("/", response_model=VerificationJobDetailOutput, status_code=201)
def create_verification_job(
    verification_job_input: VerificationJobInput,
    session: Session = Depends(get_session),
):
    """
    Create a new verification job:

    **Args:**
    - Verification Job Input: The input data for the
    verification job.

    **Returns:**
    - Verification Job Detail Output: The created verification job.
    """
    try:
        verification_job = VerificationJob(**verification_job_input.model_dump())

        session.add(verification_job)
        session.commit()
        session.refresh(verification_job)

        return verification_job

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=VerificationJobDetailOutput)
def update_verification_job(
    id: int,
    verification_job: VerificationJobUpdateInput,
    session: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
):
    """
    Update a verification job:

    **Args:**
    - id: The ID of the verification job to update.
    - Verification Job Update Input: The updated data for the verification job.

    **Returns:**
    - Verification Job Detail Output: The updated verification job.

    **Raises:**
    - HTTPException: If the verification job with the given ID does not exist.
    """
    try:
        existing_verification_job = session.get(VerificationJob, id)

        # capture original status for process check
        original_status = existing_verification_job.status

        # Check if the tray record exists
        if not existing_verification_job:
            raise NotFound(detail=f"Verification Job ID {id} Not Found")

        # Update the tray record with the mutated data
        mutated_data = verification_job.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            if (key in ["media_type_id", "size_class_id"] and
                existing_verification_job.__getattribute__(key) != value):
                background_tasks.add_task(
                    manage_verification_job_change_action(
                        session, existing_verification_job, key, value
                    )
                )

            setattr(existing_verification_job, key, value)

        setattr(existing_verification_job, "update_dt", datetime.now(timezone.utc))

        existing_verification_job = commit_record(session, existing_verification_job)

        if mutated_data.get("status") == "Completed":
            background_tasks.add_task(
                complete_verification_job, session, existing_verification_job
            )
        else:
            background_tasks.add_task(
                manage_verification_job_transition,
                session,
                existing_verification_job,
                original_status,
            )

            session.refresh(existing_verification_job)

        return existing_verification_job

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/{id}")
def delete_verification_job(id: int, session: Session = Depends(get_session)):
    """
    Delete a verification job by its ID.

    **Args:**
    - id: The ID of the verification job to delete.

    **Returns:**
    - HTTPException: An HTTP exception indicating the result of the deletion.
    """
    verification_job = session.get(VerificationJob, id)

    if verification_job:
        # do not allow deletion of completed jobs
        if verification_job.status == 'Completed':
            return HTTPException(
                status_code=400,
                detail=f"Verification Job id {id} is complete. Can't delete or cancel completed jobs.",
            )

        # find and reset underlying accession job
        acc_job = session.get(AccessionJob, verification_job.accession_job_id)
        acc_job.status = 'Paused'
        session.add(acc_job)

        if verification_job.container_type_id == 1:
            trays_in_ver_job_query = select(Tray).where(Tray.verification_job_id == id)
            trays = session.exec(trays_in_ver_job_query)
            for tray in trays:
                tray.scanned_for_verification = False
                tray.verification_job_id = None
                tray.collection_verified = False
                session.add(tray)
                # sanitize items in tray
                for item in session.exec(select(Item).where(Item.verification_job_id == id)):
                    item.scanned_for_verification = False
                    item.verification_job_id = None
                    session.add(item)
        else:
            non_trays_in_ver_job_query = select(NonTrayItem).where(
                NonTrayItem.verification_job_id == id
            )
            non_tray_items = session.exec(non_trays_in_ver_job_query)
            for non_tray_item in non_tray_items:
                non_tray_item.scanned_for_verification = False
                non_tray_item.verification_job_id = None
                session.add(non_tray_item)

        try:
            session.commit()
        except Exception as e:
            return HTTPException(
                status_code=500,
                detail=f"{e}",
            )

        session.delete(verification_job)
        session.commit()

        return HTTPException(
            status_code=204,
            detail=f"Verification Job id {id} Deleted Successfully",
        )

    raise NotFound(detail=f"Verification Job ID {id} Not Found")


@router.patch("/{id}/add", response_model=VerificationJobDetailOutput)
def add_item_to_verification_job(
    id: int,
    input: VerificationJobAddInput,
    session: Session = Depends(get_session)
):
    """
    Add an item to a verification job.

    **Args:**
    - id: The ID of the verification job.
    - item_id: The ID of the item to add.

    **Returns:**
    - Verification Job Detail Output: The updated verification job.
    """

    verification_job = session.get(VerificationJob, id)

    if not verification_job:
        raise NotFound(detail=f"Verification Job ID {id} Not Found")

    barcode = (
        session.query(Barcode).filter(Barcode.value == input.barcode_value).first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode with value {input.barcode_value} Not Found")

    tray = session.query(Tray).filter(Tray.barcode_id == barcode.id).first()
    item = session.query(Item).filter(Item.barcode_id == barcode.id).first()
    non_tray_item = (
        session.query(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id).first()
    )

    if not tray and not item and not non_tray_item:
        raise NotFound(detail=f"Item with barcode value {input.barcode_value} Not "
                              f"Found")
    if tray:
        new_verification_changes = []
        items = tray.items
        if items:
            for item in items:
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=barcode.value,
                    item_barcode_value=item_barcode.value,
                    change_type="Added",
                    completed_by_id=verification_job.user_id
                ))
        session.bulk_save_objects(new_verification_changes)
        session.commit()
    elif item:
        tray_barcode = session.query(Barcode).join(Tray, Barcode.id == Tray.barcode_id).filter(Tray.id == item.tray_id).first()
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            tray_barcode_value=tray_barcode.value,
            item_barcode_value=barcode.value,
            change_type="Added",
            completed_by_id=verification_job.user_id
        )
        commit_record(session, new_verification_change)
    else:
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            item_barcode_value=barcode.value,
            change_type="Added",
            completed_by_id=verification_job.user_id
        )
        commit_record(session, new_verification_change)

    verification_job.update_dt = datetime.now(timezone.utc)
    session.refresh(verification_job)

    return verification_job


@router.patch("/{id}/remove", response_model=VerificationJobDetailOutput)
def remove_item_from_verification_job(
    id: int,
    input: VerificationJobRemoveInput,
    session: Session = Depends(get_session)
):
    """
    Remove an item from a verification job.

    **Args:**
    - id: The ID of the verification job.
    - item_id: The ID of the item to remove.

    **Returns:**
    - Verification Job Detail Output: The updated verification job.
    """
    verification_job = session.get(VerificationJob, id)

    if not verification_job:
        raise NotFound(detail=f"Verification Job ID {id} Not Found")

    barcode = (
        session.query(Barcode).filter(Barcode.value == input.barcode_value).first()
    )

    if not barcode:
        raise NotFound(detail=f"Barcode with value {input.barcode_value} Not Found")

    tray = session.query(Tray).filter(Tray.barcode_id == barcode.id).first()
    item = session.query(Item).filter(Item.barcode_id == barcode.id).first()
    non_tray_item = (
        session.query(NonTrayItem).filter(NonTrayItem.barcode_id == barcode.id).first()
    )

    if not tray and not item and not non_tray_item:
        raise NotFound(detail=f"Item with barcode value {input.barcode_value} Not "
                              f"Found")
    if tray:
        new_verification_changes = []
        items = tray.items
        if items:
            for item in items:
                item_barcode = session.get(Barcode, item.barcode_id)
                new_verification_changes.append(VerificationChange(
                    workflow_id=verification_job.workflow_id,
                    tray_barcode_value=barcode.value,
                    item_barcode_value=item_barcode.value,
                    change_type="Removed",
                    completed_by_id=verification_job.user_id
                ))
        session.bulk_save_objects(new_verification_changes)
        session.commit()
    elif item:
        tray_barcode = session.query(Barcode).join(Tray, Barcode.id ==
                                        Tray.barcode_id).filter(Tray.id ==
                                                         item.tray_id).first()
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            tray_barcode_value=tray_barcode.value,
            item_barcode_value=barcode.value,
            change_type="Removed",
            completed_by_id=verification_job.user_id
        )
        commit_record(session, new_verification_change)
    else:
        new_verification_change = VerificationChange(
            workflow_id=verification_job.workflow_id,
            item_barcode_value=barcode.value,
            change_type="Removed",
            completed_by_id=verification_job.user_id
        )
        commit_record(session, new_verification_change)

    verification_job.update_dt = datetime.now(timezone.utc)
    session.refresh(verification_job)

    return verification_job
