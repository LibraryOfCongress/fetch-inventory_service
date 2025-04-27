import csv
import re
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, Form
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi_pagination import Page
from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session, select
from io import StringIO
import pandas as pd
from starlette import status
from starlette.responses import JSONResponse, StreamingResponse

from app.database.session import get_session, commit_record
from app.filter_params import SortParams, BatchUploadParams

from app.logger import inventory_logger
from app.models.barcode_types import BarcodeType
from app.models.barcodes import Barcode
from app.models.batch_upload import BatchUpload
from app.models.container_types import ContainerType
from app.models.ladder_numbers import LadderNumber
from app.models.ladders import Ladder
from app.models.owners import Owner
from app.models.requests import Request
from app.models.shelf_numbers import ShelfNumber
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.size_class import SizeClass
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
)
from app.config.exceptions import (
    BadRequest,
    NotFound,
    InternalServerError,
)

router = APIRouter(
    prefix="/batch-upload",
    tags=["batch upload"],
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

    **Parameters:**
    - batch_upload_type (str): The type of batch upload.
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - Batch Upload Output: The paginated list of batch uploads.
    """
    query = select(BatchUpload)

    if batch_upload_type:
        if batch_upload_type == "request":
            query = query.where(BatchUpload.withdraw_job_id.is_(None))
        elif batch_upload_type == "withdraw":
            query = query.filter(BatchUpload.withdraw_job_id.isnot(None))
    if uploaded_by:
        uploaded_by_subquery = select(User.id).where(User.email == uploaded_by)
        query = query.filter(BatchUpload.user_id == uploaded_by_subquery)

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

    **Args:**
    - id: The batch upload data containing the base64 encoded Excel file.

    **Returns:**
    - BatchUploadOutput: The result of the batch processing including any errors.
    """
    if not id:
        raise BadRequest(detail="Batch Upload ID is required")

    batch_upload = session.get(BatchUpload, id)
    if not batch_upload:
        raise NotFound(detail=f"Batch Upload ID {id} not found")

    return batch_upload


@router.delete("/{id}", response_model=BatchUploadDetailOutput)
async def delete_batch_upload(id: int, session: Session = Depends(get_session)):
    """
    Batch upload endpoint to process barcodes for different operations.

    **Args:**
    - id: The batch upload data containing the base64 encoded Excel file.

    **Returns:**
    - BatchUploadOutput: The result of the batch processing including any errors.
    """
    if not id:
        raise BadRequest(detail="Batch Upload ID is required")

    batch_upload = session.get(BatchUpload, id)

    if not batch_upload:
        raise NotFound(detail=f"Batch Upload ID {id} not found")

    session.delete(batch_upload)
    session.commit()

    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=f"Batch Upload ID {id} has been successfully deleted",
    )


