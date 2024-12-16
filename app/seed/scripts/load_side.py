from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from app.models.sides import Side
from app.models.side_orientations import SideOrientation
from app.models.aisles import Aisle
from app.models.aisle_numbers import AisleNumber


def load_side(
    side_orientation,
    aisle_number,
    row_num,
    session
):
    """
    Loads and creates a unique Side object
    if it doesn't exist.

    **Returns a list**
        list[0] = 1 if success, else 0
        list[1] = 1 if fail, else 0
        list[2] = dict if fail, else None
        list[3] = 1 if new record created, else 0
        list[4] = id (int) of created / retrieved record or None
    """
    success = None
    failure = None
    error = None
    is_new_side_created = None
    processed_side_id = None

    # business logic
    if side_orientation in [ "M", "W"]:
        side_orientation = "R"


    side_orientation_id = (
        session.query(SideOrientation.id)
        .filter(SideOrientation.name.like(f"{side_orientation}%")).scalar()
    )

    aisle_id = (
        session.query(Aisle.id, AisleNumber.id)
        .join(AisleNumber, AisleNumber.id == Aisle.aisle_number_id)
        .filter(AisleNumber.number == aisle_number).scalar()
    )

    if aisle_id and side_orientation_id:
        # valid location to attempt side creation
        success = 1
        failure = 0
        # create or skip if exists
        processed_side = session.execute((
            insert(Side)
            .values(aisle_id = aisle_id, side_orientation_id = side_orientation_id)
            .on_conflict_do_nothing(index_elements=["aisle_id", "side_orientation_id"])
            .returning(Side.id)
        )).fetchone()

        session.commit()

        # fetch side if record not created
        if not processed_side:
            is_new_side_created = 0 # new side not created
            processed_side = session.execute(
                select(Side.id).where(
                    (Side.aisle_id == aisle_id) &
                    (Side.side_orientation_id == side_orientation_id)
                )
            ).fetchone()
        else:
            is_new_side_created = 1 # new side created

        processed_side_id = processed_side[0]

    else:
        success = 0
        failure = 1
        is_new_side_created = 0
        error = {
            "row": row_num,
            "aisle_number": aisle_number,
            "side_orientation": side_orientation,
            "reason": "aisle_number or side_orientation doesn't exist"
        }
        # Clear session when commit() doesn't
        session.expire_all()

    return [success, failure, error, is_new_side_created, processed_side_id]
