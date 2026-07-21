#!/usr/bin/env bash

set -euo pipefail

# Docker Hub namespace or username.
# Defaults to the UOW CPC Docker Hub organisation.
#
# Override example:
#   DOCKER_NAMESPACE=my-user ./publish_docker.sh 1.0.0
DOCKER_NAMESPACE="${DOCKER_NAMESPACE:-uowcpc}"

# Full Docker image name.
IMAGE_NAME="${DOCKER_NAMESPACE}/sat-builder"

# Image version/tag to publish.
# Usage:
#   ./publish_docker.sh 1.0.0
VERSION="${1:-}"

if [[ -z "${VERSION}" ]]; then
  echo "Usage: ./publish_docker.sh <version>"
  echo "Example: ./publish_docker.sh 1.0.0"
  echo ""
  echo "Optional:"
  echo "  DOCKER_NAMESPACE defaults to: uowcpc"
  echo ""
  echo "Examples:"
  echo "  ./publish_docker.sh 1.0.0"
  echo "  DOCKER_NAMESPACE=my-user ./publish_docker.sh 1.0.0"
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