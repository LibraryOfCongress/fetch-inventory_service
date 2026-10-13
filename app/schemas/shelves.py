import uuid

from typing import Optional, List
from pydantic import BaseModel, conint, condecimal, ConfigDict
from datetime import datetime, timezone

from app.schemas.owners import OwnerDetailReadOutput
from app.schemas.ladders import LadderDetailWriteOutput
from app.schemas.container_types import ContainerTypeDetailReadOutput
from app.schemas.barcodes import BarcodeDetailReadOutput


class ShelfInput(BaseModel):
    sort_priority: Optional[conint(ge=0, le=32767)] = None
    ladder_id: conint(ge=0, le=2147483647)
    container_type_id: Optional[conint(ge=0, le=2147483647)] = None
    shelf_type_id: conint(ge=0, le=2147483647)
    shelf_number: conint(ge=1, le=32767)
    owner_id: conint(ge=0, le=32767)
    height: condecimal(decimal_places=2)
    width: condecimal(decimal_places=2)
    depth: condecimal(decimal_places=2)
    barcode_id: uuid.UUID | None = None
    barcode_value: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sort_priority": 1,
                "ladder_id": 1,
                "container_type_id": 1,
                "shelf_number": 1,
                "shelf_type_id": 1,
                "owner_id": 1,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001",
            }
        }
    )


class ShelfUpdateInput(BaseModel):
    sort_priority: Optional[conint(ge=0, le=32767)] = None
    ladder_id: Optional[conint(ge=0, le=2147483647)] = None
    container_type_id: Optional[conint(ge=0, le=2147483647)] = None
    shelf_type_id: Optional[conint(ge=0, le=2147483647)] = None
    shelf_number: Optional[conint(ge=1, le=32767)] = None
    owner_id: Optional[conint(ge=0, le=32767)] = None
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    barcode_id: Optional[uuid.UUID] = None
    barcode_value: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sort_priority": 1,
                "ladder_id": 1,
                "container_type_id": 1,
                "shelf_type_id": 1,
                "shelf_number": 1,
                "owner_id": 1,
                "height": 15.7,
                "width": 30.33,
                "depth": 27,
                "barcode_id": "550e8400-e29b-41d4-a716-446655440001"
            }
        }
    )


class ShelfBulkUpdateInput(BaseModel):
    id: conint(ge=0, le=2147483647)
    owner_id: Optional[conint(ge=0, le=32767)] = None
    shelf_type_id: Optional[conint(ge=0, le=2147483647)] = None
    container_type_id: Optional[conint(ge=0, le=2147483647)] = None
    sort_priority: Optional[conint(ge=0, le=32767)] = None


class NestedSizeClassDetailOutput(BaseModel):
    id: int
    name: str
    short_name: str
    height: Optional[condecimal(decimal_places=2)] = None
    width: Optional[condecimal(decimal_places=2)] = None
    depth: Optional[condecimal(decimal_places=2)] = None
    create_dt: datetime
    update_dt: datetime


class NestedShelfTypeDetailOutput(BaseModel):
    id: int
    type: str
    size_class_id: int
    size_class: Optional[NestedSizeClassDetailOutput]
    max_capacity: int
    create_dt: datetime
    update_dt: datetime


class NestedContainerTypeDetailForShelfOutput(BaseModel):
    id: int
    type: str


class ShelfBaseOutput(BaseModel):
    id: int
    location: Optional[str] = None
    internal_location: Optional[str] = None


class ShelfListOutput(ShelfBaseOutput):
    sort_priority: Optional[int] = None
    available_space: int
    ladder_id: int
    shelf_number: int
    container_type_id: Optional[int] = None
    container_type: Optional[NestedContainerTypeDetailForShelfOutput] = None
    shelf_type_id: int
    shelf_type: NestedShelfTypeDetailOutput
    owner_id: Optional[int] = None
    owner: Optional[OwnerDetailReadOutput] = None
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    barcode: Optional[BarcodeDetailReadOutput] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 10234,
                "location": "Cabin Branch-1-52-L-23-3",
                "internal_location": "02-14-575-1144-23-10234",
                "sort_priority": 1,
                "shelf_number": 3,
                "ladder_id": 1,
                "container_type_id": 1,
                "shelf_type_id": 1,
                "owner_id": 1,
            }
        }
    )


class ShelfDetailWriteOutput(ShelfBaseOutput):
    sort_priority: Optional[int] = None
    barcode_id: Optional[uuid.UUID] = None
    ladder_id: int
    container_type_id: Optional[int] = None
    shelf_type_id: int
    shelf_number: int
    owner_id: Optional[int] = None
    available_space: int
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    shelf_type: NestedShelfTypeDetailOutput
    ladder: LadderDetailWriteOutput
    owner: Optional[OwnerDetailReadOutput] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    create_dt: datetime
    update_dt: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 10234,
                "location": "Cabin Branch-1-52-L-23-3",
                "internal_location": "02-14-575-1144-23-10234",
                "sort_priority": 1,
                "shelf_number": 3,
                "ladder_id": 23,
                "available_space": 33,
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
    )


class ShelfPositionNestedForShelf(BaseModel):
    id: int
    location: Optional[str] = None
    internal_location: Optional[str] = None
    position_number: int


class ShelfDetailReadOutput(ShelfBaseOutput):
    sort_priority: Optional[int] = None
    ladder: LadderDetailWriteOutput
    shelf_number: int
    shelf_type_id: int
    shelf_type: NestedShelfTypeDetailOutput
    container_type: Optional[ContainerTypeDetailReadOutput] = None
    owner: Optional[OwnerDetailReadOutput] = None
    available_space: int
    width: Optional[float] = None
    height: Optional[float] = None
    depth: Optional[float] = None
    barcode_id: Optional[uuid.UUID] = None
    barcode: Optional[BarcodeDetailReadOutput] = None
    create_dt: datetime
    update_dt: datetime
    shelf_positions: List[ShelfPositionNestedForShelf]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 10234,
                "location": "Cabin Branch-1-52-L-23-3",
                "internal_location": "02-14-575-1144-23-10234",
                "sort_priority": 1,
                "shelf_number": 3,
                "available_space": 33,
                "shelf_positions": [
                    {
                        "id": 278,
                        "location": "Cabin Branch-04-57-L-23-10-08",
                        "internal_location": "01-04-57-L-23-10-08",
                        "position_number": 1
                    }
                ],
                "create_dt": "2023-10-08T20:46:56.764426",
                "update_dt": "2023-10-08T20:46:56.764398",
            }
        }
    )


class ShelfInsertOutput(BaseModel):
    shelf: ShelfDetailWriteOutput
    shifted_count: int

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "shelf": {
                    "id": 10235,
                    "location": "Cabin Branch-1-52-L-23-3",
                    "shelf_number": 3,
                    "available_space": 33,
                },
                "shifted_count": 2,
            }
        }
    )

