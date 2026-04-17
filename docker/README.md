# Docker

![img](https://raw.githubusercontent.com/zhijunio/linkding/master/assets/header.svg)

## Introduction

linkding is a bookmark manager that you can host yourself. It's designed be to be minimal, fast, and easy to set up using Docker.

The name comes from:

- *link* which is often used as a synonym for URLs and bookmarks in common language
- *Ding* which is German for thing
- ...so basically something for managing your links

**Feature Overview:**

- Clean UI optimized for readability
- Organize bookmarks with tags
- Bulk editing, Markdown notes, read it later functionality
- Share bookmarks with other users or guests
- Automatically provides titles, descriptions and icons of bookmarked websites
- Automatically archive websites, either as local HTML file or on Internet Archive
- Import and export bookmarks in Netscape HTML format
- Installable as a Progressive Web App (PWA)
- Extensions for [Firefox](https://addons.mozilla.org/firefox/addon/linkding-extension/) and [Chrome](https://chrome.google.com/webstore/detail/linkding-extension/beakmhbijpdhipnjhnclmhgjlddhidpe), as well as a bookmarklet
- SSO support via OIDC or authentication proxies
- REST API for developing 3rd party apps
- Admin panel for user self-service and raw data access

**Demo:** <https://linkding.zhijunio.cc/>

**Screenshot:**

![img](https://raw.githubusercontent.com/zhijunio/linkding/master/docs/public/linkding-screenshot-zh.png)

### Getting Started

The following links help you to get started with linkding:

- [Install linkding on your own server](https://linkding.link/installation) or [check managed hosting options](https://linkding.link/managed-hosting)
- [Install the browser extension](https://linkding.link/browser-extension)
- [Check out community projects](https://linkding.link/community), which include mobile apps, browser extensions, libraries and more

---

## Docker Images

This directory contains Dockerfiles for building linkding Docker images. The project provides multiple image variants to suit different use cases:

### Image Variants

| Variant | Dockerfile | Description | Size |
|---------|-----------|-------------|------|
| `latest` | `default.Dockerfile` | Standard image based on Debian slim. Provides all core functionality. | Medium |
| `latest-alpine` | `alpine.Dockerfile` | Alpine-based image for smaller size. 🧪 Experimental | Small |
| `latest-plus` | `default.Dockerfile` (target: `linkding-plus`) | Includes Chromium and uBlock Origin Lite for HTML snapshot archiving. Requires more memory and disk space. | Large |
| `latest-plus-alpine` | `alpine.Dockerfile` (target: `linkding-plus`) | Alpine-based plus variant. 🧪 Experimental | Medium-Large |

### Image Features

**Standard Images (`latest`, `latest-alpine`):**

- Core bookmark management functionality
- SQLite database support (default)
- PostgreSQL database support
- REST API
- Background task processing
- Multi-language support (English, Simplified Chinese)

**Plus Images (`latest-plus`, `latest-plus-alpine`):**

- All features from standard images
- HTML snapshot archiving using Chromium
- uBlock Origin Lite integration for cleaner snapshots
- Requires `LD_ENABLE_SNAPSHOTS=True` environment variable

### Platform Support

All images support multiple architectures:

- `linux/amd64` (x86_64)
- `linux/arm64` (ARM 64-bit)
- `linux/arm/v7` (ARM 32-bit, Raspberry Pi compatible)

Note: `latest-plus` variants exclude ARMv7 due to Chromium compatibility constraints.

---

## Running Docker Containers

### Quick Start with Docker Run

#### Basic Setup

```bash
docker run -d \
  --name linkding \
  -p 9090:9090 \
  -v /path/to/data:/etc/linkding/data \
  zhijunio/linkding:latest
```

Replace `/path/to/data` with an absolute path to a directory on your host where you want to store the linkding database and files.

#### With Initial Superuser

```bash
docker run -d \
  --name linkding \
  -p 9090:9090 \
  -v /path/to/data:/etc/linkding/data \
  -e LD_SUPERUSER_NAME=admin \
  -e LD_SUPERUSER_PASSWORD=your-secure-password \
  zhijunio/linkding:latest
```

#### Using Plus Image (with snapshots)

```bash
docker run -d \
  --name linkding \
  -p 9090:9090 \
  -v /path/to/data:/etc/linkding/data \
  -e LD_SUPERUSER_NAME=admin \
  -e LD_SUPERUSER_PASSWORD=your-secure-password \
  -e LD_ENABLE_SNAPSHOTS=True \
  zhijunio/linkding:latest-plus
```

### Using Docker Compose

1. **Download configuration files:**

```bash
# Download docker-compose.yml and .env.sample
curl -O https://raw.githubusercontent.com/zhijunio/linkding/master/docker-compose.yml
curl -O https://raw.githubusercontent.com/zhijunio/linkding/master/.env.sample
```

2. **Configure environment variables:**

```bash
# Copy and edit the environment file
cp .env.sample .env
nano .env  # or use your preferred editor
```

3. **Start the container:**

```bash
docker-compose up -d
```

4. **View logs:**

```bash
docker-compose logs -f linkding
```

### Environment Variables

Key environment variables (see `.env.sample` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `LD_SUPERUSER_NAME` | Initial superuser username | (empty) |
| `LD_SUPERUSER_PASSWORD` | Initial superuser password | (empty) |
| `LD_SERVER_PORT` | Internal server port | `9090` |
| `LD_CONTEXT_PATH` | Context path prefix (must end with `/`) | (empty) |
| `LD_LANGUAGE` | Interface language (`en-us`, `zh-hans`) | `en-us` |
| `LD_DISABLE_BACKGROUND_TASKS` | Disable background task processing | `False` |
| `LD_ENABLE_SNAPSHOTS` | Enable HTML snapshot archiving (plus images only) | `False` |
| `LD_DB_ENGINE` | Database engine (`sqlite` or `postgres`) | `sqlite` |
| `LD_DB_HOST` | PostgreSQL host | `localhost` |
| `LD_DB_NAME` | Database name | `linkding` |
| `LD_DB_USER` | Database username | `linkding` |
| `LD_DB_PASSWORD` | Database password | (empty) |

### Data Persistence

The application stores all data in `/etc/linkding/data` inside the container. You must mount this directory to a host directory to persist data:

```bash
-v /host/path/to/data:/etc/linkding/data
```

**Important:** Always use absolute paths for volume mounts.

The data directory contains:

- `db.sqlite3` - SQLite database (if using SQLite)
- `favicons/` - Downloaded favicon files
- `previews/` - Website preview images
- `assets/` - Archived HTML snapshots (if using plus image)
- `secret_key.txt` - Application secret key

### Port Mapping

The container exposes port `9090` by default. Map it to any host port:

```bash
-p 8080:9090  # Access at http://localhost:8080
-p 9090:9090   # Access at http://localhost:9090
```

### Health Check

The image includes a health check that verifies the application is responding:

```dockerfile
HEALTHCHECK --interval=30s --retries=3 --timeout=1s \
  CMD curl -f http://localhost:${LD_SERVER_PORT:-9090}/${LD_CONTEXT_PATH}health || exit 1
```

Check container health status:

```bash
docker ps  # Shows health status
docker inspect linkding | grep -A 10 Health
```

---

## User Management

### Create Initial Superuser

#### Option 1: Environment Variables (Recommended)

Set these environment variables when starting the container:

```bash
-e LD_SUPERUSER_NAME=admin \
-e LD_SUPERUSER_PASSWORD=your-secure-password
```

#### Option 2: Manual Creation

If you didn't set environment variables, create a superuser manually:

```bash
# Docker
docker exec -it linkding python manage.py createsuperuser

# Docker Compose
docker-compose exec linkding python manage.py createsuperuser
```

### Access the Application

After starting the container, access linkding at:

- **Local:** <http://localhost:9090> (or your mapped port)
- **Remote:** <http://your-server-ip:9090>

---

## Upgrading

### Upgrade Process

1. **Stop the container:**

```bash
docker stop linkding
```

2. **Pull the latest image:**

```bash
docker pull zhijunio/linkding:latest
```

3. **Remove the old container:**

```bash
docker rm linkding
```

4. **Start a new container with the same configuration:**

```bash
docker run -d \
  --name linkding \
  -p 9090:9090 \
  -v /path/to/data:/etc/linkding/data \
  zhijunio/linkding:latest
```

### Using Docker Compose

```bash
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d
```

### Automated Upgrade Script

An automated upgrade script is available:

```bash
# Set environment variables
export LD_CONTAINER_NAME=linkding
export LD_HOST_PORT=9090
export LD_HOST_DATA_DIR=/path/to/data

# Run upgrade script
./install-linkding.sh
```

---

## Troubleshooting

### Container Won't Start

1. **Check logs:**

```bash
docker logs linkding
```

2. **Verify data directory permissions:**

```bash
# Ensure the data directory is writable
chmod -R 755 /path/to/data
```

3. **Check port availability:**

```bash
# Check if port is already in use
netstat -tuln | grep 9090
# or
lsof -i :9090
```

### Database Issues

**SQLite Lock Errors:**

- Ensure only one container instance is accessing the database
- Check file permissions on the data directory
- Verify the volume mount is working correctly

**PostgreSQL Connection:**

- Verify `LD_DB_HOST`, `LD_DB_NAME`, `LD_DB_USER`, `LD_DB_PASSWORD` are correct
- Ensure PostgreSQL is accessible from the container
- Check network connectivity: `docker exec linkding ping <db-host>`

### Performance Issues

**High Memory Usage (Plus Images):**

- Plus images require more memory due to Chromium
- Consider using standard images if snapshots aren't needed
- Monitor memory usage: `docker stats linkding`

**Slow Background Tasks:**

- Check if background tasks are enabled: `LD_DISABLE_BACKGROUND_TASKS=False`
- Review logs for task errors: `docker logs linkding`

### Health Check Failing

If health checks fail:

1. Verify the application is running: `docker exec linkding ps aux`
2. Check if the port is correct: `docker exec linkding netstat -tuln`
3. Test health endpoint manually: `docker exec linkding curl http://localhost:9090/health`

---

## Advanced Configuration

### Using PostgreSQL

1. **Set environment variables:**

```bash
LD_DB_ENGINE=postgres
LD_DB_HOST=postgres-server
LD_DB_NAME=linkding
LD_DB_USER=linkding
LD_DB_PASSWORD=your-password
LD_DB_PORT=5432
```

2. **Start container with PostgreSQL:**

```bash
docker run -d \
  --name linkding \
  -p 9090:9090 \
  -v /path/to/data:/etc/linkding/data \
  -e LD_DB_ENGINE=postgres \
  -e LD_DB_HOST=postgres-server \
  -e LD_DB_NAME=linkding \
  -e LD_DB_USER=linkding \
  -e LD_DB_PASSWORD=your-password \
  --network your-network \
  zhijunio/linkding:latest
```

### Context Path

To run linkding under a subpath (e.g., `/linkding/`):

```bash
-e LD_CONTEXT_PATH=/linkding/
```

Access at: <http://localhost:9090/linkding/>

### Authentication Proxy

Configure authentication proxy (e.g., Authelia):

```bash
-e LD_ENABLE_AUTH_PROXY=True
-e LD_AUTH_PROXY_USERNAME_HEADER=Remote-User
-e LD_AUTH_PROXY_LOGOUT_URL=https://auth.example.com/logout
-e LD_DISABLE_LOGIN_FORM=True
```

### Supervisor Mode

For better logging of background tasks:

```bash
-e LD_SUPERVISOR_MANAGED=True
```

This runs all processes under supervisor, enabling better log aggregation.

---

## Image Registry

Pre-built images are available from:

- **Docker Hub:** `zhijunio/linkding:latest`
- **GitHub Container Registry:** `ghcr.io/zhijunio/linkding:latest`

### Available Tags

- `latest` - Latest stable release (Debian-based)
- `latest-alpine` - Latest stable release (Alpine-based)
- `latest-plus` - Latest stable with snapshot support
- `latest-plus-alpine` - Latest stable plus (Alpine-based)
- `{version}` - Specific version tag (e.g., `1.0.0`)
- `{version}-alpine` - Specific version (Alpine)
- `{version}-plus` - Specific version with snapshots
- `{version}-plus-alpine` - Specific version plus (Alpine)

---

## Support

- **Documentation:** <https://linkding.link/docs>
- **GitHub Issues:** <https://github.com/zhijunio/linkding/issues>
- **Community:** <https://linkding.link/community>