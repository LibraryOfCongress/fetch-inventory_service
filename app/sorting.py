from operator import or_

from sqlalchemy import asc, desc, func, inspect, case, Text, Integer
from sqlalchemy.types import Enum as enum
from sqlalchemy.orm import Query, aliased
from sqlalchemy.sql import union_all, select

from app.config.exceptions import BadRequest
from app.models.aisle_numbers import AisleNumber

from app.models.barcodes import Barcode
from app.models.buildings import Building
from app.models.container_types import ContainerType
from app.models.delivery_locations import DeliveryLocation
from app.models.item_withdrawals import ItemWithdrawal
from app.models.items import Item
from app.models.ladder_numbers import LadderNumber
from app.models.media_types import MediaType
from app.models.move_discrepancies import MoveDiscrepancy
from app.models.non_tray_Item_withdrawal import NonTrayItemWithdrawal
from app.models.non_tray_items import NonTrayItem
from app.models.owners import Owner
from app.models.pick_lists import PickList
from app.models.priorities import Priority
from app.models.refile_items import RefileItem
from app.models.refile_jobs import RefileJob
from app.models.refile_non_tray_items import RefileNonTrayItem
from app.models.request_types import RequestType
from app.models.requests import Request
from app.models.shelf_numbers import ShelfNumber
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_positions import ShelfPosition
from app.models.shelf_types import ShelfType
from app.models.shelves import Shelf
from app.models.shelving_job_discrepancies import ShelvingJobDiscrepancy
from app.models.shelving_jobs import ShelvingJob
from app.models.size_class import SizeClass
from app.models.trays import Tray
from app.models.users import User
from app.models.verification_changes import VerificationChange
from app.models.verification_jobs import VerificationJob
from app.models.withdraw_jobs import WithdrawJob


