from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from app.models.ladder_numbers import LadderNumber
from app.models.ladders import Ladder


def is_ladder_number_valid(value):
    if isinstance(value, (int)) and not isinstance(value, bool):
        if value > 76:
            return False
        if value < 1:
            return False
        return True
    else:
        return False


def load_ladder(
    ladder_number,
    current_side_id,
    row_num,
    session
):
    """
    Loads and creates a unique ladder if it doesn't exist.

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
    is_new_ladder_created = None
    processed_ladder_id = None

    ladder_remap = {
        '39': 38,
        '40': 37,
        '41': 36,
        '42': 35,
        '43': 34,
        '44': 33,
        '45': 32,
        '46': 31,
        '47': 30,
        '48': 29,
        '49': 28,
        '50': 27,
        '51': 26,
        '52': 25,
        '53': 24,
        '54': 23,
        '55': 22,
        '56': 21,
        '57': 20,
        '58': 19,
        '59': 18,
        '60': 17,
        '61': 16,
        '62': 15,
        '63': 14,
        '64': 13,
        '65': 12,
        '66': 11,
        '67': 10,
        '68': 9,
        '69': 8,
        '70': 7,
        '71': 6,
        '72': 5,
        '73': 4,
        '74': 3,
        '75': 2,
        '76': 1
    }

    ladder_number = int(ladder_number)

    # business logic
    if ladder_number == 96:
        ladder_number = 9
    if ladder_number == 81:
        ladder_number = 18
    if ladder_number == 0:
        ladder_number = 2

    # not re-mapping
    # if is_ladder_number_valid(ladder_number):
    #     if ladder_number > 38:
    #         ladder_number = ladder_remap[str(ladder_number)]
    # else:
    if not is_ladder_number_valid(ladder_number):
        success = 0
        failure = 1
        is_new_ladder_created = 0
        error = {
            "row": row_num,
            "ladder_number": ladder_number,
            "side_id": current_side_id,
            "reason": "ladder_number invalid"
        }
        session.expire_all()
        return [success, failure, error, is_new_ladder_created, processed_ladder_id]

    # lookup ladder_number_id
    ladder_number_id = (
        session.query(LadderNumber.id)
        .filter(LadderNumber.number == ladder_number).scalar()
    )
    if ladder_number_id and current_side_id:
        # valid location to attempt ladder creation
        success = 1
        failure = 0
        # create or skip if exists
        processed_ladder = session.execute((
            insert(Ladder)
            .values(ladder_number_id = ladder_number_id, side_id = current_side_id)
            .on_conflict_do_nothing(index_elements=["ladder_number_id", "side_id"])
            .returning(Ladder.id)
        )).fetchone()

        session.commit()

        # fetch side if record not created
        if not processed_ladder:
            is_new_ladder_created = 0 # new ladder not created
            processed_ladder = session.execute(
                select(Ladder.id).where(
                    (Ladder.ladder_number_id == ladder_number_id) &
                    (Ladder.side_id == current_side_id)
                )
            ).fetchone()
        else:
            is_new_ladder_created = 1 # new ladder created

        processed_ladder_id = processed_ladder[0]

    else:
        # error, ladder number not found
        success = 0
        failure = 1
        is_new_ladder_created = 0
        error = {
            "row": row_num,
            "ladder_number": ladder_number,
            "side_id": current_side_id,
            "reason": "Invalid ladder_number or missing side association"
        }
        # Clear session when commit() doesn't
        session.expire_all()

    return [success, failure, error, is_new_ladder_created, processed_ladder_id]
