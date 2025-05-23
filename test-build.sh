#!/usr/bin/env bash

set -x

IMAGE_LOCATION=images/api.test.Containerfile
IMAGE_TAG=fetch-inventory-api-image
CONTAINER_NAME=fetch-inventory-api
INTERNAL_PORT=8001
HOST_PORT=80

# stop the container if there is one running
CONTAINER_IDS=$(podman ps -q --filter name="^${CONTAINER_NAME}$")
if [ "$CONTAINER_IDS" != "" ]; then
    podman stop $CONTAINER_IDS
fi

# delete the container if there is one
CONTAINER_IDS=$(podman container ls -aq --filter name="^${CONTAINER_NAME}$")
if [ "$CONTAINER_IDS" != "" ]; then
    podman container rm -f $CONTAINER_IDS
fi

# delete the image if there is one
IMAGE_IDS=$(podman image ls -aq --filter "reference=${IMAGE_TAG}")
if [ "$IMAGE_IDS" != "" ]; then
    podman image rm -f $IMAGE_IDS
fi

# Test if port is clear
# is_port_blocked="$(lsof -i -P -n | grep ${HOST_PORT})"
# if [[ "${#is_port_blocked}" -gt 0 ]]; then
#     echo "Port ${HOST_PORT} already in use"
#     echo "${is_port_blocked}"
#     echo "Kill process id and try again"
#     echo "You may need to restart the podman machine"
#     exit 1
# fi

# build images
podman build \
--file ${IMAGE_LOCATION} --tag ${IMAGE_TAG} .

# run the fetch-inventory-api container
podman run --restart=always -it -d \
    -p${HOST_PORT}:${INTERNAL_PORT} \
    --name ${CONTAINER_NAME} \
    ${IMAGE_TAG}
