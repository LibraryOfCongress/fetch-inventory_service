# /code/app/routers/batch_upload.py - REFACRORED TO SQLALCHEMY V2

import csv
import re
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, Form, BackgroundTasks
from fastapi_pagination import Page
# CRITICAL FIX: Changed from .ext.sqlmodel to .ext.sqlalchemy
from fastapi_pagination.ext.sqlalchemy import paginate
# CRITICAL FIX: Replaced from sqlmodel import Session, select
from sqlalchemy.orm import Session # Session is imported from sqlalchemy.orm now
from sqlalchemy import select, update, insert, text, not_, or_, func # select/update imported from sqlalchemy now
from io import StringIO
import pandas as pd
from starlette import status
from starlette.responses import JSONResponse, StreamingResponse
from pydantic import TypeAdapter, ValidationError


from app.database.session import get_session, commit_record, session_manager
from app.filter_params import SortParams, BatchUploadParams

from app.logger import inventory_logger
from app.models.barcode_types import BarcodeType
from app.models.barcodes import Barcode
from app.models.batch_upload import BatchUpload, BatchUploadStatus
from app.models.container_types import ContainerType
from app.models.ladders import Ladder
from app.models.owners import Owner
from app.models.requests import Request
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.non_tray_items import NonTrayItem
from app.models.users import User
from app.models.withdraw_jobs import WithdrawJob
from app.schemas.batch_upload import (
    BatchUploadListOutput,
    BatchUploadDetailOutput,
    BatchUploadUpdateInput,
    LocationManagementSpreadSheetInput,
)
from app.sorting import BaseSorter
from app.utilities import (
    validate_request_data,
    process_request_data,
    process_withdraw_job_data,
    start_session_with_audit_info,
)
from app.config.exceptions import (
    BadRequest,
    NotFound,
    InternalServerError,
)

from app.auth.dependencies import RequiresPermission

router = APIRouter(
    prefix="/batch-upload",
    tags=["batch upload"],
    dependencies=[Depends(RequiresPermission("can_perform_batch_uploads"))],
)


@router.get("/", response_model=Page[BatchUploadListOutput])
async def get_batch_upload(
    session: Session = Depends(get_session),
    batch_upload_type: str | None = None,
    uploaded_by: str | None = None,
    params: BatchUploadParams = Depends(),
    sort_params: SortParams = Depends(),
) -> list:
    """
    Batch upload endpoint to process barcodes for different operations.
    """
    query = select(BatchUpload)

    if batch_upload_type:
        if batch_upload_type == "request":
            query = query.where(BatchUpload.withdraw_job_id.is_(None))
        elif batch_upload_type == "withdraw":
            query = query.where(BatchUpload.withdraw_job_id.isnot(None))
    if uploaded_by:
        uploaded_by_subquery = select(User.id).where(User.email == uploaded_by).scalar_subquery()
        query = query.where(BatchUpload.user_id == uploaded_by_subquery)

    if params.status:
        query = query.where(BatchUpload.status.in_(params.status))
    if params.user_id:
        query = query.where(BatchUpload.user_id.in_(params.user_id))
    if params.withdraw_job_id:
        query = query.where(BatchUpload.withdraw_job_id == params.withdraw_job_id)
    if params.file_name:
        query = query.where(BatchUpload.file_name == params.file_name)
    if params.file_type:
        query = query.where(BatchUpload.file_type.in_(params.file_type))

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using RequestSorter
        sorter = BaseSorter(BatchUpload)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=BatchUploadDetailOutput)
async def get_batch_upload_detail(id: int, session: Session = Depends(get_session)):
    """
    Batch upload endpoint to process barcodes for different operations.
    """
    if not id:
        raise BadRequest(detail="Batch Upload ID is required")

    batch_upload = session.get(BatchUpload, id)
    if not batch_upload:
        raise NotFound(detail=f"Batch Upload ID {id} not found")

    return batch_upload