class BaseSorter:
    """
    Base sorting class that provides sorting by model attributes.
    """

    def __init__(self, model):
        self.model = model

    def get_sortable_fields(self):
        """
        Retrieves all column names from the SQLAlchemy model.
        """
        return {column.key for column in inspect(self.model).c}

    def apply_sorting(self, query: Query, sort_params):
        """
        Applies sorting based on the model's fields.
        If custom sorting is needed, subclasses should override `custom_sort`.
        """
        if sort_params.sort_order not in ["asc", "desc"]:
            raise BadRequest(
                detail="Invalid value for 'sort_order'. Allowed values are: 'asc', 'desc'"
            )

        order_func = asc if sort_params.sort_order == "asc" else desc
        # Custom sort logic can be defined in subclasses
        query = self.custom_sort(query, sort_params, order_func)

        return query

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Default sorting: Sort by the model's column if it exists.
        Custom sorting can be implemented in subclasses.
        """
        sort_field = getattr(self.model, sort_params.sort_by, None)

        if sort_field:
            if hasattr(sort_field, "type") and isinstance(sort_field.type, enum):
                query = query.order_by(order_func(func.cast(sort_field, Text)))
                return query

            return query.order_by(order_func(sort_field))

        raise BadRequest(detail=f"Invalid sort parameter: {sort_params.sort_by}")


# ShelvingJobSorter: Custom Sorter for a Shelving Job List Endpoint
class ShelvingJobSorter(BaseSorter):
    """
    Request Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """

        if sort_params.sort_by == "container_count":
            container_count_subquery = (
                select(
                    ShelvingJob.id,
                    func.coalesce(func.count(Tray.id), 0)
                    + func.coalesce(func.count(NonTrayItem.id), 0),
                )
                .outerjoin(Tray, Tray.shelving_job_id == ShelvingJob.id)
                .outerjoin(NonTrayItem, NonTrayItem.shelving_job_id == ShelvingJob.id)
                .group_by(ShelvingJob.id)
                .alias("container_count_map")
            )

            # Join with ShelvingJob and order by container count
            query = query.outerjoin(
                container_count_subquery,
                ShelvingJob.id == container_count_subquery.c.id,
            ).order_by(
                order_func(container_count_subquery.c[1])
            )  # Index 1 is the count column
            return query

        # Fall back to base sorting if no custom sort logic applies
        return super().custom_sort(query, sort_params, order_func)


# RequestSorter: Custom Sorter for a Request List Endpoint
class RequestSorter(BaseSorter):
    """
    Request Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """

        # Sorting by barcode_value via Item or NonTrayItem
        if sort_params.sort_by == "barcode_value":
            # Aliases to avoid conflicts
            item_alias = aliased(Item)
            non_tray_item_alias = aliased(NonTrayItem)
            barcode_item_alias = aliased(Barcode)
            barcode_non_tray_alias = aliased(Barcode)

            # Join Request -> Item -> Barcode (for Items)
            query = query.outerjoin(
                item_alias, Request.item_id == item_alias.id
            ).outerjoin(
                barcode_item_alias, item_alias.barcode_id == barcode_item_alias.id
            )

            # Join Request -> NonTrayItem -> Barcode (for Non-Tray Items)
            query = query.outerjoin(
                non_tray_item_alias, Request.non_tray_item_id == non_tray_item_alias.id
            ).outerjoin(
                barcode_non_tray_alias,
                non_tray_item_alias.barcode_id == barcode_non_tray_alias.id,
            )

            # Ensure sorting by barcode value from both barcode tables
            query = query.order_by(
                order_func(
                    func.coalesce(
                        barcode_item_alias.value, barcode_non_tray_alias.value
                    )
                )
            )
            return query
        if sort_params.sort_by == "media_type":
            # Aliases to avoid conflicts
            item_alias = aliased(Item)
            non_tray_item_alias = aliased(NonTrayItem)
            media_type_item_alias = aliased(MediaType)
            media_type_non_tray_alias = aliased(MediaType)

            # Join Request -> Item -> MediaType
            query = query.outerjoin(
                item_alias, Request.item_id == item_alias.id
            ).outerjoin(
                media_type_item_alias,
                item_alias.media_type_id == media_type_item_alias.id,
            )

            # Join Request -> NonTrayItem -> MediaType
            query = query.outerjoin(
                non_tray_item_alias, Request.non_tray_item_id == non_tray_item_alias.id
            ).outerjoin(
                media_type_non_tray_alias,
                non_tray_item_alias.media_type_id == media_type_non_tray_alias.id,
            )

            # Select the correct media type name for sorting (prioritize Item media type first)
            query = query.order_by(
                order_func(
                    func.coalesce(
                        media_type_item_alias.name, media_type_non_tray_alias.name
                    )
                )
            )
            return query

        if sort_params.sort_by == "location":
            # Aliases for clarity
            item_alias = aliased(Item)
            tray_alias = aliased(Tray)
            non_tray_item_alias = aliased(NonTrayItem)
            shelf_position_alias = aliased(ShelfPosition)

            # Subquery to unify shelf positions from Items (via Tray) and NonTrayItems
            location_subquery = union_all(
                # Items: Request -> Item -> Tray -> ShelfPosition
                select(
                    Request.id, tray_alias.shelf_position_id.label("shelf_position_id")
                )
                .join(item_alias, Request.item_id == item_alias.id)
                .join(tray_alias, item_alias.tray_id == tray_alias.id),
                # NonTrayItems: Request -> NonTrayItem -> ShelfPosition
                select(
                    Request.id,
                    non_tray_item_alias.shelf_position_id.label("shelf_position_id"),
                ).join(
                    non_tray_item_alias,
                    Request.non_tray_item_id == non_tray_item_alias.id,
                ),
            ).alias("location_map")

            # Join the subquery with ShelfPosition and order by ShelfPosition.location
            query = (
                query.outerjoin(location_subquery, Request.id == location_subquery.c.id)
                .outerjoin(
                    shelf_position_alias,
                    location_subquery.c.shelf_position_id == shelf_position_alias.id,
                )
                .order_by(order_func(shelf_position_alias.location))
            )

            return query
        # if sort_params.sort_by == "status":
        #     # Aliases for clarity
        #     item_alias = aliased(Item)
        #     non_tray_item_alias = aliased(NonTrayItem)
        #
        #     # Join Request -> Item
        #     query = query.outerjoin(item_alias, Request.item_id == item_alias.id)
        #
        #     # Join Request -> NonTrayItem
        #     query = query.outerjoin(
        #         non_tray_item_alias, Request.non_tray_item_id == non_tray_item_alias.id
        #         )
        #
        #     # Cast ENUM fields to TEXT before applying COALESCE()
        #     status_column = func.coalesce(
        #         cast(item_alias.status, String),
        #         cast(non_tray_item_alias.status, String)
        #     )
        #
        #     # Apply sorting without modifying return columns
        #     query = query.order_by(order_func(status_column))
        #
        #     return query
        if sort_params.sort_by == "request_type":
            return query.join(RequestType).order_by(order_func(RequestType.type))
        if sort_params.sort_by == "building_name":
            return query.join(Building).order_by(order_func(Building.name))
        if sort_params.sort_by == "priority":
            return query.join(Priority).order_by(order_func(Priority.value))
        if sort_params.sort_by == "delivery_location":
            return query.join(DeliveryLocation).order_by(
                order_func(DeliveryLocation.name)
            )
        if sort_params.sort_by == "request_count":
            query = (
                query.join(Request)
                .group_by(self.model.id)
                .order_by(order_func(func.count(Request.id)))
            )
            return query

        # Fall back to base sorting if no custom sort logic applies
        if sort_params.sort_by == "request_by":
            return query.join(User).order_by(
                order_func(func.concat(User.first_name, " ", User.last_name)
                )
            )
        return super().custom_sort(query, sort_params, order_func)


class PickListSorter(BaseSorter):
    """
    Pick List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """

        if sort_params.sort_by == "request_count":
            # Subquery to get the earliest request create_dt per PickList
            request_sort_subquery = (
                select(
                    Request.pick_list_id,
                    func.min(Request.create_dt).label("first_request_date"),
                )
                .group_by(Request.pick_list_id)
                .alias("request_sort_map")
            )

            # Join PickList with the request sorting subquery
            query = query.outerjoin(
                request_sort_subquery,
                PickList.id == request_sort_subquery.c.pick_list_id,
            ).order_by(order_func(request_sort_subquery.c.first_request_date))

            return query
        if sort_params.sort_by == "building_name":
            return query.join(Building).order_by(order_func(Building.name))

        # Fall back to base sorting if no custom sort logic applies
        return super().custom_sort(query, sort_params, order_func)


class RefileQueueSorter(BaseSorter):
    """
    Refile Queue List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """
        if hasattr(query, "c"):
            return query.order_by(order_func(sort_params.sort_by))

        return super().custom_sort(query, sort_params, order_func)


class RefileJobSorter(BaseSorter):
    """
    Refile Job List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """
        if sort_params.sort_by == "item_count":
            items_count_subquery = (
                select(
                    RefileJob.id,
                    func.coalesce(func.count(RefileItem.id), 0)
                    + func.coalesce(func.count(RefileNonTrayItem.id), 0),
                )
                .outerjoin(RefileItem, RefileItem.refile_job_id == RefileJob.id)
                .outerjoin(
                    RefileNonTrayItem, RefileNonTrayItem.refile_job_id == RefileJob.id
                )
                .group_by(RefileJob.id)
                .alias("item_count_map")
            )

            # Join with ShelvingJob and order by container count
            query = query.outerjoin(
                items_count_subquery, RefileJob.id == items_count_subquery.c.id
            ).order_by(
                order_func(items_count_subquery.c[1])
            )  # Index 1 is the count column
            return query

        if sort_params.sort_by == "shelved_count":
            # Join with RefileJob and order by shelved count
            container_count_subquery = (
                select(
                    RefileJob.id,
                    (
                        func.coalesce(
                            func.sum(case((Item.status == "In", 1), else_=0)), 0
                        )
                        + func.coalesce(
                            func.sum(case((NonTrayItem.status == "In", 1), else_=0)), 0
                        )
                    ).label("shelved_count"),
                )
                .select_from(RefileJob)
                .outerjoin(RefileItem, RefileItem.refile_job_id == RefileJob.id)
                .outerjoin(Item, Item.id == RefileItem.item_id)
                .outerjoin(
                    RefileNonTrayItem, RefileNonTrayItem.refile_job_id == RefileJob.id
                )
                .outerjoin(
                    NonTrayItem, NonTrayItem.id == RefileNonTrayItem.non_tray_item_id
                )
                .group_by(RefileJob.id)
            ).alias("container_count_map")

            query = query.outerjoin(
                container_count_subquery, RefileJob.id == container_count_subquery.c.id
            ).order_by(order_func(container_count_subquery.c.shelved_count))

            return query

        return super().custom_sort(query, sort_params, order_func)


class WithdrawJobSorter(BaseSorter):

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """
        if sort_params.sort_by == "item_count":
            items_count_subquery = (
                select(
                    WithdrawJob.id,
                    func.coalesce(func.count(ItemWithdrawal.id), 0)
                    + func.coalesce(func.count(NonTrayItemWithdrawal.id), 0),
                )
                .outerjoin(
                    ItemWithdrawal, ItemWithdrawal.withdraw_job_id == WithdrawJob.id
                )
                .outerjoin(
                    NonTrayItemWithdrawal,
                    NonTrayItemWithdrawal.withdraw_job_id == WithdrawJob.id,
                )
                .group_by(WithdrawJob.id)
                .alias("item_count_map")
            )

            # Join with ShelvingJob and order by container count
            query = query.outerjoin(
                items_count_subquery, WithdrawJob.id == items_count_subquery.c.id
            ).order_by(
                order_func(items_count_subquery.c[1])
            )  # Index 1 is the count column
            return query

        return super().custom_sort(query, sort_params, order_func)


