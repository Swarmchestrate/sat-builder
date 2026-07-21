#!/usr/bin/env bash

set -euo pipefail

IMAGE_NAME="uowcpc/sat-builder"
VERSION="${1:-}"

if [[ -z "${VERSION}" ]]; then
  echo "Usage: ./publish_docker.sh <version>"
  echo "Example: ./publish_docker.sh 1.0.0"
  exit 1
fi

echo "Building Docker image..."
docker build -t "${IMAGE_NAME}:${VERSION}" -t "${IMAGE_NAME}:latest" .

echo "Pushing Docker image version: ${VERSION}"
docker push "${IMAGE_NAME}:${VERSION}"

echo "Pushing Docker image tag: latest"
docker push "${IMAGE_NAME}:latest"

echo "Done."
echo "Published:"
echo "  ${IMAGE_NAME}:${VERSION}"
echo "  ${IMAGE_NAME}:latest"