@router.delete("/{id}", status_code=204, dependencies=[Depends(RequiresPermission("delete_requests"))])
async def delete_batch_upload(id: int, session: Session = Depends(get_session)):
    """
    Delete a batch upload and all associated requests.
    
    Business Rules:
    - Status must be New, Processing, or Uploaded
    - No requests can be on a pick list
    - Cascades to delete all requests
    - Items return to 'In' status
    """
    if not id:
        raise BadRequest(detail="Batch Upload ID is required")

    batch_upload = session.get(BatchUpload, id)

    if not batch_upload:
        raise NotFound(detail=f"Batch Upload ID {id} not found")

    # Validation 1: Check status
    allowed_statuses = [BatchUploadStatus.New, BatchUploadStatus.Processing, BatchUploadStatus.Uploaded]
    if batch_upload.status not in allowed_statuses:
        raise BadRequest(
            detail=f"Cannot delete batch upload with status '{batch_upload.status}'. Only 'New', 'Processing', or 'Uploaded' batches can be deleted."
        )

    # Validation 2: Check if any requests are on a pick list
    requests_on_picklist = session.execute(
        select(Request).where(
            Request.batch_upload_id == id,
            Request.pick_list_id.isnot(None)
        )
    ).scalars().all()

    if requests_on_picklist:
        raise BadRequest(
            detail=f"Cannot delete batch upload. {len(requests_on_picklist)} request(s) are already added to a pick list."
        )

    # Get all requests for this batch
    batch_requests = session.execute(
        select(Request).where(Request.batch_upload_id == id)
    ).scalars().all()

    # Get all items from these requests and reset status to "In"
    from app.models.items import Item
    from app.models.non_tray_items import NonTrayItem
    
    for request in batch_requests:
        # Handle tray items
        if request.item_id:
            item = session.get(Item, request.item_id)
            if item and item.status != "In":
                item.status = "In"
                session.add(item)
        
        # Handle non-tray items
        if request.non_tray_item_id:
            non_tray_item = session.get(NonTrayItem, request.non_tray_item_id)
            if non_tray_item and non_tray_item.status != "In":
                non_tray_item.status = "In"
                session.add(non_tray_item)
        
        # Delete the request
        session.delete(request)

    # Delete the batch upload
    session.delete(batch_upload)
    session.commit()

    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=f"Batch Upload ID {id} and {len(batch_requests)} associated request(s) have been successfully deleted",
    )


@router.patch("/location-management")
async def batch_upload_location_management_update(
    file: UploadFile,
    session: Session = Depends(get_session),
):
    """
    Batch upload endpoint to process bulk updates for shelves via CSV.
    """
    if not file:
        raise BadRequest(detail="Upload File is required")

    file_name = file.filename
    file_size = file.size
    file_content_type = file.content_type
    contents = await file.read()

    # Load the file into a DataFrame
    if (
        file_name.endswith(".xlsx")
        or file_content_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        df = pd.read_excel(contents, dtype=str)
    elif file_name.endswith(".csv"):
        df = pd.read_csv(StringIO(contents.decode("utf-8")), dtype=str)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    new_batch_upload = BatchUpload(
        file_name=file_name, file_size=file_size, file_type=file_content_type
    )

    session.add(new_batch_upload)
    session.commit()
    session.refresh(new_batch_upload)

    # Sanitize DataFrame: Replace pandas NA/nan with None for SQLAlchemy compatibility
    df = df.replace({pd.NA: None, float("nan"): None, "": None})

    errors = []

    for index, row in df.iterrows():
        try:
            if not row.get("Shelf Barcode"):
                errors.append(
                    {"line": int(index) + 1, "error": "Shelf Barcode is required to identify the shelf"}
                )
                continue

            shelf_barcode_value = str(row["Shelf Barcode"]).strip()

            # Lookup shelf
            shelf = (
                session.execute(
                    select(Shelf)
                    .join(Barcode, Shelf.barcode_id == Barcode.id)
                    .filter(Barcode.value == shelf_barcode_value)
                )
                .scalars()
                .first()
            )

            if not shelf:
                errors.append(
                    {"line": int(index) + 1, "error": f"Shelf with barcode {shelf_barcode_value} not found"}
                )
                continue

            # Process optional updates
            if row.get("Owner"):
                owner_name = str(row["Owner"]).strip()
                owner = session.execute(select(Owner).filter(Owner.name == owner_name)).scalars().first()
                if not owner:
                    errors.append({"line": int(index) + 1, "error": f"Owner {owner_name} not found"})
                    continue
                shelf.owner_id = owner.id

            if row.get("Container Type"):
                ct_name = str(row["Container Type"]).strip()
                container_type = session.execute(select(ContainerType).filter(ContainerType.type == ct_name)).scalars().first()
                if not container_type:
                    errors.append({"line": int(index) + 1, "error": f"Container Type {ct_name} not found"})
                    continue
                shelf.container_type_id = container_type.id

            if row.get("Size Class") or row.get("Shelf Type"):
                # Load current size_class / shelf_type if only one is provided
                current_shelf_type = session.get(ShelfType, shelf.shelf_type_id)
                current_size_class_id = current_shelf_type.size_class_id
                current_size_class = session.get(SizeClass, current_size_class_id)
                
                size_class_name = str(row["Size Class"]).strip() if row.get("Size Class") else current_size_class.name
                shelf_type_name = str(row["Shelf Type"]).strip() if row.get("Shelf Type") else current_shelf_type.type

                shelf_type = (
                    session.execute(select(ShelfType)
                    .join(SizeClass)
                    .filter(SizeClass.name == size_class_name)
                    .filter(ShelfType.type == shelf_type_name))
                    .scalars()
                    .first()
                )
                if not shelf_type:
                    errors.append({"line": int(index) + 1, "error": f"Shelf Type {shelf_type_name} with Size Class {size_class_name} not found"})
                    continue
                
                # Resize shelf positions if capacity changed
                if shelf.shelf_type_id != shelf_type.id:
                    old_capacity = current_shelf_type.max_capacity if current_shelf_type else 0
                    new_capacity = shelf_type.max_capacity

                    # Path 1: Decreasing capacity
                    if new_capacity < old_capacity:
                        num_to_remove = old_capacity - new_capacity
                        positions_to_check_query = (
                            select(ShelfPosition)
                            .where(ShelfPosition.shelf_id == shelf.id)
                            .order_by(ShelfPosition.position_number.desc())
                            .limit(num_to_remove)
                        )
                        positions_to_delete = session.execute(positions_to_check_query).scalars().all()
                        position_ids_to_delete = [p.id for p in positions_to_delete]

                        if position_ids_to_delete:
                            occupied_tray = session.execute(select(Tray.id).where(Tray.shelf_position_id.in_(position_ids_to_delete)).limit(1)).first()
                            occupied_non_tray = session.execute(select(NonTrayItem.id).where(NonTrayItem.shelf_position_id.in_(position_ids_to_delete)).limit(1)).first()

                            if occupied_tray or occupied_non_tray:
                                errors.append({"line": int(index) + 1, "error": f"Cannot resize Shelf {shelf_barcode_value} - positions being removed are occupied"})
                                continue

                            for pos in positions_to_delete:
                                session.delete(pos)

                    # Path 2: Increasing capacity
                    elif new_capacity > old_capacity:
                        new_position_numbers_range = list(range(old_capacity + 1, new_capacity + 1))
                        for position_num in new_position_numbers_range:
                            new_position = ShelfPosition(
                                shelf_id=shelf.id,
                                position_number=position_num,
                            )
                            session.add(new_position)

                shelf.shelf_type_id = shelf_type.id
                
                # Re-calculate available space
                if hasattr(shelf, 'calc_available_space'):
                    session.flush()
                    shelf.calc_available_space(session=session)

            if row.get("Width"):
                shelf.width = float(row["Width"])
            if row.get("Height"):
                shelf.height = float(row["Height"])
            if row.get("Depth"):
                shelf.depth = float(row["Depth"])
            if row.get("Location Logical Order"):
                shelf.sort_priority = int(row["Location Logical Order"])

            session.add(shelf)

        except HTTPException:
            raise
        except Exception as e:
            errors.append({"line": int(index) + 1, "error": str(e)})

    if errors:
        session.rollback()

        new_batch_upload.status = "Failed"
        session.add(new_batch_upload)
        session.commit()

        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=errors)

    # Commit all shelf modifications
    session.commit()

    # Update batch upload status
    new_batch_upload.status = "Completed"
    session.add(new_batch_upload)
    session.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK, content="Batch Upload Update Successful"
    )