class ShelvingSorter(BaseSorter):
    """
    Shelving List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """
        if sort_params.sort_by == "shelf_number":
            return query.join(ShelfNumber).order_by(order_func(ShelfNumber.number))
        if sort_params.sort_by == "size_class":
            return (
                query.join(ShelfType)
                .join(SizeClass)
                .order_by(order_func(SizeClass.name))
            )
        if sort_params.sort_by == "shelf_type":
            return query.join(ShelfType).order_by(order_func(ShelfType.type))
        if sort_params.sort_by == "container_type":
            return query.join(ContainerType).order_by(order_func(ContainerType.type))
        if sort_params.sort_by == "owner":
            return query.join(Owner).order_by(order_func(Owner.name))
        if sort_params.sort_by == "barcode_value":
            return query.join(Barcode).order_by(order_func(Barcode.value))

        return super().custom_sort(query, sort_params, order_func)


class ItemSorter(BaseSorter):
    """
    Non Tray Item List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """
        if sort_params.sort_by == "owner":
            return query.join(Owner).order_by(order_func(Owner.name))
        if sort_params.sort_by == "size_class":
            return query.join(SizeClass).order_by(order_func(SizeClass.name))
        if sort_params.sort_by == "media_type":
            return query.join(MediaType).order_by(order_func(MediaType.name))
        if sort_params.sort_by == "barcode_value":
            return query.outerjoin(
                Barcode,
                or_(
                    self.model.barcode_id == Barcode.id,
                    self.model.withdrawn_barcode_id == Barcode.id,
                ),
            ).order_by(order_func(Barcode.value))

        return super().custom_sort(query, sort_params, order_func)


