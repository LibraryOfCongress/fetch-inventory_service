from datetime import datetime

from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode


def load_non_tray(
    row_num,
    container_barcode,
    media_type,
    shelf_barcode_value,
    owner_name,
    accession_dt,
    shelved_dt,
    size_class_short_name,
    shelf_position_number,
    session,
    container_types_dict,
    shelf_position_dict,
    size_class_dict,
    owners_dict,
    media_types_dict,
    barcode_types_dict
):
    """
    Creates a NonTrayItem given a legacy LAS non-tray

    returns
        [int, int, dict/None]
    """
    success = None
    failure = None
    error = None

    try:
        # ensure leading zeroes on shelf_barcode_value
        if len(shelf_barcode_value) < 6:
            missing_zeros = 6 - len(shelf_barcode_value)
            for _ in range(missing_zeros):
                shelf_barcode_value = f"0{shelf_barcode_value}"

        # create container barcode object
        # NonTray uses Item barcode rules of "^\\d{10}[0-9A]$"
        # For now, move the T to the end, and prefix 0's
        legacy_container_barcode = container_barcode #save this for error reporting
        container_barcode = container_barcode[1:]
        if len(container_barcode) < 10:
            missing_zeros = 10 - len(container_barcode)
            for _ in range(missing_zeros):
                container_barcode = f"0{container_barcode}"
        container_barcode = f"{container_barcode}T"
        non_tray_barcode_instance = Barcode(
            value=container_barcode,
            type_id=barcode_types_dict.get("Item")
        )
        session.add(non_tray_barcode_instance)
        session.commit()

        # determine media_type
        if media_type.upper() == 'A':
            media_type = 'Book/Volume'
        if media_type.upper() == 'M':
            media_type = 'Microfilm'

        # determine shelf position assignment
        positions_for_shelf = shelf_position_dict.get(shelf_barcode_value, [])
        sp_id = next(
            (position[shelf_position_number] for position in positions_for_shelf if shelf_position_number in position),
            None
        )

        # sanitize unknown dates
        if shelved_dt == '?':
            shelved_dt = None
        else:
            shelved_dt=datetime.strptime(shelved_dt, "%m/%d/%y")
        if accession_dt == '?':
            accession_dt = None
        else:
            accession_dt=datetime.strptime(accession_dt, "%m/%d/%y")

        # create the non-tray
        non_tray_instance = NonTrayItem(
            barcode_id=non_tray_barcode_instance.id,
            container_type_id=container_types_dict.get("Non-Tray"),
            owner_id=owners_dict.get(owner_name),
            size_class_id=size_class_dict.get(size_class_short_name),
            media_type_id=media_types_dict.get(media_type),
            shelf_position_id=sp_id,
            shelf_position_proposed_id=sp_id,
            shelved_dt=shelved_dt,
            accession_dt=accession_dt,
            scanned_for_accession=True,
            scanned_for_verification=True,
            scanned_for_shelving=True,
            status="In"
        )

        session.add(non_tray_instance)

        session.commit()

        success = 1
        failure = 0
    except Exception as e:
        session.rollback()
        success = 0
        failure = 1
        error = {
            "row": row_num,
            "non_tray_item_barcode": legacy_container_barcode,
            "reason": f"{e}"
        }
    finally:
        return [success, failure, error]
