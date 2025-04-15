import re

from datetime import datetime, timezone

from app.models.items import Item
from app.models.barcodes import Barcode


def load_item(
    row_num,
    create_dt,
    owner_name,
    item_barcode_value,
    container_barcode_value,
    item_accession_dt,
    status,
    session,
    owners_dict,
    barcode_types_dict,
    container_types_dict,
    container_dict
):
    """
    Creates an Item given a legacy LAS Item,
    or updates a NonTrayItem barcode given a NonTrayItem

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

        # lookup container
        current_container = container_dict.get(container_barcode_value) #list[dict]

        # deal with weird characters
        if re.search(r'[^a-zA-Z0-9]', item_barcode_value):
            raise ValueError("Non alphanumeric characters in barcode")

        # create item barcode object
        item_barcode_instance = Barcode(
            value=item_barcode_value,
            type_id=barcode_types_dict.get("Item")
        )
        session.add(item_barcode_instance)
        session.commit()

        # sanitize unknown dates
        """
        in pattern "%m/%d/%y"
            For two-digit years 00-68, Python assumes they are in the 21st century (2000-2068).
            For two-digit years 69-99, Python assumes they are in the 20th century (1969-1999).

        If your system has something from 1968 or earlier, modify ingested dates to always be 4 digit
        and use pattern "%m/%d/%Y" instead
        """
        if item_accession_dt in ['?', '', None]:
            item_accession_dt = None
        else:
            item_accession_dt=datetime.strptime(item_accession_dt, "%m/%d/%y").replace(tzinfo=timezone.utc)
        if create_dt in ['?', '', None]:
            create_dt = datetime.now(datetime.timezone.utc)
        else:
            create_dt=datetime.strptime(create_dt, "%m/%d/%y").replace(tzinfo=timezone.utc)

        item_instance = Item(
            owner_id=owners_dict.get(owner_name),
            size_class_id=current_container[0].get('size_class_id'),
            barcode_id=item_barcode_instance.id,
            status=status,
            container_type_id=container_types_dict.get("Tray"),
            tray_id=current_container[0].get('id'),
            media_type_id=current_container[0].get('media_type_id'),
            accession_dt=item_accession_dt,
            title=None,
            volume=None,
            condition=None,
            arbitrary_data=None,
            subcollection_id=None,
            scanned_for_accession=True,
            scanned_for_verification=True,
            create_dt=create_dt
        )

        session.add(item_instance)

        session.commit()

        success = 1
        failure = 0

    except Exception as e:
        session.rollback()
        success = 0
        failure = 1
        error = {
            "row": row_num,
            "item_barcode": f":: {item_barcode_value}",
            "reason": f"{e}"
        }
    finally:
        return [success, failure, error]
