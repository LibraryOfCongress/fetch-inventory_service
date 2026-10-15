import os
import json
import logging

# Define the Docker command to run the Postgres container
ROOT_FILE_PATH = os.getcwd()

# Path to your fixtures file
CREATE_DATA_SAMPLER_FIXTURE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/create_data_sampler.json"
)
DATA_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/data_response.json"
UPDATE_DATA_SAMPLER_FIXTURE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/update_data_sampler.json"
)
EMPTY_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/empty_response.json"
PAGE_EMPTY_RESPONSE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/page_empty_response.json"
)
SIZE_EMPTY_RESPONSE = (
    f"{ROOT_FILE_PATH}/tests/fixtures/payloads/size_empty_response.json"
)
DATA_PAGE_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/data_page_response.json"
DATA_SIZE_RESPONSE = f"{ROOT_FILE_PATH}/tests/fixtures/payloads/data_size_response.json"

logger = logging.getLogger(__name__)

def get_data_from_file(file_path):
    if file_path:
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        return data
    else:
        raise ValueError("File path not provided")


BARCODE_COUNTER = 0


def generate_barcode_id(client, type_id, value):
    global BARCODE_COUNTER
    BARCODE_COUNTER += 1
    unique_value = f"{value}_{BARCODE_COUNTER}"
    results = client.post(
        "/barcodes", json={"type_id": type_id, "value": unique_value}
    )

    if results.status_code == 201:
        return results.json().get("id")
    return None


def populate_record(client, fixtures_path, table):
    """
    Fixture to populate a single building record for testing purposes.
    """
    data = get_data_from_file(fixtures_path)

    if table:
        logger.info(f"Populating table: {table}")
        logger.info(f"Request Data : {data.get(table)}")

        try:
            if table == "aisle_numbers":
                return client.post("/aisles/numbers", json=data.get(table))
            elif table == "side_orientations":
                return client.post("/sides/orientations", json=data.get(table))
            elif table == "barcode_types":
                return client.post("/barcodes/types", json=data.get(table))
            elif table == "ladder_numbers":
                return client.post("/ladders/numbers", json=data.get(table))
            elif table == "shelf_numbers":
                return client.post("/shelves/numbers", json=data.get(table))
            elif table == "shelf_positions":
                return client.post("/shelves/positions/", json=data.get(table))
            elif table == "shelf_position_numbers":
                return client.post(f"/shelves/positions/numbers", json=data.get(table))
            elif table == "container_types":
                return client.post("/container-types", json=data.get(table))
            elif table == "owner_tiers":
                return client.post("/owners/tiers", json=data.get(table))
            elif table == "accession_jobs":
                return client.post("/accession-jobs", json=data.get(table))
            elif table == "verification_jobs":
                return client.post("/verification-jobs", json=data.get(table))
            elif table == "media_types":
                return client.post("/media-types", json=data.get(table))
            elif table == "conveyance_bins":
                return client.post("/conveyance-bins", json=data.get(table))
            elif table == "size_class":
                return client.post("/size_class", json=data.get(table))
            elif table == "shelf_types":
                return client.post("/shelf-types", json=data.get(table))
            elif table == "request_types":
                return client.post("/requests/types", json=data.get(table))
            elif table == "refile_jobs":
                return client.post("/refile-jobs", json=data.get(table))
            elif table == "shelving_jobs":
                response = client.patch("/verification-jobs/1", json={"status":
                                                                         "Completed"})
                if response.status_code == 200:

                    response = client.post("/shelving-jobs", json=data.get(
                        table))

                return response
            elif table == "pick_lists":
                return client.post("/pick-lists", json=data.get(table))
            else:
                if table == "shelves":
                    barcode_id = generate_barcode_id(client, 1, "5901234123458")

                    if barcode_id is not None:
                        data[table]["barcode_id"] = barcode_id

                if table == "trays":
                    barcode_id = generate_barcode_id(client, 1, "5901234123459")

                    if barcode_id is not None:
                        data[table]["barcode_id"] = barcode_id

                    conveyance_bins_results = client.post(
                        "/conveyance-bins", json={"barcode_id": barcode_id}
                    )

                    if conveyance_bins_results.status_code == 201:
                        data[table][
                            "conveyance_bin_id"
                        ] = conveyance_bins_results.json().get("id")

                if table == "items":
                    barcode_id = generate_barcode_id(client, 1, "5901234123460")

                    if barcode_id is not None:
                        data[table]["barcode_id"] = barcode_id

                return client.post(f"/{table}", json=data.get(table))

        except Exception as e:
            raise e

    else:
        raise ValueError("Table name not provided")

# Dummy exports to satisfy broken imports in tests
# These should ideally be removed from the consuming files, but this
# prevents 50+ files from breaking immediately.
client = None
session = None
init_db = None
test_database = None
