#!/bin/bash

build() {
  if [[ "$1" == "local" ]]; then
    ./local-build.sh;
  fi
  if [[ "$1" == "dev" ]]; then
    ./dev-build.sh;
  fi
  if [[ "$1" == "test" ]]; then
    ./test-build.sh;
  fi
}

api() {
  docker exec -it fetch-inventory-api /bin/bash;
}

psql() {
  docker exec -it -u postgres fetch-postgres psql -a inventory_service
}

inspect-table() {
  tablename=$1
  docker exec -ti -u postgres fetch-postgres psql -a inventory_service -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '${tablename}';"
}

idle() {
  poetry shell;
  python;
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
