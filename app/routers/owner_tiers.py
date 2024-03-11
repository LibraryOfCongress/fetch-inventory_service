from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate

from app.database.session import get_session
from app.models.owner_tiers import OwnerTier
from app.schemas.owner_tiers import (
    OwnerTierInput,
    OwnerTierListOutput,
    OwnerTierDetailOutput,
)
from app.config.exceptions import (
    NotFound,
    ValidationException,
    InternalServerError,
)

router = APIRouter(
    prefix="/owners",
    tags=["owners"],
)


@router.get("/tiers", response_model=Page[OwnerTierListOutput])
def get_owner_tier_list(session: Session = Depends(get_session)) -> list:
    """
    Get the list of owner tiers.

    Returns:
    - Owner Tier List Output: The paginated list of owner tiers.
    """
    return paginate(session, select(OwnerTier))


@router.get("/tiers/{id}", response_model=OwnerTierDetailOutput)
def get_owner_tier_detail(id: int, session: Session = Depends(get_session)):
    """
    Retrieves the details of an owner tier by its ID.

    **Parameters:**
    - id: The ID of the owner tier to retrieve.

    **Returns:**
    - Owner Tier Detail Output: The details of the owner tier.

    **Raises:**
    - HTTPException: If the owner tier with the specified ID is not found.
    """
    owner_tier = session.get(OwnerTier, id)
    if owner_tier:
        return owner_tier

    raise NotFound(detail=f"Owner Tier ID {id} Not Found")


@router.post("/tiers", response_model=OwnerTierDetailOutput, status_code=201)
def create_owner_tier(
    owner_tier_input: OwnerTierInput, session: Session = Depends(get_session)
) -> OwnerTier:
    """
    Create an owner tier:

    **Args:**
    - Owner Tier Input: The input data for creating the owner tier.

    **Returns:**
    - Owner Tier Detail Output: The created owner tier.

    **Raises:**
    - HTTPException: If there is an integrity error during the creation of the owner
    tier.

    **Notes:**
    - **level**: Required unique integer that represents a tier
    - **name**: Required unique string that names a tier (category)
    """
    try:
        new_owner_tier = OwnerTier(**owner_tier_input.model_dump())
        session.add(new_owner_tier)
        session.commit()
        session.refresh(new_owner_tier)

        return new_owner_tier

    except IntegrityError as e:
        raise ValidationException(detail=f"{e}")


@router.patch("/tiers/{id}", response_model=OwnerTierDetailOutput)
def update_owner_tier(
    id: int, owner_tier: OwnerTierInput, session: Session = Depends(get_session)
):
    """
    Update an owner tier by its ID.

    **Args:**
    - id: The ID of the owner tier to update.
    - Owner Tier Input: The updated owner tier data.

    **Returns:**
    - OwnerTierDetailOutput: The updated owner tier.
    """
    try:
        existing_owner_tier = session.get(OwnerTier, id)

        if existing_owner_tier is None:
            raise NotFound(detail=f"Owner Tier ID {id} Not Found")

        mutated_data = owner_tier.model_dump(exclude_unset=True)

        for key, value in mutated_data.items():
            setattr(existing_owner_tier, key, value)

        setattr(existing_owner_tier, "update_dt", datetime.utcnow())
        session.add(existing_owner_tier)
        session.commit()
        session.refresh(existing_owner_tier)

        return existing_owner_tier

    except Exception as e:
        raise InternalServerError(detail=f"{e}")


@router.delete("/tiers/{id}")
def delete_owner_tier(id: int, session: Session = Depends(get_session)):
    """
    Delete an owner tier by its ID.

    **Parameters:**
    - id: The ID of the owner tier to delete.

    **Returns:**
    - None

    **Raises:**
        HTTPException: If the owner tier with the specified ID is not found.
    """
    owner_tier = session.get(OwnerTier, id)

    if owner_tier:
        session.delete(owner_tier)
        session.commit()

        return HTTPException(
            status_code=204, detail=f"Owner Tier ID {id} Deleted "
                                    f"Successfully"
        )

    raise NotFound(detail=f"Owner Tier ID {id} Not Found")
