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
  (cd ../fetch-fetch-local && exec ./helper.sh build-inventory-db);
}

refresh-db() {
  # Wipe db and build
  (cd ../fetch-fetch-local && exec ./helper.sh wipe-inventory-db);
  # Give the db a moment to catch its breath
  sleep 5;
  # Then rebuild from podman compose for schema
  (cd ../fetch-fetch-local \
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

  docker exec -it fetch-inventory-api python -c "$SEED_FAKE_DATA";
}

bootstrap-production() {
    EMAIL=$1
    FIRST_NAME=${2:-"System"}
    LAST_NAME=${3:-"Admin"}
    if [ -z "$EMAIL" ]; then
        echo "Usage: ./helper.sh bootstrap-production <email> [first_name] [last_name]"
        echo "Example: ./helper.sh bootstrap-production admin@example.com"
        exit 1
    fi
    podman exec -it fetch-inventory-api python -c "from app.seed.bootstrap_production import bootstrap_admin; bootstrap_admin('$EMAIL', '$FIRST_NAME', '$LAST_NAME')"
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

# ----------------------------------------------------------------------
# refresh-deployed-db
#   Wipes and reseeds the inventory_service DB in a deployed k8s env.
#   Steps:
#     1. DROP + CREATE the database (via a running inventory-service pod).
#     2. Rollout-restart the deployment so startup runs alembic upgrade head.
#     3. Invoke seed_fake_data() inside the new pod.
#
#   Usage:
#     ./helper.sh refresh-deployed-db                          # defaults: fetch / inventory-service
#     ./helper.sh refresh-deployed-db <namespace> <deployment>
#
#   NOT FOR PRODUCTION. Drops the database; loads fake users (FBaggins-style)
#   and 2432 synthetic shelves. Intended for the deployed dev environment.
# ----------------------------------------------------------------------
refresh-deployed-db() {
    NAMESPACE=${1:-fetch}
    DEPLOYMENT=${2:-inventory-service}
    CONTEXT=$(kubectl config current-context 2>/dev/null)

    if [ -z "$CONTEXT" ]; then
        echo "kubectl not configured (no current-context)."
        return 1
    fi

    echo "About to WIPE and reseed the inventory_service database:"
    echo "  kubectl context: $CONTEXT"
    echo "  namespace:       $NAMESPACE"
    echo "  deployment:      $DEPLOYMENT"
    echo ""
    echo "This will:"
    echo "  1. DROP DATABASE inventory_service WITH (FORCE)"
    echo "  2. CREATE DATABASE inventory_service"
    echo "  3. rollout restart $DEPLOYMENT (triggers alembic upgrade head)"
    echo "  4. run seed_fake_data() (synthetic users, 2432 shelves)"
    echo ""
    printf "Type 'yes' to proceed: "
    read CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        return 1
    fi

    echo ">> [1/3] Dropping and recreating database..."
    kubectl -n "$NAMESPACE" exec "deploy/$DEPLOYMENT" -- sh -c \
        'cd /code && python -m app.seed.wipe_db' || {
            echo "Drop/create failed."; return 1;
        }

    echo ">> [2/3] Rolling deployment to run migrations on empty DB..."
    kubectl -n "$NAMESPACE" rollout restart "deploy/$DEPLOYMENT" || return 1
    kubectl -n "$NAMESPACE" rollout status  "deploy/$DEPLOYMENT" --timeout=300s || {
            echo "Rollout did not complete in time."; return 1;
        }

    echo ">> [3/3] Seeding fake data (this can take several minutes)..."
    kubectl -n "$NAMESPACE" exec "deploy/$DEPLOYMENT" -- sh -c \
        'cd /code && python -m app.seed.run_seed_fake' || {
            echo "Seeding failed. DB has schema but no data."; return 1;
        }

    echo ">> Done."
}

# ----------------------------------------------------------------------
# wipe-and-seed
#   Same flow as refresh-deployed-db, but runs ENTIRELY INSIDE the
#   inventory-service container. Use this when you've already done
#   `kubectl exec -it deploy/inventory-service -- bash` and want a
#   one-shot wipe/migrate/seed without bouncing back out to kubectl.
#
#   Steps:
#     1. DROP + CREATE the database (via app.seed.wipe_db).
#     2. alembic upgrade head (runs in-process, no pod restart needed).
#     3. seed_fake_data().
#
#   The uvicorn process in this same pod stays up; once alembic finishes
#   its connection pool reconnects (pool_pre_ping handles the stale conns).
#
#   Usage (inside the container):
#     cd /code && ./helper.sh wipe-and-seed
#
#   NOT FOR PRODUCTION. Drops the database; loads synthetic users and
#   2432 fake shelves. Intended for the deployed dev environment.
# ----------------------------------------------------------------------
wipe-and-seed() {
    if [ ! -f /code/alembic.ini ]; then
        echo "Doesn't look like we're inside the inventory-service container."
        echo "Expected /code/alembic.ini to exist."
        echo "If you're on your local machine, use refresh-deployed-db instead."
        return 1
    fi

    echo "About to WIPE and reseed the database this container connects to."
    echo "This will:"
    echo "  1. DROP DATABASE ... WITH (FORCE)"
    echo "  2. CREATE DATABASE ..."
    echo "  3. alembic upgrade head"
    echo "  4. seed_fake_data() (synthetic users, 2432 shelves)"
    echo ""
    printf "Type 'yes' to proceed: "
    read CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        return 1
    fi

    cd /code || return 1

    echo ">> [1/3] Dropping and recreating database..."
    python -m app.seed.wipe_db || {
        echo "Drop/create failed."; return 1;
    }

    echo ">> [2/3] Running alembic upgrade head on empty DB..."
    alembic upgrade head || {
        echo "Migrations failed. DB is empty -- re-run wipe-and-seed."; return 1;
    }

    echo ">> [3/3] Seeding fake data (this can take several minutes)..."
    python -m app.seed.run_seed_fake || {
        echo "Seeding failed. DB has schema but no data."; return 1;
    }

    echo ">> Done."
}

"$@"
