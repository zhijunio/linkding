# Docker Images

Docker images for linkding with Debian and Alpine variants.

## Image Variants

| Variant | Dockerfile | Target | Platforms | Description |
|---------|-----------|--------|-----------|-------------|
| `latest` | `default.Dockerfile` | `linkding` | amd64, arm64 | Standard Debian-based image |
| `latest-alpine` | `alpine.Dockerfile` | `linkding` | amd64, arm64, arm/v7 | Alpine-based (smaller size) |
| `latest-plus` | `default.Dockerfile` | `linkding-plus` | amd64, arm64 | Debian + Chromium for snapshots |
| `latest-plus-alpine` | `alpine.Dockerfile` | `linkding-plus` | amd64, arm64, arm/v7 | Alpine + Chromium for snapshots |

## Build

```bash
# Build standard Debian image
docker buildx build --target linkding -f docker/default.Dockerfile -t zhijunio/linkding:latest --push .

# Build Alpine image
docker buildx build --target linkding -f docker/alpine.Dockerfile -t zhijunio/linkding:latest-alpine --push .

# Build Debian Plus image
docker buildx build --target linkding-plus -f docker/default.Dockerfile -t zhijunio/linkding:latest-plus --push .

# Build Alpine Plus image
docker buildx build --target linkding-plus -f docker/alpine.Dockerfile -t zhijunio/linkding:latest-plus-alpine --push .
```

## Run

```bash
# Standard Debian
docker run -d -p 9090:9090 -v ./data:/etc/linkding/data zhijunio/linkding:latest

# Standard Alpine
docker run -d -p 9090:9090 -v ./data:/etc/linkding/data zhijunio/linkding:latest-alpine

# Debian Plus (with snapshots)
docker run -d -p 9090:9090 -v ./data:/etc/linkding/data -e LD_ENABLE_SNAPSHOTS=True zhijunio/linkding:latest-plus

# Alpine Plus (with snapshots)
docker run -d -p 9090:9090 -v ./data:/etc/linkding/data -e LD_ENABLE_SNAPSHOTS=True zhijunio/linkding:latest-plus-alpine
```

## Platforms

- **Debian images**: `linux/amd64`, `linux/arm64`
- **Alpine images**: `linux/amd64`, `linux/arm64`, `linux/arm/v7`