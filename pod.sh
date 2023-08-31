#!/usr/bin/env bash

set -x

IMAGE_TAG=fetch-api-image
POD_NAME=api
SECRETS_POD=local-secrets

# tear down pod if exists
podman pod exists ${POD_NAME}
if [ "$?" == "0" ]; then
  podman kube down local.yml;
fi

# tear down secrets
podman pod exists ${SECRETS_POD}
if [ "$?" == "0" ]; then
  podman kube down local.yml;
fi

podman build \
--file images/api.local.Containerfile --tag ${IMAGE_TAG} .

podman kube play local-secrets.yml 

podman play kube local.yml
