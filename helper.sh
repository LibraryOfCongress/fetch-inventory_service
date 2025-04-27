#!/bin/bash

build() {
  # this is old, use fetch-local and podman compose
  if [[ "$1" == "local" ]]; then
    (cd ../fetch-local \
      && exec ./helper.sh build-inventory-api);
  fi
  if [[ "$1" == "develop" ]]; then
    # this is old, revisit later
    ./dev-build.sh;
  fi
  if [[ "$1" == "test" ]]; then
    # this is old, revisit later
    ./test-build.sh;
  fi
}

build-db() {
  (cd ../fetch-local && exec ./helper.sh build-inventory-db);
}

refresh-db() {
  # Wipe db and build
  (cd ../fetch-local && exec ./helper.sh wipe-inventory-db);
  # Give the db a moment to catch its breath
  sleep 5;
  # Then rebuild from podman compose for schema
  (cd ../fetch-local \
    && exec ./helper.sh build-inventory-api);
}

seed-fake-data() {
# this gets called from fetch-local
# don't call this directly
# do not indent on shell str
SEED_FAKE_DATA="
from app import main
from app.seed.seed_fake_data import seed_fake_data
seed_fake_data()
";

  podman exec -it fetch-inventory-api python -c "$SEED_FAKE_DATA";
}

run-storage-migration() {
# do not indent on shell str
RUN_DATA_MIGRATION="
from app import main
from app.seed.seed_data import seed_data
seed_data()
";

  podman exec -it fetch-inventory-api python -c "$RUN_DATA_MIGRATION";
}

run-tray-migration() {
# do not indent on shell str
RUN_TRAY_MIGRATION="
from app import main
from app.seed.seed_data import seed_containers
seed_containers()
";

    podman exec -it fetch-inventory-api python -c "$RUN_TRAY_MIGRATION";
}

run-item-migration() {
# do not indent on shell str
RUN_ITEM_MIGRATION="
from app import main
from app.seed.seed_data import seed_items
seed_items()
";

    podman exec -it fetch-inventory-api python -c "$RUN_ITEM_MIGRATION";
}

run-available-space-migration() {
# do not indent on shell str
RUN_SPACE_MIGRATION="
from app import main
from app.seed.seed_data import seed_initial_available_space_calc
seed_initial_available_space_calc()
";

    podman exec -it fetch-inventory-api python -c "$RUN_SPACE_MIGRATION";
}

run-addressing-migration() {
# do not indent on shell str
RUN_ADDRESS_MIGRATION="
from app import main
from app.seed.seed_data import seed_location_address_values
seed_location_address_values()
";

    podman exec -it fetch-inventory-api python -c "$RUN_ADDRESS_MIGRATION"; 
}

run-barcode-cleanup() {
RUN_BARCODE_CLEANUP="
from app import main
from app.seed.seed_data import seed_unused_barcode_cleanup
seed_unused_barcode_cleanup()
";

    podman exec -it fetch-inventory-api python -c "$RUN_BARCODE_CLEANUP";
}

extract-data-migration() {
  # This can take like 20 minutes
  # dump in postgres native sql format
  # you may have to jump into the container shell and do this manually
    (podman exec -i inventory-database pg_dump -U postgres -d inventory_service -Fc > /tmp/fetch_dump_$(date +%m-%d-%Y).dump);
  # compress to xz
    (podman exec -i inventory-database xz /tmp/fetch_dump_$(date +%m-%d-%Y).dump);
  # podman doesn't create host directory, so you have to do this
    (mkdir -p ~/Desktop/fetch_migration);
  # copy the compressed dump to host
    (podman cp inventory-database:/tmp/fetch_dump_$(date +%m-%d-%Y).dump.xz ~/Desktop/fetch_migration/fetch_dump_$(date +%m-%d-%Y).dump.xz);
}

extract-migration-errors() {
  # podman doesn't create host directory, so you have to do this
  (mkdir -p ~/Desktop/fetch_migration);
  # If there are none, this will have an error
  (podman cp fetch-inventory-api:/code/app/seed/errors ~/Desktop/fetch_migration);
}

makemigrations() {
  USE_MIGRATION_URL=true alembic revision --autogenerate -m $1
}

migrate() {
  USE_MIGRATION_URL=true alembic upgrade head
}

current() {
  USE_MIGRATION_URL=true alembic current
}

downgrade-1() {
    USE_MIGRATION_URL=true alembic downgrade -1
}

api() {
  # gets you inside the inventory_service api shell
  podman exec -it fetch-inventory-api /bin/bash;
}

database() {
  # gets you inside the db container shell
  podman exec -it inventory-database /bin/bash;
}

psql() {
  # gets you into the pg engine psql on the container
  podman exec -it -u postgres inventory-database psql -a inventory_service
}

drop-db() {
    podman exec -it -u postgres inventory-database psql -d postgres -c "DROP DATABASE IF EXISTS inventory_service WITH (FORCE);" -c "CREATE DATABASE inventory_service;"
}

unzip-dump() {
  # decompresses without destruction. Not necessary. pg_restore can read compressed.
  xz -dk ~/Desktop/fetch_migration/$1
}

pg-restore() {
  # restores database on database container from compressed dump
  (podman cp ~/Desktop/fetch_migration/$1 inventory-database:/tmp/$1);

  (podman exec -it -u postgres inventory-database sh -c "xz -dc /tmp/$1 | pg_restore -U postgres -d inventory_service");
}

inspect-table() {
  tablename=$1
  podman exec -ti -u postgres inventory-database psql -a inventory_service -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '${tablename}';"
}

inspect-records() {
    tablename=$1
    podman exec -ti -u postgres inventory-database psql -a inventory_service -c "SELECT * FROM $1;"
}

idle() {
#   poetry shell;
#   python;
    podman exec -it fetch-inventory-api python;
}

test() {
  pytest
}

encrypt() {
  value=$1
  echo -n $value | base64
}

decrypt() {
  value=$1
  echo `echo $value | base64 --decode`
}

"$@"