class OpenLocationsSorter(BaseSorter):
    """
    Open Location List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        """
        Overrides the default sort to allow custom sorting for specific fields.
        """
        if sort_params.sort_by == "owner":
            return query.order_by(order_func(Owner.name))
        if sort_params.sort_by == "size_class":
            return query.order_by(order_func(SizeClass.short_name))
        if sort_params.sort_by == "media_type":
            return query.order_by(order_func(MediaType.name))
        if sort_params.sort_by == "location":
            # Join ShelfPosition if not already joined
            query = query.order_by(
                order_func(func.split_part(Shelf.location, "-", 1)),
                order_func(func.cast(func.split_part(Shelf.location, "-", 2), Integer)),
                order_func(func.cast(func.split_part(Shelf.location, "-", 3), Integer)),
                order_func(func.split_part(Shelf.location, "-", 4)),
                order_func(func.cast(func.split_part(Shelf.location, "-", 5), Integer)),
                order_func(func.cast(func.split_part(Shelf.location, "-", 6), Integer)),
            )

            return query

        return super().custom_sort(query, sort_params, order_func)


class AisleItemsCountSorter(BaseSorter):
    """
    Aisle Items Count List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "aisle_number":
            return query.order_by(order_func("aisle_number"))
        if sort_params.sort_by == "shelf_count":
            return query.order_by(order_func("shelf_count"))
        if sort_params.sort_by == "tray_count":
            return query.order_by(order_func("tray_count"))
        if sort_params.sort_by == "item_count":
            return query.order_by(order_func("item_count"))
        if sort_params.sort_by == "non_tray_item_count":
            return query.order_by(order_func("non_tray_item_count"))
        if sort_params.sort_by == "total_item_count":
            return query.order_by(order_func("total_item_count"))

        return super().custom_sort(query, sort_params, order_func)


