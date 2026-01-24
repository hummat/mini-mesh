#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-}"

if [[ -z "$VERSION" || "$VERSION" == "-h" || "$VERSION" == "--help" ]]; then
  cat <<'EOF'
Usage: docker/publish.sh VERSION

Tags and pushes mini-mesh Docker images to Docker Hub and GHCR.

Arguments:
  VERSION    Version tag (e.g., 0.3.1)

Prerequisites:
  - Images must be built first: docker/build.sh full && docker/build.sh slim
  - Login to registries: docker login && docker login ghcr.io -u <username>

Example:
  docker/publish.sh 0.3.1
EOF
  exit 0
fi

DOCKERHUB="hummat/mini-mesh"
GHCR="ghcr.io/hummat/mini-mesh"

echo "Publishing mini-mesh images with version: $VERSION"

# Check images exist
for img in "${DOCKERHUB}:latest" "${DOCKERHUB}:slim"; do
  if ! docker image inspect "$img" &>/dev/null; then
    echo "Error: $img not found. Run docker/build.sh first." >&2
    exit 1
  fi
done

# Tag images
echo "Tagging images..."
docker tag "${DOCKERHUB}:latest" "${DOCKERHUB}:${VERSION}"
docker tag "${DOCKERHUB}:slim" "${DOCKERHUB}:${VERSION}-slim"
docker tag "${DOCKERHUB}:latest" "${GHCR}:latest"
docker tag "${DOCKERHUB}:latest" "${GHCR}:${VERSION}"
docker tag "${DOCKERHUB}:slim" "${GHCR}:slim"
docker tag "${DOCKERHUB}:slim" "${GHCR}:${VERSION}-slim"

# Push to Docker Hub
echo "Pushing to Docker Hub..."
docker push "${DOCKERHUB}:latest"
docker push "${DOCKERHUB}:${VERSION}"
docker push "${DOCKERHUB}:slim"
docker push "${DOCKERHUB}:${VERSION}-slim"

# Push to GHCR
echo "Pushing to GHCR..."
docker push "${GHCR}:latest"
docker push "${GHCR}:${VERSION}"
docker push "${GHCR}:slim"
docker push "${GHCR}:${VERSION}-slim"

echo "Done. Published:"
echo "  Docker Hub: ${DOCKERHUB}:latest, :${VERSION}, :slim, :${VERSION}-slim"
echo "  GHCR:       ${GHCR}:latest, :${VERSION}, :slim, :${VERSION}-slim"
