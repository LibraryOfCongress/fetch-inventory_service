from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from app.models.shelf_positions import ShelfPosition
from app.models.shelf_position_numbers import ShelfPositionNumber
from app.models.shelf_types import ShelfType


def load_shelf_positions(
    current_shelf_id,
    current_shelf_type_id,
    row_num,
    session,
    shelf_position_number_dict,
    shelf_type_max_cap_dict
):
    """
    Given a shelf, creates X shelf_positions
    where X is the shelf's shelf_type.max_capacity
    and associates the positions to the shelf(parent)

    **Returns a list**
        list[0] = 1 if success, else 0
        list[1] = 1 if fail, else 0
        list[2] = dict if fail, else None
        list[3] = num(int) of new records created, else 0
        list[4] = num(int) of records failed to create, else 0
    """
    success = None
    failure = None
    errors = []
    new_records_created = 0
    failed_records = 0

    # shelf_type = session.query(ShelfType).filter(ShelfType.id == current_shelf_type_id).first()
    shelf_type_max_capacity_value = shelf_type_max_cap_dict.get(current_shelf_type_id)

    # if not shelf_type:
    if not shelf_type_max_capacity_value:
        # ^ this is valid because if it's missing from here, it's missing.
        success = 0
        failure = 1
        errors.append(
            {
                "row": row_num,
                "shelf_id": current_shelf_id,
                "shelf_position_number": "NA",
                "reason": f"Failed to retrieve shelf_type_id {current_shelf_type_id}"
            }
        )
        # Clear session when commit() doesn't
        # session.expire_all()
        return [success, failure, errors, new_records_created, failed_records]
    else:
        success = 1
        failure = 0

    for i in range(shelf_type_max_capacity_value):
    # for i in range(shelf_type.max_capacity):
        try:
            # get shelf_position_number
            position_number = i + 1
            shelf_position_number_id = shelf_position_number_dict.get(position_number)
            # shelf_position_number_id = (
            #     session.query(ShelfPositionNumber.id)
            #     .filter(ShelfPositionNumber.number == position_number).scalar()
            # )
            if not shelf_position_number_id:
                failed_records += 1
                errors.append(
                    {
                        "row": row_num,
                        "shelf_id": current_shelf_id,
                        "shelf_position_number": position_number,
                        "reason": f"Unregistered shelf_position_number"
                    }
                )
                continue

            # create shelf_position
            new_shelf_position = session.execute((
                insert(ShelfPosition)
                .values(shelf_id = current_shelf_id, shelf_position_number_id = shelf_position_number_id)
                .returning(ShelfPosition.id)
            )).fetchone()

            session.commit()
            new_records_created += 1

            # MOVING LOCATION GEN TO NEW SCRIPT
            # generate shelf_position.location and shelf_position.internal_location
            # position_to_update = session.query(ShelfPosition).filter(ShelfPosition.id == new_shelf_position[0]).first()
            # position_to_update.update_position_address(session=session)

            session.commit()

        except Exception as e:
            session.rollback()
            errors.append(
                {
                    "row": row_num,
                    "shelf_id": current_shelf_id,
                    "shelf_position_number": position_number,
                    "reason": f"{e}"
                }
            )
            # Clear session when commit() doesn't
            # session.expire_all()
            failed_records += 1

    return [success, failure, errors, new_records_created, failed_records]
