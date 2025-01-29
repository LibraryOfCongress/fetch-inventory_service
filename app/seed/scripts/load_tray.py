import re

from datetime import datetime

from app.models.trays import Tray
from app.models.barcodes import Barcode


def load_tray(
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
    Creates a Tray given a legacy LAS tray

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

        # deal with weird characters
        if re.search(r'[^a-zA-Z0-9]', container_barcode):
            raise ValueError("Non alphanumeric characters in barcode")

        # create container barcode object
        tray_barcode_instance = Barcode(
            value=container_barcode,
            type_id=barcode_types_dict.get("Tray")
        )
        session.add(tray_barcode_instance)
        session.commit()

        # determine media_type
        if media_type.upper() == 'A':
            media_type = 'Book/Volume'
        if media_type.upper() == 'M':
            media_type = 'Microfilm'

        # determine shelf position assignment
        shelf_position_number = int(shelf_position_number)
        positions_for_shelf = shelf_position_dict.get(shelf_barcode_value, [])
        sp_id = next(
            (position[shelf_position_number] for position in positions_for_shelf if shelf_position_number in position),
            None
        )

        # sanitize unknown dates
        """
        in pattern "%m/%d/%y"
            For two-digit years 00-68, Python assumes they are in the 21st century (2000-2068).
            For two-digit years 69-99, Python assumes they are in the 20th century (1969-1999).

        If your system has something from 1968 or earlier, modify ingested dates to always be 4 digit
        and use pattern "%m/%d/%Y" instead
        """
        if shelved_dt == '?':
            shelved_dt = None
        else:
            shelved_dt=datetime.strptime(shelved_dt, "%m/%d/%y")
        if accession_dt == '?':
            accession_dt = None
        else:
            accession_dt=datetime.strptime(accession_dt, "%m/%d/%y")

        # fix owner_name casing
        if owner_name in ["lc", "Lc", "lC"]:
            owner_name = "LC"

        # create the tray
        tray_instance = Tray(
            barcode_id=tray_barcode_instance.id,
            container_type_id=container_types_dict.get("Tray"),
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
            collection_accessioned=True,
            collection_verified=True
        )

        session.add(tray_instance)

        session.commit()

        success = 1
        failure = 0

    except Exception as e:
        session.rollback()
        success = 0
        failure = 1
        error = {
            "row": row_num,
            "tray_barcode": container_barcode,
            "reason": f"{e}"
        }
    finally:
        return [success, failure, error]
