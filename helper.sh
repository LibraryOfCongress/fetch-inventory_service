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
