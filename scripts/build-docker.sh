#!/usr/bin/env bash

# Enable BuildKit for better caching
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain
export SOURCE_DATE_EPOCH="1704067200"

# Docker mirror for users in China (optional)
# Usage: DOCKER_MIRROR=1 ./scripts/build-docker.sh
if [ "${DOCKER_MIRROR:-}" = "1" ]; then
  # Use dockerhub.icu as mirror proxy
  # Configure in /etc/docker/daemon.json:
  #   {"registry-mirrors": ["https://dockerhub.icu"]}
  echo "Note: Set DOCKER_MIRROR=1 and configure /etc/docker/daemon.json with registry-mirrors"
fi

version=$(<version.txt)

# Local build uses linux/amd64 only. For multi-arch builds, use GitHub Actions.
PLATFORM="${PLATFORM:-linux/amd64}"

# Set registry (default: Docker Hub)
REGISTRY="${REGISTRY:-docker.io}"
USERNAME="${DOCKER_USERNAME:-}"
PASSWORD="${DOCKER_PASSWORD:-}"

# Login to registry if credentials are provided
if [ -n "$USERNAME" ] && [ -n "$PASSWORD" ]; then
  echo "Logging in to $REGISTRY..."
  echo "$PASSWORD" | docker login "$REGISTRY" -u "$USERNAME" --password-stdin
fi

echo "Building Debian images..."
docker buildx build --platform $PLATFORM \
  -f docker/default.Dockerfile \
  -t zhijunio/linkding:latest \
  -t zhijunio/linkding:${version} \
  --target linkding \
  --cache-from type=local,src=/tmp/.buildx-cache-debian \
  --cache-to type=local,dest=/tmp/.buildx-cache-debian,mode=max \
  --push \
  .

docker buildx build --platform $PLATFORM \
  -f docker/default.Dockerfile \
  -t zhijunio/linkding:latest-plus \
  -t zhijunio/linkding:${version}-plus \
  --target linkding-plus \
  --cache-from type=local,src=/tmp/.buildx-cache-debian \
  --cache-to type=local,dest=/tmp/.buildx-cache-debian,mode=max \
  --push \
  .

echo "Building Alpine images..."
docker buildx build --platform $PLATFORM \
  -f docker/alpine.Dockerfile \
  -t zhijunio/linkding:latest-alpine \
  -t zhijunio/linkding:${version}-alpine \
  --target linkding \
  --cache-from type=local,src=/tmp/.buildx-cache-alpine \
  --cache-to type=local,dest=/tmp/.buildx-cache-alpine,mode=max \
  --push \
  .

docker buildx build --platform $PLATFORM \
  -f docker/alpine.Dockerfile \
  -t zhijunio/linkding:latest-plus-alpine \
  -t zhijunio/linkding:${version}-plus-alpine \
  --target linkding-plus \
  --cache-from type=local,src=/tmp/.buildx-cache-alpine \
  --cache-to type=local,dest=/tmp/.buildx-cache-alpine,mode=max \
  --push \
  .

echo ""
echo "Build completed!"
echo ""
echo "Note: BuildKit local cache is stored in /tmp/.buildx-cache-*"
echo "      Set PLATFORM=linux/amd64,linux/arm64 for multi-arch builds."
echo ""
echo "China users: Configure Docker mirror in /etc/docker/daemon.json:"
echo '  {"registry-mirrors": ["https://dockerhub.icu"]}'
echo "Then restart Docker: sudo systemctl restart docker"
