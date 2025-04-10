import re

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, event
from sqlalchemy.exc import IntegrityError

from app.models.shelves import Shelf
from app.models.shelf_types import ShelfType
from app.models.shelf_numbers import ShelfNumber
from app.models.barcodes import Barcode
from app.models.barcode_types import BarcodeType
from app.models.container_types import ContainerType
from app.models.owners import Owner
from app.models.size_class import SizeClass
from app.models.sides import Side
from app.models.side_orientations import SideOrientation
from app.models.aisles import Aisle
from app.models.aisle_numbers import AisleNumber
from app.models.ladder_numbers import LadderNumber
from app.models.ladders import Ladder


def is_shelf_number_valid(value):
    if isinstance(value, (int)) and not isinstance(value, bool):
        if value < 1:
            return False
        return True
    else:
        return False


# def determine_full_or_short(ladder_id, session):
#     """
#     Business logic to map certain ladder's shelves
#     to 'Short' type.  If not 'Short', return 'Long'
#     """
#     ladder_id = int(ladder_id)
#     side_id = None
#     ladder_number_id = None
#     aisle_id = None
#     side_orientation_id = None

#     ladder_result = session.query(
#         Ladder.side_id,
#         Ladder.ladder_number_id
#     ).filter(
#         Ladder.id == ladder_id
#     ).first()

#     if ladder_result:
#         side_id, ladder_number_id = ladder_result

#     side_result = session.query(
#         Side.aisle_id,
#         Side.side_orientation_id
#     ).filter(
#         Side.id == side_id
#     ).first()

#     if side_result:
#         aisle_id, side_orientation_id = side_result

#     side_orientation = (
#         session.query(SideOrientation.name)
#         .filter(SideOrientation.id == side_orientation_id).scalar()
#     )

#     aisle_number_id = (
#         session.query(Aisle.aisle_number_id)
#         .filter(Aisle.id == aisle_id).scalar()
#     )

#     aisle_number = (
#         session.query(AisleNumber.number)
#         .filter(AisleNumber.id == aisle_number_id).scalar()
#     )

#     ladder_number = (
#         session.query(LadderNumber.number)
#         .filter(LadderNumber.id == ladder_number_id).scalar()
#     )

#     aisle_num_side_face_ladder_num = f"{aisle_number}|{side_orientation[0]}|{ladder_number}"

#     short_types = [
#         "1|L|4",
#         "1|L|14",
#         "1|L|24",
#         "2|L|4",
#         "2|L|14",
#         "2|L|24",
#         "3|L|4",
#         "3|L|14",
#         "3|L|24",
#         "4|L|4",
#         "4|L|14",
#         "4|L|24",
#         "5|L|4",
#         "5|L|14",
#         "5|L|24",
#         "6|L|4",
#         "6|L|13",
#         "6|L|22",
#         "6|L|31",
#         "7|L|4",
#         "7|L|13",
#         "7|L|22",
#         "7|L|31",
#         "8|L|4",
#         "8|L|13",
#         "8|L|22",
#         "8|L|31",
#         "9|L|4",
#         "9|L|13",
#         "9|L|22",
#         "9|L|31",
#         "10|L|4",
#         "10|L|13",
#         "10|L|22",
#         "10|L|31",
#         "11|L|4",
#         "11|L|13",
#         "11|L|22",
#         "11|L|31",
#         "12|L|4",
#         "12|L|13",
#         "12|L|22",
#         "12|L|31",
#         "13|L|4",
#         "13|L|13",
#         "13|L|22",
#         "13|L|31",
#         "14|L|4",
#         "14|L|13",
#         "14|L|22",
#         "14|L|31",
#         "15|L|4",
#         "15|L|13",
#         "15|L|22",
#         "15|L|31",
#         "16|L|4",
#         "16|L|13",
#         "16|L|22",
#         "16|L|31",
#         "17|L|4",
#         "17|L|13",
#         "17|L|22",
#         "17|L|31",
#         "18|L|4",
#         "18|L|13",
#         "18|L|22",
#         "18|L|31",
#         "19|L|4",
#         "19|L|13",
#         "19|L|22",
#         "19|L|31",
#         "20|L|4",
#         "20|L|13",
#         "20|L|22",
#         "20|L|31",
#         "52|L|4",
#         "52|L|13",
#         "52|L|22",
#         "52|L|31",
#         "53|L|4",
#         "53|L|13",
#         "53|L|22",
#         "53|L|31",
#         "54|L|4",
#         "54|L|13",
#         "54|L|22",
#         "54|L|31",
#         "55|L|4",
#         "55|L|13",
#         "55|L|22",
#         "55|L|31",
#         "56|L|4",
#         "56|L|13",
#         "56|L|22",
#         "56|L|31",
#         "57|R|4",
#         "57|R|13",
#         "57|R|22",
#         "57|R|31",
#         "58|R|4",
#         "58|R|13",
#         "58|R|22",
#         "58|R|31",
#         "59|R|4",
#         "59|R|13",
#         "59|R|22",
#         "59|R|31",
#         "60|R|4",
#         "60|R|13",
#         "60|R|22",
#         "60|R|31",
#         "61|R|4",
#         "61|R|13",
#         "61|R|22",
#         "61|R|31",
#         "62|L|4",
#         "62|L|13",
#         "62|L|22",
#         "62|L|31",
#         "63|L|4",
#         "63|L|13",
#         "63|L|22",
#         "63|L|31",
#         "64|L|4",
#         "64|L|13",
#         "64|L|22",
#         "64|L|31",
#         "65|L|4",
#         "65|L|13",
#         "65|L|22",
#         "65|L|31"
#     ]

