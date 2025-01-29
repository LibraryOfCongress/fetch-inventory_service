import re

from datetime import datetime

from app.models.non_tray_items import NonTrayItem
from app.models.barcodes import Barcode


def load_non_tray(
    row_num,#satisfied
    create_dt,
    item_barcode_value,#satisfied
    # media_type,#foreign unsatisfied
    non_tray_missing_data_dict,
    container_barcode_value,#satisfied
    owner_name,#satisfied
    item_accession_dt,#satisfied
    # shelved_dt,#foreign unsatisfied
    size_class_short_name,#satisfied
    shelf_position_number,#satisfied
    session,#satisfied
    container_types_dict,#satisfied
    shelf_position_dict,#satisfied
    size_class_dict,#satisfied
    owners_dict,#satisfied
    media_types_dict,#satisfied
    barcode_types_dict#satisfied
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
        # fix owner_name casing
        if owner_name in ["lc", "Lc", "lC"]:
            owner_name = "LC"

        # shelf_barcode from container_barcode_value stripped (everything after 'T')
        shelf_barcode_value = container_barcode_value[-6:]

        # create non_tray barcode object
        # NonTray uses Item barcode rules of "^\\d{10}[0-9A]$"
        # deal with weird characters
        if re.search(r'[^a-zA-Z0-9]', item_barcode_value):
            raise ValueError("Non alphanumeric characters in barcode")
        non_tray_barcode_instance = Barcode(
            value=item_barcode_value,
            type_id=barcode_types_dict.get("Item")
        )
        session.add(non_tray_barcode_instance)
        session.commit()

        # grab missing data for item.txt (satisfied from tray.txt)
        non_tray_missing_data = non_tray_missing_data_dict.get(shelf_barcode_value) #returns a list of dictionaries
        if not non_tray_missing_data:
            raise ValueError(f"Missing shelved_dt and/or media_type data for non_trays on shelf {shelf_barcode_value}")

        # If more than one, an incongruent matchup was gathered because of invalid LAS entry
        # reference shelves 000000 and 200000 to understand this
        # In this case, we treat the T+shelf_barcode version from tray.txt row[0] as source of truth
        # else we use the one and only collection returned from shelf barcode in row[4]
        if len(non_tray_missing_data) > 1:
            # for data_dict in non_tray_missing_data:
            #     if data_dict['nt_computed_barcode'][-6:] == shelf_barcode_value:
            #         selected_dict = data_dict
            #         break
            #     else:
            #         selected_dict = non_tray_missing_data[0]
            # non_tray_missing_data = selected_dict
            # error it for now
            raise ValueError(f"Multiple shelved_dt and/or media_types to choose. Unable to reconcile between in {non_tray_missing_data}")
        else:
            non_tray_missing_data = non_tray_missing_data[0]

        # determine media_type
        media_type = non_tray_missing_data.get('media_type')
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
        shelved_dt = non_tray_missing_data.get('shelved_dt')
        if shelved_dt == '?':
            shelved_dt = None
        else:
            shelved_dt=datetime.strptime(shelved_dt, "%m/%d/%y")
        if item_accession_dt == '?':
            item_accession_dt = None
        else:
            item_accession_dt=datetime.strptime(item_accession_dt, "%m/%d/%y")
        if create_dt == '?':
            create_dt = None
        else:
            create_dt=datetime.strptime(create_dt, "%m/%d/%y")

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
            accession_dt=item_accession_dt,
            scanned_for_accession=True,
            scanned_for_verification=True,
            scanned_for_shelving=True,
            status="In",
            create_dt=create_dt
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
            "non_tray_item_barcode": f":: {item_barcode_value}",
            "reason": f"{e}"
        }
    finally:
        return [success, failure, error]
