import base64
from fastapi import APIRouter, HTTPException, Depends, UploadFile
from sqlmodel import Session
from io import BytesIO, StringIO
import pandas as pd
from starlette import status
from starlette.responses import JSONResponse

from app.database.session import get_session, commit_record
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.withdraw_jobs import WithdrawJob
from app.schemas.batch_upload import BatchUploadInput
from app.schemas.withdraw_jobs import WithdrawJobWriteOutput, WithdrawJobDetailOutput
from app.utilities import (
    validate_request_data,
    process_request_data,
    process_withdraw_job_data,
)
from app.config.exceptions import (
    BadRequest,
)

router = APIRouter(
    prefix="/batch-upload",
    tags=["batch upload"],
)


@router.post("/request")
async def batch_upload_request(
    file: UploadFile, session: Session = Depends(get_session)
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
    content_type = file.content_type
    contents = await file.read()

    if file_name.endswith(".xlsx"):
        df = pd.read_excel(contents)
    if file_name.endswith(".csv"):
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

    # Check if the necessary column exists
    if "Item Barcode" not in df.columns:
        raise BadRequest(detail="Excel file must contain a 'Item Barcode' column.")

    df["Item Barcode"] = df["Item Barcode"].astype(str)

    validated_df, errored_df, errors = validate_request_data(session, df)
    # Process the request data
    if validated_df.empty:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=errors)
    else:
        request_df, request_instances = process_request_data(session, validated_df)

    session.bulk_save_objects(request_instances)
    session.commit()

    if errors:
        return JSONResponse(status_code=status.HTTP_200_OK, content=errors)

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
    content_type = file.content_type
    contents = await file.read()

    if file_name.endswith(".xlsx"):
        df = pd.read_excel(contents)
    if file_name.endswith(".csv"):
        df = pd.read_csv(
            StringIO(contents.decode("utf-8")),
            dtype={"Item Barcode": str, "Tray Barcode": str},
        )

    # Remove rows with NaN values in 'Item Barcode' or 'Tray Barcode'
    df = df.dropna(subset=["Item Barcode", "Tray Barcode"], how="all")

    # Check if the necessary column exists
    withdraw_job = session.get(WithdrawJob, job_id)

    if not withdraw_job:
        raise BadRequest(detail=f"Withdraw job id {job_id} not found")

    if "Item Barcode" not in df.columns and "Tray Barcode" not in df.columns:
        raise BadRequest(
            detail="Excel file must contain a 'Item Barcode' or 'Tray "
            "Barcode' columns."
        )

    lookup_barcode_values = []
    if not df["Item Barcode"].empty:
        lookup_barcode_values.extend(df["Item Barcode"].astype(str).tolist())

    if not df["Tray Barcode"].empty:
        lookup_barcode_values.extend(df["Tray Barcode"].astype(str).tolist())

    if not lookup_barcode_values:
        raise BadRequest(detail="At least one barcode value must be provided")

    barcodes = (
        session.query(Barcode).filter(Barcode.value.in_(lookup_barcode_values)).all()
    )

    if not barcodes:
        raise BadRequest(detail="At least one valid barcode value must be provided")

    (
        withdraw_items,
        withdraw_non_tray_items,
        withdraw_trays,
        errored_barcodes,
    ) = process_withdraw_job_data(session, withdraw_job.id, barcodes, df)

    if not withdraw_items and not withdraw_non_tray_items and not withdraw_trays:
        if not errored_barcodes.get("errors"):
            raise BadRequest(
                detail=f"At least one valida barcode value must be provided"
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST, content=errored_barcodes
            )

    session.bulk_save_objects(withdraw_items)
    session.bulk_save_objects(withdraw_non_tray_items)
    session.bulk_save_objects(withdraw_trays)
    session.commit()
    session.refresh(withdraw_job)

    if errored_barcodes.get("errors"):
        return JSONResponse(status_code=status.HTTP_200_OK, content=errored_barcodes)

    return JSONResponse(
        status_code=status.HTTP_200_OK, content="Batch Upload Successful"
    )