#     if aisle_num_side_face_ladder_num in short_types:
#         return "Short"

#     return "Full"


def load_shelf(
    shelf_number,
    current_ladder_id,
    owner_name,
    shelf_height,
    shelf_width,
    shelf_depth,
    shelf_legacy_type,
    shelf_barcode_value,
    shelf_new_type,
    row_num,
    session
):
    """
    Loads and creates a unique shelf if it doesn't exist

    **Returns a list**
        list[0] = 1 if success, else 0
        list[1] = 1 if fail, else 0
        list[2] = dict if fail, else None
        list[3] = 1 if new record created, else 0
        list[4] = id (int) of created / retrieved record or None
        list[5] = id (int) or None

        loc.type == size_class (if this is not a zero, it will say the tray size). If it is a zero, it is a non-trayed-item, and if blank, nothing there.
        On non trays, we don’t really know the size_class.
        create a temporary one.
    """
    success = None
    failure = None
    error = None
    is_new_shelf_created = None
    processed_shelf_id = None
    processed_shelf_type_id = None

    # business logic
    if owner_name in ["lc", "Lc", "lC"]:
        owner_name = "LC"

    # satisfy shelf_number_id
    shelf_number = int(shelf_number)
    if is_shelf_number_valid(shelf_number):
        # get shelf_number object
        shelf_number_id = (
            session.query(ShelfNumber.id)
            .filter(ShelfNumber.number == shelf_number).scalar()
        )
        if not shelf_number_id:
            # create a shelf_number object
            try:
                # new_shelf_number_instance = ShelfNumber(number=shelf_number)
                # session.add(new_shelf_number_instance)
                # session.commit()
                # shelf_number_id = new_shelf_number_instance.id
                # ^ kept for ref. below version should handle parallel processing race condition
                new_shelf_number_instance = session.execute((
                    insert(ShelfNumber)
                    .values(number=shelf_number)
                    .on_conflict_do_nothing(index_elements=["number"])
                    .returning(ShelfNumber.id)
                )).fetchone()
                session.commit()
                shelf_number_id = new_shelf_number_instance[0]
            except Exception as e:
                success = 0
                failure = 1
                is_new_shelf_created = 0
                error = {
                    "row": row_num,
                    "shelf_number": shelf_number,
                    "barcode": shelf_barcode_value,
                    "owner": owner_name,
                    "type": shelf_legacy_type,
                    "reason": f"{e}"
                }
                return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]
    else:
        success = 0
        failure = 1
        is_new_shelf_created = 0
        error = {
            "row": row_num,
            "shelf_number": shelf_number,
            "barcode": shelf_barcode_value,
            "owner": owner_name,
            "type": shelf_legacy_type,
            "reason": "shelf_number from 'position' is invalid"
        }
        session.expire_all()
        return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]

    # satisfy barcode_id
    if not shelf_barcode_value:
        success = 0
        failure = 1
        is_new_shelf_created = 0
        error = {
            "row": row_num,
            "shelf_number": shelf_number,
            "barcode": shelf_barcode_value,
            "owner": owner_name,
            "type": shelf_legacy_type,
            "reason": "missing barcode"
        }
        session.expire_all()
        return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]
    else:
        # fix missing prefix zero's
        # if len(shelf_barcode_value) < 6:
        #     missing_zeros = 6 - len(shelf_barcode_value)
        #     for _ in range(missing_zeros):
        #         shelf_barcode_value = f"0{shelf_barcode_value}"
        
        # shelf barcodes can now be 5 or 6 digits (valid)
        if len(shelf_barcode_value) < 5:
            missing_zeros = 5 - len(shelf_barcode_value)
            for _ in range(missing_zeros):
                shelf_barcode_value = f"0{shelf_barcode_value}"

        # satisfy barcode_type_id
        barcode_type_id, allowed_pattern = session.execute(
            select(BarcodeType.id, BarcodeType.allowed_pattern)
            .where(BarcodeType.name == "Shelf")).fetchone()

        # satisfy barcode typecheck
        if not re.fullmatch(allowed_pattern, shelf_barcode_value):
            success = 0
            failure = 1
            is_new_shelf_created = 0
            error = {
                "row": row_num,
                "shelf_number": shelf_number,
                "barcode": shelf_barcode_value,
                "owner": owner_name,
                "type": shelf_legacy_type,
                "reason": "Invalid barcode format for shelves"
            }
            session.expire_all()
            return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]

        # get barcode object
        barcode_id = (
            session.query(Barcode.id)
            .filter(Barcode.value == shelf_barcode_value).scalar()
        )
        if not barcode_id:
            # or create new barcode object
            try:
                new_shelf_barcode_instance = Barcode(
                    value=shelf_barcode_value,
                    withdrawn=False,
                    type_id=barcode_type_id
                )
                session.add(new_shelf_barcode_instance)
                session.commit()
                barcode_id = new_shelf_barcode_instance.id
            except Exception as e:
                success = 0
                failure = 1
                is_new_shelf_created = 0
                error = {
                    "row": row_num,
                    "shelf_number": shelf_number,
                    "barcode": shelf_barcode_value,
                    "owner": owner_name,
                    "type": shelf_legacy_type,
                    "reason": f"{e}"
                }
                session.expire_all()
                return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]

    # everything has a legacy type
    # so find new way to determine container type
    # satisfy container_type_id
    if "NT" in shelf_legacy_type:
        container_type = "Non-Tray"
    else:
        container_type = "Tray"

    # if not shelf_legacy_type:
    #     container_type = "Non-Tray"
    # elif shelf_legacy_type == "0":
    #     container_type = "Non-Tray"
    # else:
    #     container_type = "Tray"

    container_type_id = (
        session.query(ContainerType.id)
        .filter(ContainerType.type == container_type).scalar()
    )

    # satisfy owner_id
    # nullable field, can pass directly
    owner_id = (
        session.query(Owner.id)
        .filter(Owner.name == owner_name).scalar()
    )
    # check for unfound
    if owner_name and not owner_id:
        success = 0
        failure = 1
        is_new_shelf_created = 0
        error = {
            "row": row_num,
            "shelf_number": shelf_number,
            "barcode": shelf_barcode_value,
            "owner": owner_name,
            "type": shelf_legacy_type,
            "reason": "Unregistered owner"
        }
        session.expire_all()
        return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]

    # business logic short types
    # shelf_type_type = determine_full_or_short(current_ladder_id, session)
    # ^ returns 'Short' or 'Full' currently
    # intention is to get shelf_type.type value
    # New method cuts out 6 queries per row
    shelf_type_type = shelf_new_type

    # satisfy shelf_type_id
    # if not shelf_legacy_type:
    #     # change when you know full vs short driver
    #     shelf_type_result = (
    #         session.query(ShelfType.id)
    #         .join(SizeClass, SizeClass.id == ShelfType.size_class_id)
    #         .filter(SizeClass.short_name == "NT").where(
    #             ShelfType.type == shelf_type_type
    #         ).first()
    #     )
    #     shelf_type_id = shelf_type_result[0] if shelf_type_result else None
    # elif shelf_legacy_type == "0":
    #     shelf_type_result = (
    #         session.query(ShelfType.id)
    #         .join(SizeClass, SizeClass.id == ShelfType.size_class_id)
    #         .filter(SizeClass.short_name == "NT").where(
    #             ShelfType.type == shelf_type_type
    #         ).first()
    #     )
    #     shelf_type_id = shelf_type_result[0] if shelf_type_result else None
    if not shelf_legacy_type.isalpha():
        success = 0
        failure = 1
        is_new_shelf_created = 0
        error = {
            "row": row_num,
            "shelf_number": shelf_number,
            "barcode": shelf_barcode_value,
            "owner": owner_name,
            "type": shelf_legacy_type,
            "reason": "type size class is not valid"
        }
        session.expire_all()
        return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]
    else:
        if shelf_legacy_type == "Unassigned":
            shelf_legacy_type = "UNA"
        # s_l_t_uppercase = shelf_legacy_type.upper() #convert before eval, else nullifies index benefits
        shelf_type_result = (
            session.query(ShelfType.id)
            .join(SizeClass, SizeClass.id == ShelfType.size_class_id)
            .filter(SizeClass.short_name == shelf_legacy_type).where(
                ShelfType.type == shelf_type_type
            ).first()
        )
        shelf_type_id = shelf_type_result[0] if shelf_type_result else None

    if not shelf_type_id:
        success = 0
        failure = 1
        is_new_shelf_created = 0
        error = {
            "row": row_num,
            "shelf_number": shelf_number,
            "barcode": shelf_barcode_value,
            "owner": owner_name,
            "type": shelf_legacy_type,
            "reason": f"shelf_type is unregistered for type: {shelf_type_type}"
        }
        session.expire_all()
        return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]

    # valid location to attempt shelf creation
    success = 1
    failure = 0
    try:
        # create or skip if exists
        processed_shelf = session.execute((
            insert(Shelf)
            .values(
                barcode_id = barcode_id,
                ladder_id = current_ladder_id,
                shelf_number_id = shelf_number_id,
                owner_id = owner_id,
                container_type_id = container_type_id,
                shelf_type_id = shelf_type_id,
                height = shelf_height,
                width = shelf_width,
                depth = shelf_depth
            )
            .returning(Shelf.id)
        )).fetchone()

        session.commit()
    except IntegrityError as e:
        session.rollback()
        success = 0
        failure = 1
        is_new_shelf_created = 0
        error = {
            "row": row_num,
            "shelf_number": shelf_number,
            "barcode": shelf_barcode_value,
            "owner": owner_name,
            "type": shelf_legacy_type,
            "reason": f"{e.orig}"
        }
        session.expire_all()
        return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]

    # fetch shelf if record not created
    if not processed_shelf:
        is_new_shelf_created = 0 # new shelf not created
        processed_shelf = session.execute(
            select(Shelf.id).where(
                (Shelf.barcode_id == barcode_id)
            )
        ).fetchone()
    else:
        is_new_shelf_created = 1 # new shelf created
        # generate shelf.location and shelf.internal_location
        shelf_to_update = session.query(Shelf).filter(Shelf.id == processed_shelf[0]).first()
        shelf_to_update.update_shelf_address(session=session)
        session.commit()

    processed_shelf_id = processed_shelf[0]
    processed_shelf_type_id = shelf_type_id

    if not processed_shelf_id:
        # something went wrong
        success = 0
        failure = 1
        error = {
            "row": row_num,
            "shelf_number": shelf_number,
            "barcode": shelf_barcode_value,
            "owner": owner_name,
            "type": shelf_legacy_type,
            "reason": "Failed to retrieve an existing shelf"
        }
        # Clear session when commit() doesn't
        session.expire_all()

    return [success, failure, error, is_new_shelf_created, processed_shelf_id, processed_shelf_type_id]
