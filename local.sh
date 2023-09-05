#!/usr/bin/env bash

set -x

IMAGE_LOCATION=images/api.local.Containerfile
IMAGE_TAG=fetch-api-image
POD_NAME=api
POD_PORT=8002

# podman machine status
podman machine ls --format json

# tear down pod if exists
podman pod exists ${POD_NAME}
if [ "$?" == "0" ]; then
  podman kube down local.yml;
fi

# Test if port is clear
is_port_blocked="$(lsof -i -P -n | grep ${POD_PORT})"
if [[ "${#is_port_blocked}" -gt 0 ]]; then
    echo "Port ${POD_PORT} already in use"
    echo "${is_port_blocked}"
    echo "Kill process id and try again"
    echo "You may need to restart the Podman machine"
    exit 1
fi

# build images
podman build \
--file ${IMAGE_LOCATION} --tag ${IMAGE_TAG} .

# Run pod from kube configuration
podman play kube local.yml
