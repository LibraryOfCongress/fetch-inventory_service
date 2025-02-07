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

extract-data-migration() {
  (podman cp fetch-inventory-api:/code/app/seed/errors ~/Desktop/fetch_migration);
  (podman exec -i inventory-database pg_dump -U postgres -d inventory_service | gzip > ~/Desktop/fetch_migration/fetch_dump_`date +%m-%d-%Y`.sql.gz);
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

api() {
  podman exec -it fetch-inventory-api /bin/bash;
}

psql() {
  podman exec -it -u postgres inventory-database psql -a inventory_service
}

unzip-dump() {
    gzip -d ~/Desktop/fetch_migration/$1
}

pg-restore() {
    podman cp ~/Desktop/fetch_migration/$1 inventory-database:/tmp/$1;
    podman exec -it -u postgres inventory-database psql -d inventory_service -f /tmp/$1
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
