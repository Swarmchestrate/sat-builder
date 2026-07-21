#!/usr/bin/env bash
set -e

IMAGE_NAME="sat-builder"
CONTAINER_NAME="sat-builder"
HOST_PORT="8000"
CONTAINER_PORT="8000"
PLATFORM="linux/amd64"

echo "Building Docker image: ${IMAGE_NAME}"
docker build \
  --platform "${PLATFORM}" \
  --no-cache \
  -t "${IMAGE_NAME}" \
  .

echo "Stopping existing container if it exists..."
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo "Running container: ${CONTAINER_NAME}"
docker run \
  --platform "${PLATFORM}" \
  -d \
  --name "${CONTAINER_NAME}" \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  "${IMAGE_NAME}"

echo "Container started at http://localhost:${HOST_PORT}"
echo "View logs with: docker logs -f ${CONTAINER_NAME}"