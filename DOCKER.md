# SAT Builder Docker Setup

This document explains how to build, run, configure, and publish the SAT Builder Docker image.

## Overview

SAT Builder is packaged as a Python 3.12 Docker container.

The container:

- uses `python:3.12-slim`
- runs from `/sat-builder`
- starts the application with:

```shell
python -m src
```

- copies only the required runtime folders:
  - `configs`
  - `src`
  - `templates`
- copies `env.template` into the image as `.env`
- excludes local/private files through `.dockerignore`

## Project files

Relevant Docker-related files:

```text
.
├── Dockerfile
├── docker-compose.yaml
├── .dockerignore
├── env.template
├── requirements.txt
├── configs/
├── src/
└── templates/
```

## Runtime structure inside the container

After building the image, the container will contain:

```text
/sat-builder/
├── .env
├── configs/
├── src/
├── templates/
└── logs/
```

The `.env` file inside the container is created from:

```text
env.template
```

using:

```dockerfile
COPY env.template ./.env
```

Your local `.env` file is not copied into the image.

## Environment configuration

The image uses `env.template` as the default container configuration.

Example runtime values:

```env
SERVICE__ID=sat-builder
SERVICE__NAME=SAT Builder

SERVER__HOST=0.0.0.0
SERVER__PORT=8000
SERVER__RELOAD=false
SERVER__LOG_LEVEL=info

CORS__ENABLED=false
CORS__ORIGINS=*
CORS__ALLOW_CREDENTIALS=true
CORS__ALLOW_METHODS=*
CORS__ALLOW_HEADERS=*

LOGGING__LEVEL=INFO
LOGGING__TO_FILE=true
LOGGING__TO_CONSOLE=true
LOGGING__FILE_PATH=logs/app.log
LOGGING__ERROR_FILE_PATH=logs/error.log
LOGGING__ACCESS_FILE_PATH=logs/access.log
LOGGING__SEPARATE_ERROR_LOG=true
LOGGING__SEPARATE_ACCESS_LOG=true
LOGGING__MAX_BYTES=10485760
LOGGING__BACKUP_COUNT=5
LOGGING__JSON_FORMAT=false
LOGGING__USE_COLORS=true
```

## Build the image

From the project root, run:

```shell
docker build -t sat-builder:1.0.0 .
```

You can also tag it as `latest`:

```shell
docker build -t sat-builder:latest .
```

Or build both tags at once:

```shell
docker build -t sat-builder:1.0.0 -t sat-builder:latest .
```

## Run the container

Run the container locally:

```shell
docker run --rm -p 8000:8000 sat-builder:1.0.0
```

The application should be available at:

```text
http://localhost:8000
```

## Run with Docker Compose

Start the service using the published image:

```shell
docker compose up -d
```

Pull the latest image and restart:

```shell
docker compose pull
docker compose up -d
```

Stop the service:

```shell
docker compose down
```

View logs:

```shell
docker compose logs -f sat-builder
```

## Health check

The Dockerfile includes a health check against:

```text
http://localhost:8000/health
```

You can test it manually:

```shell
curl http://localhost:8000/health
```

## Override configuration at runtime

You can override environment variables using `-e`.

Example:

```shell
docker run --rm -p 8000:8000 \
  -e SERVER__LOG_LEVEL=debug \
  -e CORS__ENABLED=true \
  sat-builder:1.0.0
```

You can also use your local `.env` file at runtime:

```shell
docker run --rm -p 8000:8000 \
  --env-file .env \
  sat-builder:1.0.0
```

This does not bake your `.env` into the image.

## Docker ignore behavior

The `.dockerignore` file excludes unnecessary files from the Docker build context, including:

```text
.git/
.env
README*
logs/
tests/
.venv/
__pycache__/
Dockerfile
.dockerignore
docker-compose*.yml
```

Important behavior:

- local `.env` is excluded
- `env.template` is included
- all `README*` files are excluded from the image
- only required runtime folders are copied explicitly

## Publish the image

Log in to Docker Hub:

```shell
docker login
```

Build and tag the image:

```shell
docker build -t sat-builder:1.0.0 -t sat-builder:latest .
```

Push the image:

```shell
docker push sat-builder:1.0.0
docker push sat-builder:latest
```

## Recommended local workflow

Build:

```shell
docker build -t sat-builder:1.0.0 .
```

Run:

```shell
docker run --rm -p 8000:8000 sat-builder:1.0.0
```

Run with Docker Compose:

```shell
docker compose up -d
```

Run with debug logging:

```shell
docker run --rm -p 8000:8000 \
  -e SERVER__LOG_LEVEL=debug \
  sat-builder:1.0.0
```

Check health:

```shell
curl http://localhost:8000/health
```