class NonTrayItemCountSorter(BaseSorter):
    """
    Non Tray Item Count List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "size_class_short_name":
            return query.order_by(order_func("size_class_short_name"))
        if sort_params.sort_by == "non_tray_item_count":
            return query.order_by(order_func("non_tray_item_count"))

        return super().custom_sort(query, sort_params, order_func)


class TrayItemCountSorter(BaseSorter):
    """
    Tray Item Count List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "size_class_short_name":
            return query.order_by(order_func("size_class_short_name"))
        if sort_params.sort_by == "tray_count":
            return query.order_by(order_func("tray_count"))
        if sort_params.sort_by == "tray_item_count":
            return query.order_by(order_func("tray_item_count"))

        return super().custom_sort(query, sort_params, order_func)


class VerificationChangeSorter(BaseSorter):
    """
    Verification Change List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "completed_dt":
            return query.order_by(order_func("update_dt"))
        if sort_params.sort_by == "completed_by":
            return query.order_by(order_func("completed_by_id"))
        if sort_params.sort_by == "item_barcode":
            return query.order_by(order_func("item_barcode_value"))
        if sort_params.sort_by == "tray_barcode":
            return query.order_by(order_func("tray_barcode_value"))
        if sort_params.sort_by == "action":
            return query.order_by(
                order_func(func.cast(VerificationChange.change_type, Text))
            )

        return super().custom_sort(query, sort_params, order_func)


class RetrievalItemCountSorter(BaseSorter):
    """
    Retrieval Item Count List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "owner_name":
            return query.order_by(order_func("owner_name"))
        if sort_params.sort_by == "total_item_retrieved_count":
            return query.order_by(order_func("total_item_retrieved_count"))
        if sort_params.sort_by == "max_retrieved_count":
            return query.order_by(order_func("max_retrieved_count"))

        return super().custom_sort(query, sort_params, order_func)


