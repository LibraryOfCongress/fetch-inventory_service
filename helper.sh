#!/bin/bash

build() {
  if [[ "$1" == "local" ]]; then
    (cd ../fetch-local \
      && export SEED_FAKE_DATA=false \
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
  # Then re-schema and re-seed
  (cd ../fetch-local \
    && export SEED_FAKE_DATA=true \
    && exec ./helper.sh build-inventory-api \
    && export SEED_FAKE_DATA=false);
    # Reset seed arg in case user runs compose elsewhere
}

run-data-migration() {
# do not indent on shell str
RUN_DATA_MIGRATION="
from app import main
from app.seed.seed_data import seed_data
seed_data()
";

  docker exec -it fetch-inventory-api python -c "$RUN_DATA_MIGRATION";
}

extract-data-migration() {
  (docker cp fetch-inventory-api:/code/app/seed/errors ~/Desktop/fetch_migration);
  (docker exec -i inventory-database pg_dump -U postgres -d inventory_service | gzip > ~/Desktop/fetch_migration/fetch_dump.sql.gz);
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
  docker exec -it fetch-inventory-api /bin/bash;
}

psql() {
  docker exec -it -u postgres inventory-database psql -a inventory_service
}

inspect-table() {
  tablename=$1
  docker exec -ti -u postgres inventory-database psql -a inventory_service -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '${tablename}';"
}

inspect-records() {
    tablename=$1
    docker exec -ti -u postgres inventory-database psql -a inventory_service -c "SELECT * FROM $1;"
}

idle() {
#   poetry shell;
#   python;
    docker exec -it fetch-inventory-api python;
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
