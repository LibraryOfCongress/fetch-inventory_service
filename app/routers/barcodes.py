import uuid, re

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy.exc import IntegrityError

from app.database.session import get_session
from app.filter_params import SortParams
from app.logger import inventory_logger
from app.models.barcodes import Barcode
from app.models.barcode_types import BarcodeType
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.schemas.barcodes import (
    BarcodeInput,
    BarcodeUpdateInput,
    BarcodeListOutput,
    BarcodeDetailWriteOutput,
    BarcodeDetailReadOutput,
    BarcodeMutationInput,
)
from app.config.exceptions import NotFound, ValidationException
from app.sorting import BaseSorter

router = APIRouter(
    prefix="/barcodes",
    tags=["barcodes"],
)


@router.get("/", response_model=Page[BarcodeListOutput])
def get_barcode_list(
    session: Session = Depends(get_session),
    sort_params: SortParams = Depends()
) -> list:
    """
    Retrieve a list of barcodes from the database.

    **Parameters:**
    - sort_params (SortParams): The sorting parameters.

    **Returns:**
    - list: A list of barcodes.
    """
    # Create a query to retrieve all barcodes
    query = select(Barcode).distinct()

    # Validate and Apply sorting based on sort_params
    if sort_params.sort_by:
        # Apply sorting using BaseSorter
        sorter = BaseSorter(Barcode)
        query = sorter.apply_sorting(query, sort_params)

    return paginate(session, query)


@router.get("/{id}", response_model=BarcodeDetailReadOutput)
def get_barcode_detail(id: uuid.UUID, session: Session = Depends(get_session)):
    """
    Retrieve barcode details by ID.

    **Parameters:**
    - id (int): The ID of the barcode to retrieve.

    **Returns:**
    - Barcode Detail Read Output: The barcode details.

    **Raises:**
    - HTTPException: If the barcode is not found.
    """
    # Retrieve the barcode from the database by ID
    barcode = session.get(Barcode, id)

    if barcode:
        return barcode

    raise NotFound(detail=f"Barcode ID {id} Not Found")


@router.get("/value/{value}", response_model=BarcodeDetailReadOutput)
def get_barcode_by_value(value: str, session: Session = Depends(get_session)):
    """
    Retrieve barcode details by its value

    **Parameters:**
    - value (str): The value of the barcode to retrieve.

    **Returns:**
    - Barcode Detail Read Output: The barcode details.

    **Raises:**
    - HTTPException: If the barcode is not found.
    """
    barcode = session.query(Barcode).filter(Barcode.value == value).first()
    if not barcode:
        raise NotFound(detail=f"Barcode with value {value} not found")
    return barcode