@router.patch("/{id}", response_model=BatchUploadDetailOutput)
async def update_batch_upload(
    id: int,
    batch_upload: BatchUploadUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Batch upload endpoint to process barcodes for different operations.
    """
    if not id:
        raise BadRequest(detail="Batch Upload ID is required")

    existing_batch_upload = session.get(BatchUpload, id)
    if not existing_batch_upload:
        raise NotFound(detail=f"Batch Upload ID {id} not found")

    mutated_data = batch_upload.model_dump(exclude_unset=True)

    for key, value in mutated_data.items():
        setattr(existing_batch_upload, key, value)

    setattr(existing_batch_upload, "update_dt", datetime.now(timezone.utc))

    session.add(existing_batch_upload)
    session.commit()
    session.refresh(existing_batch_upload)

    return existing_batch_upload


@router.post("/request")
async def batch_upload_request(
    file: UploadFile, requested_by_id: int = Form(None), session: Session = Depends(get_session)
):
    """
    Batch upload endpoint to process barcodes for different operations.
    """
    try:
        file_name = file.filename
        file_size = file.size
        file_content_type = file.content_type
        contents = await file.read()

        if (
            file_name.endswith(".xlsx")
            or file_content_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            df = pd.read_excel(
                contents,
                dtype={
                    "Item Barcode": str,
                    "External Request ID": str,
                    "Requestor Name": str,
                    "Request Type": str,
                    "Priority": str,
                    "Delivery Location": str,
                },
            )
        if file_name.endswith(".csv") or file_content_type == "text/csv":
            df = pd.read_csv(
                StringIO(contents.decode("utf-8")),
                dtype={
                    "Item Barcode": str,
                    "External Request ID": str,
                    "Requestor Name": str,
                    "Request Type": str,
                    "Priority": str,
                    "Delivery Location": str,
                },
            )

        df = df.dropna(subset=["Item Barcode"])

        df.fillna(
            {
                "External Request ID": "",
                "Priority": "",
                "Requestor Name": "",
                "Request Type": "",
                "Delivery Location": "",
            },
            inplace=True,
        )

        new_batch_upload = BatchUpload(
            file_name=file_name,
            file_size=file_size,
            file_type=file_content_type,
            user_id=requested_by_id,
        )

        session.add(new_batch_upload)
        session.commit()
        session.refresh(new_batch_upload)

        update_dt = datetime.now(timezone.utc)

        # Check if the necessary column exists
        if "Item Barcode" not in df.columns:
            # V2 UPDATE FIX: session.execute(update(Model).where(conditions).values(updates))
            session.execute(
                update(BatchUpload)
                .where(BatchUpload.id == new_batch_upload.id)
                .values(status="Failed", update_dt=update_dt)
            )
            raise BadRequest(detail="Excel file must contain a 'Item Barcode' column.")

        df["Item Barcode"] = df["Item Barcode"].astype(str)

        # V2 UPDATE FIX
        session.execute(
            update(BatchUpload)
            .where(BatchUpload.id == new_batch_upload.id)
            .values(status="Processing", update_dt=update_dt)
        )

        validated_df, errored_df, errors = validate_request_data(session, df)
        # Process the request data
        if validated_df.empty or errors.get("errors"):
            
            # V2 UPDATE FIX
            session.execute(
                update(BatchUpload)
                .where(BatchUpload.id == new_batch_upload.id)
                .values(status="Failed", update_dt=update_dt)
            )
            session.commit()

            if errors.get("errors"):
                error_list = errors.get("errors")
                # Create an in-memory CSV
                output = StringIO()
                writer = csv.writer(output)
                # Write headers (optional: use column names dynamically)
                writer.writerow(["Line Item", "Item Barcode", "Error"])

                # Write rows
                for row in error_list:
                    writer.writerow(
                        [
                            row.get("line"),
                            row.get("barcode_value"),
                            row.get("error"),
                        ]
                    )

                # Reset the buffer position
                output.seek(0)
                content = f"attachment; filename=error_request_batch_upload_{new_batch_upload.id}_{update_dt}.csv"

                # Create a StreamingResponse
                return StreamingResponse(
                    output,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    media_type="text/csv",
                    headers={"Content-Disposition": content},
                )

            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"""Unable to process Request batch upload ID:
                 {new_batch_upload.id}""",
            )

        # Process the request data
        request_df, request_instances = process_request_data(
            session, validated_df, new_batch_upload.id, requested_by_id
        )

        session.bulk_save_objects(request_instances)

        # V2 UPDATE FIX
        session.execute(
            update(BatchUpload)
            .where(BatchUpload.id == new_batch_upload.id)
            .values(status=BatchUploadStatus.Uploaded, update_dt=datetime.now(timezone.utc))
        )
        session.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content="Batch upload successful"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError(detail=str(f"Request BatchUpload Error: {e}"))


@router.post("/withdraw-jobs/{job_id}")
async def batch_upload_withdraw_job(
    job_id: int, file: UploadFile, session: Session = Depends(get_session)
):
    """
    Batch upload endpoint to process barcodes for different operations.
    """
    try:
        if not job_id:
            raise BadRequest(detail="Withdraw Job ID is required")

        file_name = file.filename
        file_size = file.size
        file_content_type = file.content_type
        contents = await file.read()

        if (
            file_name.endswith(".xlsx")
            or file_content_type
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ):
            df = pd.read_excel(
                contents,
                dtype={"Item Barcode": str, "Tray Barcode": str},
            )
        if file_name.endswith(".csv"):
            df = pd.read_csv(
                StringIO(contents.decode("utf-8")),
                dtype={"Item Barcode": str, "Tray Barcode": str},
            )

        # Check if the necessary column exists
        withdraw_job = session.get(WithdrawJob, job_id)

        if not withdraw_job:
            raise NotFound(detail=f"Withdraw job id {job_id} not found")

        # Create a new batch upload
        new_batch_upload = BatchUpload(
            file_name=file_name,
            file_size=file_size,
            file_type=file_content_type,
            type="Withdraw",
            withdraw_job_id=withdraw_job.id,
        )

        session.add(new_batch_upload)
        session.commit()
        session.refresh(new_batch_upload)

        # Remove rows with NaN values in 'Item Barcode' and 'Tray Barcode'
        df = df.dropna(subset=["Item Barcode", "Tray Barcode"], how="all")

        if not withdraw_job:
            # V2 UPDATE FIX
            session.execute(
                update(BatchUpload)
                .where(BatchUpload.id == new_batch_upload.id)
                .values(status="Failed", update_dt=datetime.now(timezone.utc))
            )
            session.commit()
            raise NotFound(detail=f"Withdraw job id {job_id} not found")

        if "Item Barcode" not in df.columns and "Tray Barcode" not in df.columns:
            # V2 UPDATE FIX
            session.execute(
                update(BatchUpload)
                .where(BatchUpload.id == new_batch_upload.id)
                .values(status="Failed", update_dt=datetime.now(timezone.utc))
            )
            session.commit()
            raise BadRequest(
                detail="Batch file must contain a 'Item Barcode' or 'Tray "
                "Barcode' columns."
            )

        # Drop NaN and empty string values
        item_df = df["Item Barcode"].replace("", pd.NA).dropna()

        # Reset the index if necessary
        item_df.reset_index(drop=True, inplace=True)

        # Create DataFrame
        item_df = pd.DataFrame(item_df)
        # rename columns
        item_df.rename(columns={"Item Barcode": "Barcode"}, inplace=True)

        lookup_barcode_values = []
        if not item_df["Barcode"].empty:
            lookup_barcode_values.extend(item_df["Barcode"].astype(str).tolist())

        if not lookup_barcode_values:
            # V2 UPDATE FIX
            session.execute(
                update(BatchUpload)
                .where(BatchUpload.id == new_batch_upload.id)
                .values(status="Failed", update_dt=datetime.now(timezone.utc))
            )
            raise NotFound(
                detail="All barcodes are invalid to process bulk withdraw upload. Please check your barcodes and try again."
            )

        # V2 UPDATE FIX
        session.execute(
            update(BatchUpload)
            .where(BatchUpload.id == new_batch_upload.id)
            .values(status="Processing", update_dt=datetime.now(timezone.utc))
        )
        session.commit()

        lookup_barcode_values = list(set(lookup_barcode_values))
        # V2 FIX: session.query().filter().all() -> session.execute(select(...)).scalars().all()
        barcodes = (
            session.execute(select(Barcode)
            .filter(Barcode.value.in_(lookup_barcode_values)))
            .scalars()
            .all()
        )

        found_barcodes = set(barcode.value for barcode in barcodes)
        missing_barcodes = set(lookup_barcode_values) - found_barcodes

        errored_barcodes = {"errors": []}

        for barcode in missing_barcodes:
            index = item_df.index[item_df["Barcode"] == barcode].tolist()
            if index:
                errored_barcodes["errors"].append(
                    {
                        "line": index[0] + 1,
                        "error": f"Barcode value {barcode} not found",
                    }
                )

        if not barcodes:
            # V2 UPDATE FIX
            session.execute(
                update(BatchUpload)
                .where(BatchUpload.id == new_batch_upload.id)
                .values(status="Failed", update_dt=datetime.now(timezone.utc))
            )
            session.commit()
            raise BadRequest(
                detail="All barcodes are invalid to process bulk withdraw upload. Please check your barcodes and try again."
            )

        (
            withdraw_items,
            withdraw_non_tray_items,
            withdraw_trays,
            errored_barcodes_from_processing,
        ) = process_withdraw_job_data(session, withdraw_job.id, barcodes, df)

        errored_barcodes["errors"].extend(
            errored_barcodes_from_processing.get("errors", [])
        )

        if not withdraw_items and not withdraw_non_tray_items and not withdraw_trays:
            if not errored_barcodes.get("errors"):
                # V2 UPDATE FIX
                session.execute(
                    update(BatchUpload)
                    .where(BatchUpload.id == new_batch_upload.id)
                    .values(status="Failed", update_dt=datetime.now(timezone.utc))
                )
                session.commit()
                raise NotFound(
                    detail="All barcodes are invalid to process bulk withdraw upload. Please check your barcodes and try again."
                )
            else:
                # V2 UPDATE FIX
                session.execute(
                    update(BatchUpload)
                    .where(BatchUpload.id == new_batch_upload.id)
                    .values(status="Failed", update_dt=datetime.now(timezone.utc))
                )
                session.commit()
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST, content=errored_barcodes
                )

        # V2 UPDATE FIX
        session.execute(
            update(BatchUpload)
            .where(BatchUpload.id == new_batch_upload.id)
            .values(status="Completed", update_dt=datetime.now(timezone.utc))
        )

        if withdraw_trays:
            session.bulk_save_objects(withdraw_trays)
        if withdraw_items:
            session.bulk_save_objects(withdraw_items)
        if withdraw_non_tray_items:
            session.bulk_save_objects(withdraw_non_tray_items)

        session.commit()
        session.refresh(withdraw_job)

        if errored_barcodes.get("errors"):
            return JSONResponse(
                status_code=status.HTTP_200_OK, content=errored_barcodes
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content="Batch Upload Successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        inventory_logger.error(f"Batch Upload Internal Server Error: {e}")
        raise InternalServerError(detail=f"Internal Server Error: {e}")


def _process_location_upload(
    batch_upload_id: int,
    side_id: int,
    new_ladder_specs: list,
    shelf_payload: list,
    shelf_barcode_type_id,
    audit_info: dict,
):
    """Background worker: perform the validated location inserts and record the
    outcome on the BatchUpload row. Runs in a threadpool (sync def) so the slow
    DB writes never block the event loop or trip gunicorn's worker timeout. All
    inputs are plain data, so this uses its own fresh session.
    """
    try:
        with session_manager() as session:
            start_session_with_audit_info(audit_info, session)

            # Resolve ladders: existing on this side + create the new ones.
            ladders_by_number = {
                ladder.ladder_number: ladder
                for ladder in session.execute(
                    select(Ladder).filter(Ladder.side_id == side_id)
                ).scalars().all()
            }
            for spec in new_ladder_specs:
                if spec["ladder_number"] not in ladders_by_number:
                    ladder = Ladder(
                        ladder_number=spec["ladder_number"],
                        sort_priority=spec["sort_priority"],
                        side_id=side_id,
                    )
                    session.add(ladder)
                    ladders_by_number[spec["ladder_number"]] = ladder
            session.flush()  # assign ladder ids

            # Build barcodes + shelves.
            shelf_objs = []  # (Shelf, max_capacity)
            for s in shelf_payload:
                barcode = None
                if s["barcode_value"] is not None:
                    barcode = Barcode(value=s["barcode_value"], type_id=shelf_barcode_type_id)
                    session.add(barcode)
                shelf = Shelf(
                    height=s["height"],
                    width=s["width"],
                    depth=s["depth"],
                    sort_priority=s["shelf_sort_priority"],
                    container_type_id=s["container_type_id"],
                    shelf_number=s["shelf_number"],
                    shelf_type_id=s["shelf_type_id"],
                    owner_id=s["owner_id"],
                    ladder=ladders_by_number[s["ladder_number"]],
                    barcode=barcode,
                    available_space=s["max_capacity"],
                )
                session.add(shelf)
                shelf_objs.append((shelf, s["max_capacity"]))
            session.flush()  # assign shelf/barcode ids

            # Positions via a Core executemany insert (the bulk of the rows).
            position_rows = [
                {"shelf_id": shelf.id, "position_number": n}
                for shelf, cap in shelf_objs
                for n in range(1, cap + 1)
            ]
            if position_rows:
                session.execute(insert(ShelfPosition), position_rows)

            batch_upload = session.get(BatchUpload, batch_upload_id)
            if batch_upload:
                batch_upload.status = BatchUploadStatus.Completed
                batch_upload.result = {
                    "message": f"Batch upload successful: {len(shelf_objs)} shelves created.",
                    "shelves_created": len(shelf_objs),
                    "error_count": 0,
                    "errors": [],
                }
                session.add(batch_upload)
            session.commit()
    except Exception as e:
        inventory_logger.error(
            f"Batch location upload {batch_upload_id} failed in background: {e}"
        )
        # Record the failure on the job so the frontend poll surfaces it.
        try:
            with session_manager() as session:
                batch_upload = session.get(BatchUpload, batch_upload_id)
                if batch_upload:
                    batch_upload.status = BatchUploadStatus.Failed
                    batch_upload.result = {
                        "message": "Processing failed while creating locations.",
                        "error_count": 1,
                        "errors": [{"line": None, "error": str(e)}],
                    }
                    session.add(batch_upload)
                    session.commit()
        except Exception as inner:
            inventory_logger.error(
                f"Could not record failure for batch upload {batch_upload_id}: {inner}"
            )


@router.post("/location-management")
async def batch_upload_location_management(
    file: UploadFile,
    building_id: int = Form(),
    module_id: int = Form(),
    aisle_id: int = Form(),
    side_id: int = Form(),
    background_tasks: BackgroundTasks = None,
    session: Session = Depends(get_session),
):
    """
    Validate a location bulk-upload synchronously (instant row-level errors),
    then hand the actual inserts to a background task so the request returns
    immediately. The frontend polls GET /batch-upload/{id} for the result.
    """
    if not building_id:
        raise BadRequest(detail="Building ID is required")

    if not module_id:
        raise BadRequest(detail="Module ID is required")

    if not aisle_id:
        raise BadRequest(detail="Aisle ID is required")

    if not side_id:
        raise BadRequest(detail="Side ID is required")

    if not file:
        raise BadRequest(detail="Upload File is required")

    if not file:
        raise HTTPException(status_code=400, detail="Upload file is required")

    file_name = file.filename
    file_size = file.size
    file_content_type = file.content_type
    contents = await file.read()

    # Load the file into a DataFrame
    if (
        file_name.endswith(".xlsx")
        or file_content_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        df = pd.read_excel(
            contents,
            dtype={
                "Ladder Number": int,
                "Ladder Sort Priority": int,
                "Shelf Number": int,
                "Shelf Sort Priority": int,
                "Owner": str,
                "Size Class": str,
                "Container Type": str,
                "Shelf Type": str,
                "Width": float,
                "Height": float,
                "Depth": float,
                "Shelf Barcode": str,
            },
        )
    elif file_name.endswith(".csv"):
        df = pd.read_csv(
            StringIO(contents.decode("utf-8")),
            dtype={
                "Ladder Number": int,
                "Ladder Sort Priority": "Int64",
                "Shelf Number": "Int64",
                "Shelf Sort Priority": "Int64",
                "Owner": str,
                "Size Class": str,
                "Container Type": str,
                "Shelf Type": str,
                "Width": float,
                "Height": float,
                "Depth": float,
                "Shelf Barcode": str,
            },
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    new_batch_upload = BatchUpload(
        file_name=file_name, file_size=file_size, file_type=file_content_type
    )

    session.add(new_batch_upload)
    session.commit()
    session.refresh(new_batch_upload)

    df.rename(
        columns={
            "Ladder Number": "ladder_number",
            "Ladder Sort Priority": "ladder_sort_priority",
            "Shelf Number": "shelf_number",
            "Shelf Sort Priority": "shelf_sort_priority",
            "Owner": "owner",
            "Size Class": "size_class",
            "Container Type": "container_type",
            "Shelf Type": "shelf_type",
            "Width": "width",
            "Height": "height",
            "Depth": "depth",
            "Shelf Barcode": "shelf_barcode",
        },
        inplace=True,
    )

    # Validate the data from dataframe using pydantic TypeAdapter
    try:
        location_hierarchy_adapter = TypeAdapter(
            List[LocationManagementSpreadSheetInput]
        )
        location_hierarchy_adapter.validate_json(df.to_json(orient="records"))
    except ValidationError as e:
        new_batch_upload.status = "Failed"
        session.add(new_batch_upload)
        session.commit()
        session.refresh(new_batch_upload)
        errors = [
            {"loc": err["loc"], "msg": err["msg"], "type": err["type"]}
            for err in e.errors()
        ]
        raise HTTPException(status_code=422, detail=errors)

    # ---- Pre-load all reference data ONCE. The original ran ~6 SELECTs per row
    # (owner, container type, size class, shelf type, existing shelf, barcode) ->
    # ~6k queries for 1k rows. Everything below now resolves from these maps. ----
    owners_by_name = {
        o.name: o for o in session.execute(select(Owner)).scalars().all()
    }
    container_types_by_type = {
        c.type: c for c in session.execute(select(ContainerType)).scalars().all()
    }
    size_classes_by_name = {
        s.name: s for s in session.execute(select(SizeClass)).scalars().all()
    }
    # Shelf type is identified by (size_class, type) -- mirrors the original join.
    shelf_types_by_key = {
        (st.size_class_id, st.type): st
        for st in session.execute(select(ShelfType)).scalars().all()
    }
    shelf_barcode_type = (
        session.execute(select(BarcodeType).filter(BarcodeType.name == "Shelf"))
        .scalars()
        .first()
    )

    # Sanitize DataFrame: pandas NA/nan -> None for SQLAlchemy compatibility
    df = df.replace({pd.NA: None, float("nan"): None})

    # Existing ladders on this side, keyed by ladder_number.
    ladders_by_number = {
        ladder.ladder_number: ladder
        for ladder in session.execute(
            select(Ladder).filter(Ladder.side_id == side_id)
        ).scalars().all()
    }
    # Existing (ladder_id, shelf_number) pairs on this side -> duplicate detection.
    existing_shelf_keys = set()
    if ladders_by_number:
        existing_shelf_keys = set(
            session.execute(
                select(Shelf.ladder_id, Shelf.shelf_number).filter(
                    Shelf.ladder_id.in_([l.id for l in ladders_by_number.values()])
                )
            ).all()
        )
    # Existing Shelf-barcode values that collide with this file (single scoped query).
    csv_barcode_values = [str(v) for v in df["shelf_barcode"].tolist() if pd.notna(v)]
    existing_barcode_values = set()
    if csv_barcode_values:
        existing_barcode_values = set(
            session.execute(
                select(Barcode.value)
                .join(BarcodeType, Barcode.type_id == BarcodeType.id)
                .filter(
                    BarcodeType.name == "Shelf",
                    Barcode.value.in_(csv_barcode_values),
                )
            ).scalars().all()
        )

    # Validate every row and resolve it to PLAIN data (not session-bound ORM
    # objects) so it can be handed to the background task's own session.
    shelf_payload = []          # list of plain shelf dicts
    new_ladder_specs = {}       # ladder_number -> {ladder_number, sort_priority}
    seen_shelf_keys = set()     # (ladder_number, shelf_number) created in THIS file
    seen_barcode_values = set()
    errors = []

    def _opt_int(v):
        return int(v) if pd.notna(v) else None

    def _opt_float(v):
        return float(v) if pd.notna(v) else None

    for index, row in df.iterrows():
        line = int(index) + 1
        try:
            if not row["ladder_number"]:
                errors.append({"line": line, "error": "Ladder Number is required"})
                continue

            ladder_number = int(row["ladder_number"])
            existing_ladder = ladders_by_number.get(ladder_number)
            if existing_ladder is None and ladder_number not in new_ladder_specs:
                new_ladder_specs[ladder_number] = {
                    "ladder_number": ladder_number,
                    "sort_priority": _opt_int(row["ladder_sort_priority"]),
                }

            if not pd.notna(row["shelf_number"]):
                continue
            shelf_number = int(row["shelf_number"])

            owner = owners_by_name.get(row["owner"])
            if not owner:
                errors.append({"line": line, "error": f"Owner {row['owner']} not found"})
                continue

            container_type = container_types_by_type.get(row["container_type"])
            if not container_type:
                errors.append({"line": line, "error": f"Container Type {row['container_type']} not found"})
                continue

            size_class = size_classes_by_name.get(row["size_class"])
            if not size_class:
                errors.append({"line": line, "error": f"Size Class {row['size_class']} not found"})
                continue

            shelf_type = shelf_types_by_key.get((size_class.id, row["shelf_type"]))
            if not shelf_type:
                errors.append({"line": line, "error": f"Shelf Type {row['shelf_type']} with Size Class {row['size_class']} not found"})
                continue

            # Duplicate shelf: already in the DB (existing ladder), or earlier in
            # this file. New ladders can't collide with existing shelves.
            file_key = (ladder_number, shelf_number)
            db_key = (existing_ladder.id, shelf_number) if existing_ladder else None
            if file_key in seen_shelf_keys or (db_key is not None and db_key in existing_shelf_keys):
                errors.append({"line": line, "error": f"Shelf number {shelf_number} at ladder number {ladder_number} already exists"})
                continue
            seen_shelf_keys.add(file_key)

            barcode_value = None
            if pd.notna(row["shelf_barcode"]):
                bc_value = str(row["shelf_barcode"])
                if bc_value in existing_barcode_values or bc_value in seen_barcode_values:
                    errors.append({"line": line, "error": f"Shelf Barcode value {row['shelf_barcode']} already exists"})
                    continue
                if not re.fullmatch(shelf_barcode_type.allowed_pattern, bc_value):
                    errors.append({"line": line, "error": f"Shelf Barcode value: {bc_value} is invalid for barcode rules"})
                    continue
                seen_barcode_values.add(bc_value)
                barcode_value = bc_value

            shelf_payload.append({
                "ladder_number": ladder_number,
                "shelf_number": shelf_number,
                "shelf_sort_priority": _opt_int(row["shelf_sort_priority"]),
                "height": _opt_float(row["height"]),
                "width": _opt_float(row["width"]),
                "depth": _opt_float(row["depth"]),
                "container_type_id": container_type.id,
                "shelf_type_id": shelf_type.id,
                "owner_id": owner.id,
                "max_capacity": shelf_type.max_capacity,
                "barcode_value": barcode_value,
            })

        except (ValidationError, ValueError) as e:
            errors.append({"line": line, "error": str(e)})

    # Any invalid row -> fail fast, synchronously, with ONE consolidated message
    # (the common "bad CSV" case still gives immediate, per-line feedback).
    if errors:
        new_batch_upload.status = BatchUploadStatus.Failed
        new_batch_upload.result = {
            "message": (
                f"{len(errors)} of {len(df)} rows could not be processed. "
                "No locations were created."
            ),
            "error_count": len(errors),
            "errors": errors,
        }
        session.add(new_batch_upload)
        session.commit()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=new_batch_upload.result,
        )

    # Valid: mark Processing and hand the inserts to a background task. The inserts
    # are the only part that hits the slow network path, so keeping them off the
    # request avoids the worker timeout. The frontend polls GET /batch-upload/{id}.
    new_batch_upload.status = BatchUploadStatus.Processing
    session.add(new_batch_upload)
    session.commit()

    audit_info = getattr(session, "audit_info", {"name": "System", "id": "0"})
    background_tasks.add_task(
        _process_location_upload,
        batch_upload_id=new_batch_upload.id,
        side_id=side_id,
        new_ladder_specs=list(new_ladder_specs.values()),
        shelf_payload=shelf_payload,
        shelf_barcode_type_id=(shelf_barcode_type.id if shelf_barcode_type else None),
        audit_info=dict(audit_info),
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": f"Upload accepted: processing {len(shelf_payload)} shelves in the background.",
            "batch_upload_id": new_batch_upload.id,
            "status": BatchUploadStatus.Processing.value,
        },
    )
