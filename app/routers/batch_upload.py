import base64
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, Form
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi_pagination import Page
from sqlalchemy import and_
from sqlmodel import Session, select
from io import BytesIO, StringIO
import pandas as pd
from starlette import status
from starlette.responses import JSONResponse

from app.database.session import get_session
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.batch_upload import BatchUpload
from app.models.requests import Request
from app.models.withdraw_jobs import WithdrawJob
from app.schemas.batch_upload import (
    BatchUploadListOutput,
    BatchUploadDetailOutput,
    BatchUploadUpdateInput,
    BatchUploadInput,
)
from app.utilities import (
    validate_request_data,
    process_request_data,
    process_withdraw_job_data,
)
from app.config.exceptions import (
    BadRequest,
    NotFound,
)

router = APIRouter(
    prefix="/batch-upload",
    tags=["batch upload"],
)


@router.get("/", response_model=Page[BatchUploadListOutput])
async def get_batch_upload(
    batch_upload_type: str | None = None, session: Session = (Depends(get_session))
) -> list:
    """
    Batch upload endpoint to process barcodes for different operations.

    **Returns:**
    - Batch Upload Output: The paginated list of batch uploads.
    """
    query = select(BatchUpload)

    if batch_upload_type:
        if batch_upload_type == "request":
            query = query.filter(BatchUpload.withdraw_job_id.is_(None))
        elif batch_upload_type == "withdraw":
            query = query.filter(BatchUpload.withdraw_job_id.isnot(None))

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
    if batch_upload.withdraw_job_id:
        session.query(WithdrawJob).filter(
            WithdrawJob.id == batch_upload.withdraw_job_id
        ).delete()
    else:
        session.query(Request).filter(Request.batch_upload_id == id).delete()

    session.delete(batch_upload)
    session.commit()
    session.refresh(batch_upload)

    return batch_upload


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

    setattr(existing_batch_upload, "update_dt", datetime.utcnow())

    session.add(existing_batch_upload)
    session.commit()
    session.refresh(existing_batch_upload)

    return existing_batch_upload


@router.post("/request")
async def batch_upload_request(
    file: UploadFile, user_id: int = Form(None), session: Session = Depends(get_session)
):
    """
    Batch upload endpoint to process barcodes for different operations.

    **Args:**
    - batch_upload_input: The batch upload data containing the base64 encoded Excel file.
    - process_type: The type of processing to be performed ("request", "shelving", "withdraw").

    **Returns:**
    - BatchUploadOutput: The result of the batch processing including any errors.
    """
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
        user_id=user_id,
    )

    session.add(new_batch_upload)
    session.commit()
    session.refresh(new_batch_upload)

    # Check if the necessary column exists
    if "Item Barcode" not in df.columns:
        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Failed", "update_dt": datetime.utcnow()},
            synchronize_session=False,
        )
        raise BadRequest(detail="Excel file must contain a 'Item Barcode' column.")

    df["Item Barcode"] = df["Item Barcode"].astype(str)

    session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
        {"status": "Processing", "update_dt": datetime.utcnow()},
        synchronize_session=False,
    )

    validated_df, errored_df, errors = validate_request_data(session, df)
    # Process the request data
    if validated_df.empty:
        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Failed", "update_dt": datetime.utcnow()},
            synchronize_session=False,
        )
        session.commit()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=errors)
    else:
        request_df, request_instances = process_request_data(
            session, validated_df, new_batch_upload.id
        )

    session.bulk_save_objects(request_instances)

    if errors.get("errors"):
        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Completed", "update_dt": datetime.utcnow()},
            synchronize_session=False,
        )
        session.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, content=errors)

    session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
        {"status": "Completed", "update_dt": datetime.utcnow()},
        synchronize_session=False,
    )
    session.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK, content="Batch upload successful"
    )


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
        withdraw_job_id=withdraw_job.id,
    )

    session.add(new_batch_upload)
    session.commit()
    session.refresh(new_batch_upload)

    # Remove rows with NaN values in 'Item Barcode' and 'Tray Barcode'
    df = df.dropna(subset=["Item Barcode", "Tray Barcode"], how="all")

    if not withdraw_job:
        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Failed", "update_dt": datetime.utcnow()},
            synchronize_session=False,
        )
        session.commit()
        raise NotFound(detail=f"Withdraw job id {job_id} not found")

    if "Item Barcode" not in df.columns and "Tray Barcode" not in df.columns:
        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Failed", "update_dt": datetime.utcnow()},
            synchronize_session=False,
        )
        session.commit()
        raise BadRequest(
            detail="Batch file must contain a 'Item Barcode' or 'Tray "
            "Barcode' columns."
        )

    # Drop NaN and empty string values
    item_df = df["Item Barcode"].replace("", pd.NA).dropna()
    tray_df = df["Tray Barcode"].replace("", pd.NA).dropna()

    # Concatenate the cleaned columns into a single Series
    merged_series = pd.concat([item_df, tray_df])

    # Create a new DataFrame from the concatenated Series
    merged_df = pd.DataFrame(merged_series, columns=["Barcode"])

    # Reset the index if necessary
    merged_df.reset_index(drop=True, inplace=True)

    lookup_barcode_values = []
    if not merged_df["Barcode"].empty:
        lookup_barcode_values.extend(merged_df["Barcode"].astype(str).tolist())

    if not lookup_barcode_values:
        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Failed", "update_dt": datetime.utcnow()},
            synchronize_session=False,
        )
        raise NotFound(
            detail="All barcodes are invalid to process bulk withdraw upload. Please check your barcodes and try again."
        )

    session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
        {"status": "Processing", "update_dt": datetime.utcnow()},
        synchronize_session=False,
    )
    session.commit()

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )

    found_barcodes = set(barcode.value for barcode in barcodes)
    missing_barcodes = set(lookup_barcode_values) - found_barcodes

    errored_barcodes = {"errors": []}

    for barcode in missing_barcodes:
        index = merged_df.index[merged_df["Barcode"] == barcode].tolist()
        if index:
            errored_barcodes["errors"].append(
                {"line": index[0] + 1, "error": f"Barcode value {barcode} not found"}
            )

    if not barcodes:
        session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
            {"status": "Failed", "update_dt": datetime.utcnow()},
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
                {"status": "Failed", "update_dt": datetime.utcnow()},
                synchronize_session=False,
            )
            session.commit()
            raise NotFound(
                detail=f"All barcodes are invalid to process bulk withdraw upload. Please check your barcodes and try again."
            )
        else:
            session.query(BatchUpload).filter(
                BatchUpload.id == new_batch_upload.id
            ).update(
                {"status": "Failed", "update_dt": datetime.utcnow()},
                synchronize_session=False,
            )
            session.commit()
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST, content=errored_barcodes
            )

    session.query(BatchUpload).filter(BatchUpload.id == new_batch_upload.id).update(
        {"status": "Completed", "update_dt": datetime.utcnow()},
        synchronize_session=False,
    )

    if withdraw_items:
        session.bulk_save_objects(withdraw_items)
    if withdraw_non_tray_items:
        session.bulk_save_objects(withdraw_non_tray_items)
    if withdraw_trays:
        session.bulk_save_objects(withdraw_trays)

    session.commit()
    session.refresh(withdraw_job)

    if errored_barcodes.get("errors"):
        return JSONResponse(status_code=status.HTTP_200_OK, content=errored_barcodes)

    return JSONResponse(
        status_code=status.HTTP_200_OK, content="Batch Upload Successful"
    )
