#!/bin/bash

build() {
  ./local.sh;
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
