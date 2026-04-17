#!/usr/bin/env bash

version=$(<version.txt)

base_platform="linux/amd64,linux/arm64,linux/arm/v7"
plus_platform="linux/amd64,linux/arm64"

base_platform="linux/amd64"
plus_platform="linux/amd64"

# Base image
docker buildx build --target linkding --platform ${base_platform} \
  -f docker/default.Dockerfile \
  -t zhijunio/linkding:latest \
  -t zhijunio/linkding:$version \
  --push .

docker buildx build --target linkding --platform ${base_platform} \
  -f docker/alpine.Dockerfile \
  -t zhijunio/linkding:latest-alpine \
  -t zhijunio/linkding:$version-alpine \
  --push .

# Plus image with support for single-file snapshots
# Needs checking if this works with ARMv7, excluded for now
docker buildx build --target linkding-plus --platform ${plus_platform} \
  -f docker/default.Dockerfile \
  -t zhijunio/linkding:latest-plus \
  -t zhijunio/linkding:$version-plus \
  --push .

docker buildx build --target linkding-plus --platform ${plus_platform} \
  -f docker/alpine.Dockerfile \
  -t zhijunio/linkding:latest-plus-alpine \
  -t zhijunio/linkding:$version-plus-alpine \
  --push .