@router.post("/", response_model=BarcodeDetailWriteOutput, status_code=201)
def create_barcode(
    barcode_input: BarcodeInput, session: Session = Depends(get_session)
) -> Barcode:
    """
    Create a new barcode.

    **Args:**
    - Barcode Input: The input data for creating a barcode.

    **Returns:**
    - Barcode: The newly created barcode.
    """
    try:
        barcode_type_string = barcode_input.type
        barcode_type = session.exec(
            select(BarcodeType).where(BarcodeType.name == barcode_type_string)
        ).first()

        if not barcode_type:
            raise NotFound(detail=f"Barcode type '{barcode_type_string}' not found.")
        else:
            mutated_barcode_input = barcode_input.model_dump()
            mutated_barcode_input["type_id"] = barcode_type.id
            # Use muttion input to avoid missing type_id validation
            mutated_barcode_input = BarcodeMutationInput(**mutated_barcode_input)

        # validate value against barcode_type allowed_pattern
        if not re.fullmatch(barcode_type.allowed_pattern, barcode_input.value):
            raise ValidationException(
                detail=f"Barcode value is invalid for {barcode_type.name} barcode rules."
            )

        # validate tray barcode value first two characters which is the tray short
        # name against available tray short names
        if barcode_type.name == "Tray":
            short_name = barcode_input.value[:2]
            container_size = (
                session.query(SizeClass)
                .filter(SizeClass.short_name == short_name)
                .first()
            )

            if not container_size:
                raise ValidationException(
                    detail=f"The tray can not be added, the container size "
                    f"{short_name} doesnt exist in the system. Please add it and try again."
                )

        existing_barcode = session.exec(
            select(Barcode).where(Barcode.value == barcode_input.value)
        ).first()

        if existing_barcode:
            if not existing_barcode.withdrawn:
                raise ValidationException(
                    detail=f"Barcode with value {barcode_input.value} already exists."
                )
            else:
                return existing_barcode

        new_barcode = Barcode(**mutated_barcode_input.model_dump(exclude={"type"}))
        session.add(new_barcode)
        session.commit()
        session.refresh(new_barcode)

        return new_barcode

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/{id}", response_model=BarcodeDetailWriteOutput)
def update_barcode(
    id: uuid.UUID, barcode: BarcodeUpdateInput, session: Session = Depends(get_session)
):
    """
    Update barcode details.

    **Parameters:**
    - id (int): The ID of the barcode to retrieve.
    - Barcode Update Input: The updated barcode details.

    **Returns:**
    - Barcode Update Input: The barcode details.

    **Raises:**
    - HTTPException: If the barcode is not found.
    """
    # First check if new barcode type and if exists
    new_barcode_type = None
    mutated_barcode_type_id = None
    if barcode.type:
        new_barcode_type = session.exec(
            select(BarcodeType).where(BarcodeType.name == barcode.type)
        ).first()
        if not new_barcode_type:
            raise NotFound(detail=f"Barcode type {barcode.type} not found.")
        else:
            # barcode['type_id'] = new_barcode_type.id
            mutated_barcode_type_id = new_barcode_type.id

    existing_barcode = session.get(Barcode, id)

    if not existing_barcode:
        raise NotFound(detail=f"Barcode ID {id} Not Found")

    if new_barcode_type:
        # use new allowed pattern to validate
        if barcode.value:
            # Validate against incoming value
            if not re.fullmatch(new_barcode_type.allowed_pattern, barcode.value):
                raise ValidationException(
                    detail=f"Barcode value is invalid for {new_barcode_type.name} barcode rules."
                )
        else:
            # Validate existing value
            if not re.fullmatch(
                new_barcode_type.allowed_pattern, existing_barcode.value
            ):
                raise ValidationException(
                    detail=f"Barcode type {new_barcode_type.name} would make existing barcode value invalid."
                )
    else:
        # use existing allowed pattern to validate
        existing_barcode_type = session.exec(
            select(BarcodeType).where(BarcodeType.id == existing_barcode.type_id)
        ).first()
        if barcode.value:
            # Validate incoming against existing allowed_pattern
            if not re.fullmatch(existing_barcode_type.allowed_pattern, barcode.value):
                raise ValidationException(
                    detail=f"New Barcode value is invalid for {existing_barcode_type.name} barcode rules."
                )
        # Else neither type or barcode value changed, nothing to validate

    # validate tray barcode value first two characters which is the tray short
    # name against available tray short names
    if barcode.value:
        existing_barcode_type = session.exec(
            select(BarcodeType).where(BarcodeType.id == existing_barcode.type_id)
        ).first()
        inventory_logger.info(f"Existing Barcode Type: {existing_barcode_type}")
        if (
            barcode.type
            and barcode.type == "Tray"
            or existing_barcode_type.name == "Tray"
        ):
            short_name = barcode.value[:2]
            container_size = (
                session.query(SizeClass)
                .filter(SizeClass.short_name == short_name)
                .first()
            )

            if not container_size:
                raise ValidationException(
                    detail=f"The tray can not be added, the container size "
                    f"{short_name} doesnt exist in the system. Please add it and try again."
                )

        if (existing_barcode_type.name == "Item" and existing_barcode.value !=
            barcode.value):
            item = session.query(Item).filter(Item.barcode_id ==
                                              existing_barcode.id).first()
            non_tray_item = session.query(NonTrayItem).filter(
                NonTrayItem.barcode_id == existing_barcode.id
            ).first()
            if item:
                verification_job = session.query(VerificationJob).filter(
                    VerificationJob.id == item.verification_job_id
                ).first()
                if verification_job:
                    tray_barcode = session.query(Barcode).join(Tray, Barcode.id == Tray.barcode_id).filter(Tray.id == item.tray_id).first()
                    new_verification_change = VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        tray_barcode_value=tray_barcode.value,
                        item_barcode_value=existing_barcode.value,
                        change_type="BarcodeValueEdit",
                        completed_by_id=verification_job.user_id
                    )
                    session.add(new_verification_change)
            else:
                verification_job = session.query(VerificationJob).filter(
                    VerificationJob.id == non_tray_item.verification_job_id
                ).first()
                if verification_job:
                    new_verification_change = VerificationChange(
                        workflow_id=verification_job.workflow_id,
                        item_barcode_value=existing_barcode.value,
                        change_type="BarcodeValueEdit",
                        completed_by_id=verification_job.user_id
                    )
                    session.add(new_verification_change)

    mutated_data = barcode.model_dump(exclude={"type"}, exclude_unset=True)

    if mutated_barcode_type_id:
        mutated_data["type_id"] = mutated_barcode_type_id

    for key, value in mutated_data.items():
        setattr(existing_barcode, key, value)

    setattr(existing_barcode, "update_dt", datetime.now(timezone.utc))

    session.add(existing_barcode)
    session.commit()
    session.refresh(existing_barcode)

    return existing_barcode


@router.delete("/{id}")
def delete_barcode(id: uuid.UUID, session: Session = Depends(get_session)):
    """
    Deletes a barcode by its ID.

    **Parameters:**
    - id (int): The ID of the barcode to delete.

    **Returns:**
    - None

    **Raises:**
    - HTTPException: If the barcode with the given ID is not found.
    """
    # Get the barcode with the given ID from the session
    barcode = session.get(Barcode, id)

    if barcode:
        session.delete(barcode)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Barcode ID {id} Deleted Successfully"
        )

    raise NotFound(detail=f"Barcode ID {id} Not Found")
