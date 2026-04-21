#!/usr/bin/env bash

version=$(<version.txt)

# Local build uses linux/amd64 only. For multi-arch builds, use GitHub Actions.
PLATFORM="linux/amd64"

echo "Building Debian images..."
docker build --target linkding --platform $PLATFORM \
  -f docker/default.Dockerfile \
  -t zhijunio/linkding:latest \
  -t zhijunio/linkding:${version} \
  .

docker build --target linkding-plus --platform $PLATFORM \
  -f docker/default.Dockerfile \
  -t zhijunio/linkding:latest-plus \
  -t zhijunio/linkding:${version}-plus \
  .

echo "Building Alpine images..."
docker build --target linkding --platform $PLATFORM \
  -f docker/alpine.Dockerfile \
  -t zhijunio/linkding:latest-alpine \
  -t zhijunio/linkding:${version}-alpine \
  .

docker build --target linkding-plus --platform $PLATFORM \
  -f docker/alpine.Dockerfile \
  -t zhijunio/linkding:latest-plus-alpine \
  -t zhijunio/linkding:${version}-plus-alpine \
  .

echo ""
echo "Build completed! Images:"
docker images zhijunio/linkding --format "{{.Repository}}:{{.Tag}} - {{.Size}}" | grep -v test

echo ""
echo "Note: Local builds use Docker's default caching."
echo "For faster rebuilds when dependencies change, consider:"
echo "  1. Building base images: docker build -f docker/base-debian.Dockerfile --target build-deps -t zhijunio/linkding:base-debian ."
echo "  2. Using BuildKit mount caching (requires BUILDKIT_PROGRESS=plain)"
