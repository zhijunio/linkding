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
