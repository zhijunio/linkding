# Build stage: Node.js (shared)
FROM node:22-alpine AS node-build
WORKDIR /etc/linkding
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm,id=npm-cache \
    npm ci
COPY rollup.config.mjs postcss.config.js ./
COPY bookmarks/frontend ./bookmarks/frontend/
COPY bookmarks/styles ./bookmarks/styles/
RUN --mount=type=cache,target=node_modules,id=npm-build \
    npm run build

# Build stage: uBlock Origin Lite
FROM node:22-alpine AS ublock-build
WORKDIR /etc/linkding
ARG UBOL_TAG=2026.308.1810
RUN --mount=type=cache,target=/var/cache/apk,id=ublock-apk \
    apk add --no-cache curl jq unzip && \
    curl -sLf "https://github.com/uBlockOrigin/uBOL-home/releases/download/${UBOL_TAG}/uBOLite_${UBOL_TAG}.chromium.zip" -o uBOLite.zip && \
    unzip -q uBOLite.zip -d uBOLite.chromium.mv3 && rm uBOLite.zip && \
    jq '.declarative_net_request.rule_resources |= map(if .id == "annoyances-overlays" or .id == "annoyances-cookies" or .id == "annoyances-social" or .id == "annoyances-widgets" or .id == "annoyances-others" then .enabled = true else . end)' \
        uBOLite.chromium.mv3/manifest.json > temp.json && mv temp.json uBOLite.chromium.mv3/manifest.json && \
    rm -rf /var/cache/apk/*

# Build stage: Python dependencies (Debian)
FROM python:3.13.7-slim-trixie AS build-deps
RUN apt-get update && apt-get -y install --no-install-recommends \
    build-essential pkg-config libpq-dev libicu-dev libsqlite3-dev libffi-dev wget unzip gettext curl && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /etc/linkding
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/uv
RUN uv venv /etc/linkding/.venv
COPY pyproject.toml uv.lock ./
ENV VIRTUAL_ENV=/etc/linkding/.venv PATH="/etc/linkding/.venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache \
    uv sync --no-dev --group postgres

# Build stage: ICU extension
FROM build-deps AS compile-icu
ARG SQLITE_RELEASE_YEAR=2023
ARG SQLITE_RELEASE=3430000
RUN --mount=type=cache,target=/var/cache/apt,id=apt-cache \
    wget -q https://www.sqlite.org/${SQLITE_RELEASE_YEAR}/sqlite-amalgamation-${SQLITE_RELEASE}.zip && \
    unzip -q sqlite-amalgamation-${SQLITE_RELEASE}.zip && \
    cp sqlite-amalgamation-${SQLITE_RELEASE}/sqlite3.h . && \
    cp sqlite-amalgamation-${SQLITE_RELEASE}/sqlite3ext.h . && \
    wget -q "https://www.sqlite.org/src/raw/ext/icu/icu.c?name=91c021c7e3e8bbba286960810fa303295c622e323567b2e6def4ce58e4466e60" -O icu.c && \
    gcc -O3 -fPIC -shared icu.c `pkg-config --libs --cflags icu-uc icu-io` -o libicu.so && \
    rm -f sqlite-amalgamation-${SQLITE_RELEASE}.zip && rm -rf sqlite-amalgamation-${SQLITE_RELEASE} icu.c

# Runtime stage: linkding-plus base (Debian)
FROM build-deps AS linkding-plus-base
RUN apt-get update && apt-get -y install --no-install-recommends \
    media-types libpq-dev libicu-dev libssl3t64 curl gettext chromium && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get -y install --no-install-recommends nodejs && \
    mkdir -p chromium-profile && \
    rm -rf /var/lib/apt/lists/* && \
    chown -R www-data:www-data chromium-profile 2>/dev/null || true
RUN --mount=type=cache,target=/root/.npm,id=npm-global \
    npm install -g single-file-cli@2.0.75
ENV VIRTUAL_ENV=/etc/linkding/.venv PATH="/etc/linkding/.venv/bin:$PATH" LD_ENABLE_SNAPSHOTS=True NPM_CONFIG_CACHE=/tmp/npm-cache

# Build stage: Static files and translations
FROM build-deps AS static-build
COPY --from=compile-icu /etc/linkding/libicu.so .
COPY --from=node-build /etc/linkding/bookmarks/static bookmarks/static/
COPY bookmarks/*.py ./bookmarks/
COPY bookmarks/management bookmarks/management/
COPY bookmarks/templates bookmarks/templates/
COPY bookmarks/settings bookmarks/settings/
COPY bookmarks/urls.py bookmarks/migrations.py ./bookmarks/
COPY locale ./locale/
COPY requirements.txt pyproject.toml uv.lock manage.py bootstrap.sh ./
COPY *.conf .
ENV VIRTUAL_ENV=/etc/linkding/.venv PATH="/etc/linkding/.venv/bin:$PATH"
RUN mkdir -p data && python manage.py collectstatic --noinput && python manage.py compilemessages

# Final stage: linkding (Debian)
FROM python:3.13.7-slim-trixie AS linkding
RUN apt-get update && apt-get -y install --no-install-recommends \
    media-types libpq-dev libicu-dev libssl3t64 curl gettext && \
    adduser --system --group --uid 82 www-data || true && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /etc/linkding
COPY --from=build-deps /etc/linkding/.venv .venv/
COPY --from=static-build /etc/linkding/libicu.so .
COPY --from=static-build /etc/linkding/data ./data/
COPY --from=static-build /etc/linkding/bookmarks/static bookmarks/static/
COPY --from=static-build /etc/linkding/bookmarks/locale bookmarks/locale/
COPY --from=static-build /etc/linkding/manage.py .
COPY --from=static-build /etc/linkding/bootstrap.sh .
COPY --from=static-build /etc/linkding/*.py .
COPY --from=static-build /etc/linkding/*.conf .
HEALTHCHECK --interval=30s --retries=3 --timeout=1s CMD curl -f http://localhost:${LD_SERVER_PORT:-9090}/${LD_CONTEXT_PATH}health || exit 1
CMD ["/bin/bash", "./bootstrap.sh"]

# Final stage: linkding-plus (Debian)
FROM linkding-plus-base AS linkding-plus
COPY --from=static-build /etc/linkding/libicu.so .
COPY --from=static-build /etc/linkding/data ./data/
COPY --from=static-build /etc/linkding/bookmarks/static bookmarks/static/
COPY --from=static-build /etc/linkding/bookmarks/locale bookmarks/locale/
COPY --from=ublock-build /etc/linkding/uBOLite.chromium.mv3 uBOLite.chromium.mv3/
COPY --from=static-build /etc/linkding/manage.py .
COPY --from=static-build /etc/linkding/bootstrap.sh .
COPY --from=static-build /etc/linkding/*.py .
COPY --from=static-build /etc/linkding/*.conf .
HEALTHCHECK --interval=30s --retries=3 --timeout=1s CMD curl -f http://localhost:${LD_SERVER_PORT:-9090}/${LD_CONTEXT_PATH}health || exit 1
CMD ["/bin/bash", "./bootstrap.sh"]