@router.patch("/{id}", response_model=BatchUploadDetailOutput)
async def update_batch_upload(
    id: int,
    batch_upload: BatchUploadUpdateInput,
    session: Session = Depends(get_session),
):
    """
    Batch upload endpoint to process barcodes for different operations.

    **Args:**
    - id: The batch upload data containing the base64 encoded Excel file.

    **Returns:**
    - BatchUploadOutput: The result of the batch processing including any errors.
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

    **Args:**
    - batch_upload_input: The batch upload data containing the base64 encoded Excel file.
    - process_type: The type of processing to be performed ("request", "shelving", "withdraw").

    **Returns:**
    - BatchUploadOutput: The result of the batch processing including any errors.
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
            session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
                {"status": "Failed", "update_dt": update_dt},
                synchronize_session=False,
            )
            raise BadRequest(detail="Excel file must contain a 'Item Barcode' column.")

        df["Item Barcode"] = df["Item Barcode"].astype(str)

        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Processing", "update_dt": update_dt},
            synchronize_session=False,
        )

        validated_df, errored_df, errors = validate_request_data(session, df)
        # Process the request data
        if validated_df.empty or errors.get("errors"):

            session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
                {"status": "Failed", "update_dt": update_dt},
                synchronize_session=False,
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

        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Completed", "update_dt": datetime.now(timezone.utc)},
            synchronize_session=False,
        )
        session.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK, content="Batch upload successful"
        )

    except Exception as e:
        raise InternalServerError(detail=str(f"Request BatchUpload Error: {e}"))


@router.post("/withdraw-jobs/{job_id}")
async def batch_upload_withdraw_job(
    job_id: int, file: UploadFile, session: Session = Depends(get_session)
):
    """
    Batch upload endpoint to process barcodes for different operations.

    **Args:**
    - batch_upload_input: The batch upload data containing the base64 encoded Excel file.
    - process_type: The type of processing to be performed ("request", "shelving", "withdraw").

    **Returns:**
    - BatchUploadOutput: The result of the batch processing including any errors.
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
            session.query(BatchUpload).filter(
                BatchUpload.id == new_batch_upload.id
            ).update(
                {"status": "Failed", "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
            session.commit()
            raise NotFound(detail=f"Withdraw job id {job_id} not found")

        if "Item Barcode" not in df.columns and "Tray Barcode" not in df.columns:
            session.query(BatchUpload).filter(
                BatchUpload.id == new_batch_upload.id
            ).update(
                {"status": "Failed", "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
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
            session.query(BatchUpload).filter(
                BatchUpload.id == new_batch_upload.id
            ).update(
                {"status": "Failed", "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
            raise NotFound(
                detail="All barcodes are invalid to process bulk withdraw upload. Please check your barcodes and try again."
            )

        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Processing", "update_dt": datetime.now(timezone.utc)},
            synchronize_session=False,
        )
        session.commit()

        lookup_barcode_values = list(set(lookup_barcode_values))
        barcodes = (
            session.query(Barcode)
            .filter(Barcode.value.in_(lookup_barcode_values))
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
            session.query(BatchUpload).filter(
                BatchUpload.id == new_batch_upload.id
            ).update(
                {"status": "Failed", "update_dt": datetime.now(timezone.utc)},
                synchronize_session=False,
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
                session.query(BatchUpload).filter(
                    BatchUpload.id == new_batch_upload.id
                ).update(
                    {"status": "Failed", "update_dt": datetime.now(timezone.utc)},
                    synchronize_session=False,
                )
                session.commit()
                raise NotFound(
                    detail="All barcodes are invalid to process bulk withdraw upload. Please check your barcodes and try again."
                )
            else:
                session.query(BatchUpload).filter(
                    BatchUpload.id == new_batch_upload.id
                ).update(
                    {"status": "Failed", "update_dt": datetime.now(timezone.utc)},
                    synchronize_session=False,
                )
                session.commit()
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST, content=errored_barcodes
                )

        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Completed", "update_dt": datetime.now(timezone.utc)},
            synchronize_session=False,
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
    except Exception as e:
        inventory_logger.error(f"Batch Upload Internal Server Error: {e}")
        raise InternalServerError(detail=f"Internal Server Error: {e}")


@router.post("/location-management")
async def batch_upload_location_management(
    file: UploadFile,
    building_id: int = Form(),
    module_id: int = Form(),
    aisle_id: int = Form(),
    side_id: int = Form(),
    session: Session = Depends(get_session),
):
    """
    Batch upload endpoint to process barcodes for different operations.

    **Args:**
    - batch_upload_input: The batch upload data containing the base64 encoded Excel file.
    - process_type: The type of processing to be performed ("request", "shelving", "withdraw").

    **Returns:**
    - BatchUploadOutput: The result of the batch processing including any errors.
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

    shelves_bulk = []
    errors = []

    for index, row in df.iterrows():
        try:
            if not row["ladder_number"]:
                errors.append(
                    {"line": int(index) + 1, "error": "Ladder Number is required"}
                )
                continue

            ladder_number = (
                session.query(LadderNumber)
                .filter(LadderNumber.number == row["ladder_number"])
                .first()
            )

            if not ladder_number:
                ladder_number = LadderNumber(number=row["ladder_number"])
                ladder_number = commit_record(session, ladder_number)

            ladder = (
                session.query(Ladder)
                .filter(
                    Ladder.ladder_number_id == ladder_number.id,
                    Ladder.side_id == side_id,
                )
                .first()
            )

            if not ladder:
                ladder = Ladder(
                    ladder_number_id=ladder_number.id,
                    sort_priority=row["ladder_sort_priority"],
                    side_id=side_id,
                )
                ladder = commit_record(session, ladder)

            if pd.notna(row["shelf_number"]):
                owner = session.query(Owner).filter(Owner.name == row["owner"]).first()
                if not owner:
                    errors.append(
                        {
                            "line": int(index) + 1,
                            "error": f"Owner {row['owner']} not found",
                        }
                    )
                    continue
                container_type = (
                    session.query(ContainerType)
                    .filter(ContainerType.type == row["container_type"])
                    .first()
                )
                if not container_type:
                    errors.append(
                        {
                            "line": int(index) + 1,
                            "error": f"Container Type {row['container_type']} "
                            "not found",
                        }
                    )
                    continue
                size_class = (
                    session.query(SizeClass)
                    .filter(SizeClass.name == row["size_class"])
                    .first()
                )
                if not size_class:
                    errors.append(
                        {
                            "line": int(index) + 1,
                            "error": f"Size Class {row['size_class']} not found",
                        }
                    )
                    continue
                shelf_type = (
                    session.query(ShelfType)
                    .join(SizeClass)
                    .filter(SizeClass.name == row["size_class"])
                    .filter(ShelfType.type == row["shelf_type"])
                    .first()
                )
                if not shelf_type:
                    errors.append(
                        {
                            "line": int(index) + 1,
                            "error": f"Shelf Type {row['shelf_type']} with Size Class "
                            f"{row['size_class']} not found",
                        }
                    )
                    continue

                shelf_number = (
                    session.query(ShelfNumber)
                    .filter(ShelfNumber.number == row["shelf_number"])
                    .first()
                )

                if shelf_number:
                    # Check if the shelf already exists
                    existing_shelf = (
                        session.query(Shelf)
                        .filter(
                            Shelf.shelf_number_id == shelf_number.id,
                            Shelf.ladder_id == ladder.id,
                        )
                        .first()
                    )
                    if existing_shelf:
                        errors.append(
                            {
                                "line": int(index) + 1,
                                "error": f"Shelf number {row['shelf_number']} at "
                                "ladder number "
                                f"{row['ladder_number']} already exists",
                            }
                        )
                        continue
                else:
                    shelf_number = ShelfNumber(number=row["shelf_number"])
                    shelf_number = commit_record(session, shelf_number)

                shelf_barcode = None
                if pd.notna(row["shelf_barcode"]):
                    shelf_barcode_value = row["shelf_barcode"]

                    shelf_barcode = (
                        session.query(Barcode)
                        .join(BarcodeType, Barcode.type_id == BarcodeType.id)
                        .filter(Barcode.value == shelf_barcode_value)
                        .filter(BarcodeType.name == "Shelf")
                        .first()
                    )

                    if shelf_barcode:
                        errors.append(
                            {
                                "line": int(index) + 1,
                                "error": f"Shelf Barcode value {row['shelf_barcode']} "
                                "already exists",
                            }
                        )
                        continue
                    else:
                        barcode_type = (
                            session.query(BarcodeType)
                            .filter(BarcodeType.name == "Shelf")
                            .first()
                        )

                        if not re.fullmatch(
                            barcode_type.allowed_pattern, shelf_barcode_value
                        ):
                            errors.append(
                                {
                                    "line": int(index) + 1,
                                    "error": "Shelf Barcode value: "
                                    f"{shelf_barcode_value} is invalid for "
                                    "barcode rules",
                                }
                            )
                            continue

                        shelf_barcode = Barcode(
                            value=shelf_barcode_value, type_id=barcode_type.id
                        )
                        shelf_barcode = commit_record(session, shelf_barcode)

                new_shelf = Shelf(
                    height=row["height"],
                    width=row["width"],
                    depth=row["depth"],
                    sort_priority=row["shelf_sort_priority"],
                    container_type_id=container_type.id,
                    shelf_number_id=shelf_number.id,
                    shelf_type_id=shelf_type.id,
                    owner_id=owner.id,
                    ladder_id=ladder.id,
                )

                if shelf_barcode:
                    new_shelf.barcode_id = shelf_barcode.id

                shelves_bulk.append(new_shelf)

        except (ValidationError, ValueError) as e:
            errors.append({"line": int(index) + 1, "error": str(e)})

    if errors:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=errors)

    if len(shelves_bulk) > 0:
        session.add_all(shelves_bulk)
        session.commit()

        for shelf in shelves_bulk:
            shelf_type = shelf.shelf_type
            max_capacity = shelf_type.max_capacity

            # Create Shelf Positions
            shelf_position_bulk = []
            for index in range(1, max_capacity + 1):
                shelf_position_number = (
                    session.query(ShelfPositionNumber)
                    .filter(ShelfPositionNumber.number == index)
                    .first()
                )

                if not shelf_position_number:
                    shelf_position_number = ShelfPositionNumber(
                        shelf_type_id=shelf_type.id, position_number=index
                    )
                    session.add(shelf_position_number)
                    session.commit()
                    session.refresh(shelf_position_number)

                shelf_position_bulk.append(
                    ShelfPosition(
                        shelf_id=shelf.id,
                        shelf_position_number_id=shelf_position_number.id,
                    )
                )

            session.add_all(shelf_position_bulk)
            session.add(shelf)

            session.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK, content="Batch Upload Successful"
    )
