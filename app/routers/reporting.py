from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlmodel import paginate
from sqlalchemy import func, union_all, literal, and_
from sqlmodel import Session, select

from app.database.session import get_session
from app.logger import inventory_logger
from app.models.items import Item
from app.models.media_types import MediaType
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.size_class import SizeClass
from app.schemas.reporting import AccessionItemsDetailOutput

router = APIRouter(
    prefix="/reporting",
    tags=["reporting"],
)


@router.get("/accession-items", response_model=Page[AccessionItemsDetailOutput])
def get_accessioned_items_aggregate(
    session: Session = Depends(get_session),
    owner_id: list[int] = Query(default=None),
    size_class_id: list[int] = Query(default=None),
    media_type_id: list[int] = Query(default=None),
    from_dt: datetime = Query(default=None),
    to_dt: datetime = Query(default=None),
):
    item_query_conditions = []
    non_tray_item_query_conditions = []
    selection = []
    group_by = []

    try:
        if owner_id:
            item_query_conditions.append(Item.owner_id.in_(owner_id))
            non_tray_item_query_conditions.append(NonTrayItem.owner_id.in_(owner_id))
        if size_class_id:
            item_query_conditions.append(Item.size_class_id.in_(size_class_id))
            non_tray_item_query_conditions.append(
                NonTrayItem.size_class_id.in_(size_class_id)
            )
        if media_type_id:
            item_query_conditions.append(Item.media_type_id.in_(media_type_id))
            non_tray_item_query_conditions.append(
                NonTrayItem.media_type_id.in_(media_type_id)
            )
        if from_dt:
            item_query_conditions.append(Item.accession_dt >= from_dt)
            non_tray_item_query_conditions.append(NonTrayItem.accession_dt >= from_dt)
        if to_dt:
            item_query_conditions.append(Item.accession_dt <= to_dt)
            non_tray_item_query_conditions.append(NonTrayItem.accession_dt <= to_dt)

        item_query = (
            select(
                Item.id.label("item_id"),
                Owner.name.label("owner_name"),
                SizeClass.name.label("size_class_name"),
                MediaType.name.label("media_type_name"),
            )
            .select_from(Item)
            .join(Owner, Owner.id == Item.owner_id)
            .join(SizeClass, SizeClass.id == Item.size_class_id)
            .join(MediaType, MediaType.id == Item.media_type_id)
            .filter(and_(*item_query_conditions))
        )
        non_tray_item_query = (
            select(
                NonTrayItem.id.label("item_id"),
                Owner.name.label("owner_name"),
                SizeClass.name.label("size_class_name"),
                MediaType.name.label("media_type_name"),
            )
            .select_from(NonTrayItem)
            .join(Owner, Owner.id == NonTrayItem.owner_id)
            .join(SizeClass, SizeClass.id == NonTrayItem.size_class_id)
            .join(MediaType, MediaType.id == NonTrayItem.media_type_id)
            .filter(and_(*non_tray_item_query_conditions))
        )

        combined_query = union_all(item_query, non_tray_item_query).subquery()

        if owner_id:
            selection.append(combined_query.c.owner_name)
            group_by.append(combined_query.c.owner_name)
        if size_class_id:
            selection.append(combined_query.c.size_class_name)
            group_by.append(combined_query.c.size_class_name)
        if media_type_id:
            selection.append(combined_query.c.media_type_name)
            group_by.append(combined_query.c.media_type_name)

        if not selection:
            final_query = select(
                literal("All").label("owner_name"),
                literal("All").label("size_class_name"),
                literal("All").label("media_type_name"),
                func.count().label("count"),
            ).select_from(combined_query)

        else:
            final_query = select(
                *selection,
                func.count().label("count"),
            ).group_by(*group_by)

        return paginate(session, final_query)

    except Exception as e:
        inventory_logger.error(e)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