class ShelvingJobDiscrepancySorter(BaseSorter):
    """
    Shelving Job Discrepancy List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "owner":
            query = query.join(Owner, ShelvingJobDiscrepancy.owner_id == Owner.id)
            return query.order_by(order_func(Owner.name))
        if sort_params.sort_by == "assigned_user":
            query = query.join(User, ShelvingJobDiscrepancy.assigned_user_id == User.id)
            return query.order_by(
                order_func(func.concat(User.first_name, " ", User.last_name))
            )
        if sort_params.sort_by == "barcode_value":
            # Outer join to Tray and NonTrayItem so that if one is missing, the row is not dropped.
            query = query.outerjoin(Tray, ShelvingJobDiscrepancy.tray_id == Tray.id)
            query = query.outerjoin(
                NonTrayItem, ShelvingJobDiscrepancy.non_tray_item_id == NonTrayItem.id
            )
            # Outer join Barcode by checking both possibilities
            query = query.outerjoin(
                Barcode,
                or_(
                    Tray.barcode_id == Barcode.id, NonTrayItem.barcode_id == Barcode.id
                ),
            )
            return query.order_by(order_func(Barcode.value))
        if sort_params.sort_by == "size_class":
            query = query.join(
                SizeClass, ShelvingJobDiscrepancy.size_class_id == SizeClass.id
            )
            return query.order_by(order_func(SizeClass.short_name))

        return super().custom_sort(query, sort_params, order_func)


class UserSorter(BaseSorter):
    """
    User List Sort By with specific sorting logic for related models.
    """

    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "name":
            return query.order_by(func.concat(User.first_name, " ", User.last_name))

        return super().custom_sort(query, sort_params, order_func)


class MoveDiscrepancySorter(BaseSorter):
    """
    Move Discrepancy List Sort By with specific sorting logic for related models.
    """
    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by == "owner":
            query = query.join(Owner, MoveDiscrepancy.owner_id == Owner.id)
            return query.order_by(order_func(Owner.name))
        if sort_params.sort_by == "assigned_user":
            query = query.join(User, MoveDiscrepancy.assigned_user_id == User.id)
            return query.order_by(
                order_func(func.concat(User.first_name, " ", User.last_name))
            )
        if sort_params.sort_by == "barcode_value":
            # Aliases to avoid conflicts
            tray_alias = aliased(Tray)
            item_alias = aliased(Item)
            non_tray_item_alias = aliased(NonTrayItem)
            barcode_tray_alias = aliased(Barcode)
            barcode_item_alias = aliased(Barcode)
            barcode_non_tray_alias = aliased(Barcode)

            # Join MoveDiscrepancy -> Tray -> Barcode (for Trays)
            query = query.outerjoin(
                tray_alias, MoveDiscrepancy.tray_id == tray_alias.id
            ).outerjoin(
                barcode_tray_alias, tray_alias.barcode_id == barcode_tray_alias.id
            )

            # Join MoveDiscrepancy -> Item -> Barcode (for Items)
            query = query.outerjoin(
                item_alias, MoveDiscrepancy.item_id == item_alias.id
            ).outerjoin(
                barcode_item_alias, item_alias.barcode_id == barcode_item_alias.id
            )

            # Join Request -> NonTrayItem -> Barcode (for Non-Tray Items)
            query = query.outerjoin(
                non_tray_item_alias, MoveDiscrepancy.non_tray_item_id == non_tray_item_alias.id
            ).outerjoin(
                barcode_non_tray_alias,
                non_tray_item_alias.barcode_id == barcode_non_tray_alias.id,
            )

            # Ensure sorting by barcode value from both barcode tables
            query = query.order_by(
                order_func(
                    func.coalesce(
                        barcode_tray_alias.value, barcode_item_alias.value,
                        barcode_non_tray_alias.value
                    )
                )
            )
            return query

        if sort_params.sort_by == "size_class":
            query = query.join(
                SizeClass, MoveDiscrepancy.size_class_id == SizeClass.id
            )
            return query.order_by(order_func(SizeClass.short_name))
        if sort_params.sort_by == "container_type":
            query = query.join(
                ContainerType, MoveDiscrepancy.container_type_id == ContainerType.id
            )
            return query.order_by(order_func(ContainerType.type))

        return super().custom_sort(query, sort_params, order_func)


class AisleSorter(BaseSorter):
    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by.lower() == 'aisle_number':
            return query.join(AisleNumber).order_by(order_func(AisleNumber.number))

        return super().custom_sort(query, sort_params, order_func)


class LadderSorter(BaseSorter):
    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by.lower() == 'ladder_number':
            return query.join(LadderNumber).order_by(order_func(LadderNumber.number))

        return super().custom_sort(query, sort_params, order_func)


class ShelvesSorter(BaseSorter):
    def custom_sort(self, query: Query, sort_params, order_func):
        if sort_params.sort_by.lower() == 'shelf_position_number':
            return query.join(ShelfPositionNumber).order_by(order_func(ShelfPositionNumber.number))

        return super().custom_sort(query, sort_params, order_func)
