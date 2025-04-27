import csv, os

from app.database.session import get_sqlalchemy_session
from sqlalchemy import select, delete, outerjoin, and_
from app.logger import migration_logger

from app.models.barcodes import Barcode
from app.models.shelves import Shelf
from app.models.trays import Tray
from app.models.items import Item
from app.models.non_tray_items import NonTrayItem

current_dir = os.path.dirname(os.path.abspath(__file__))


def load_barcode_cleanup():
    """Redact unused barcodes"""
    session = next(get_sqlalchemy_session())

    joined = (
        outerjoin(Barcode, Shelf, Shelf.barcode_id == Barcode.id)
    )
    joined = (
        outerjoin(joined, Tray, Tray.barcode_id == Barcode.id)
    )
    joined = (
        outerjoin(joined, Item, Item.barcode_id == Barcode.id)
    )
    joined = (
        outerjoin(joined, NonTrayItem, NonTrayItem.barcode_id == Barcode.id)
    )

    stmt = (
        select(Barcode.id, Barcode.value)
        .select_from(joined)
        .where(
            Shelf.barcode_id == None,
            Tray.barcode_id == None,
            Item.barcode_id == None,
            NonTrayItem.barcode_id == None,
        )
    )

    unused_barcodes = session.execute(stmt).all()

    barcode_values = [row.value for row in unused_barcodes]
    migration_logger.info(f"{len(barcode_values)} unused barcodes found.")

    error_directory = "errors"
    output_file = "unused_barcodes_removed.csv"

    # Ensure the directory exists
    os.makedirs(
        os.path.join(current_dir, error_directory),
        exist_ok=True
    )

    output_file = os.path.join(
        current_dir,
        error_directory,
        output_file
    )

    # Delete the unused barcodes
    barcode_ids = [row.id for row in unused_barcodes]
    delete_stmt = delete(Barcode).where(Barcode.id.in_(barcode_ids))

    # Execute the delete statement
    session.execute(delete_stmt)
    session.commit()

    migration_logger.info(f"Deleted {len(barcode_ids)} unused barcodes.")

    if len(barcode_values) > 0:
        migration_logger.info(f"Logging in unused_barcodes_removed.csv")
        with open(output_file, mode="w", newline="") as error_file:
            writer = csv.writer(error_file)
            writer.writerow(['barcode_value'])  # header
            for _, barcode_value in unused_barcodes:
                writer.writerow([barcode_value])

    return
