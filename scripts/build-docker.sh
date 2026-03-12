#!/usr/bin/env bash

version=$(<version.txt)

base_platform="linux/amd64,linux/arm64,linux/arm/v7"
plus_platform="linux/amd64,linux/arm64"

base_platform="linux/amd64"
plus_platform="linux/amd64"

# Base image
docker buildx build --target linkding --platform ${base_platform} \
  -f docker/default.Dockerfile \
  -t chensoul/linkding:latest \
  -t chensoul/linkding:$version \
  --push .

docker buildx build --target linkding --platform ${base_platform} \
  -f docker/alpine.Dockerfile \
  -t chensoul/linkding:latest-alpine \
  -t chensoul/linkding:$version-alpine \
  --push .

# Plus image with support for single-file snapshots
# Needs checking if this works with ARMv7, excluded for now
docker buildx build --target linkding-plus --platform ${plus_platform} \
  -f docker/default.Dockerfile \
  -t chensoul/linkding:latest-plus \
  -t chensoul/linkding:$version-plus \
  --push .

docker buildx build --target linkding-plus --platform ${plus_platform} \
  -f docker/alpine.Dockerfile \
  -t chensoul/linkding:latest-plus-alpine \
  -t chensoul/linkding:$version-plus-alpine \
  --push .
