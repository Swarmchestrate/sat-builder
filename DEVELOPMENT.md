# SAT Builder Local Development Setup

This document explains how to set up and run SAT Builder locally for development purposes.

## Overview

SAT Builder is a Python FastAPI application that can be run locally without Docker.

The application starts with:

```shell
python -m src
```

A helper script is provided to simplify local setup. The script creates a virtual environment, installs dependencies, prepares local configuration, creates the logs directory, and starts the application.

## Requirements

Before starting, make sure the following tools are installed:

- Python 3.12 or compatible Python 3 version
- `pip`
- `venv`

You can check your Python version with:

```shell
python3 --version
```

## Project files

Relevant local development files:

```text
.
├── run_dev.sh
├── env.template
├── requirements.txt
├── configs/
├── src/
├── templates/
└── logs/
```

## Local environment file

The application uses a local `.env` file for runtime configuration.

For development, `.env` is created from:

```text
env.template
```

The helper script only creates `.env` if it does not already exist.

This means:

- if `.env` does not exist, it will be created from `env.template`
- if `.env` already exists, it will be kept unchanged

Your local `.env` file should not be committed to Git.

## Setup script

The local development script is named:

```text
run_dev.sh
```

It performs the following steps:

1. Creates a Python virtual environment in `.venv` if it does not already exist.
2. Activates the virtual environment.
3. Upgrades `pip`.
4. Installs dependencies from `requirements.txt`.
5. Creates `.env` from `env.template` if `.env` does not already exist.
6. Creates the `logs/` directory.
7. Starts the application with `python -m src`.

## Make the script executable

Run this once:
```shell
chmod +x run_dev.sh
```

## Run the application locally

Start the application with:
```shell
./run_dev.sh
```

The application should start using the values from `.env`.

By default, the API should be available at:
```text
http://localhost:8000
```

## Health check

If the health endpoint is enabled, test it with:
```shell
curl http://localhost:8000/health
```

## Manual setup without the script

If you prefer to run the setup manually, use the following commands.

Create a virtual environment:
```shell
python3 -m venv .venv
```

Activate it:
```shell
source .venv/bin/activate
```

Upgrade `pip`:

```shell
python -m pip install --upgrade pip
```

Install dependencies:

```shell
pip install -r requirements.txt
```

Create `.env` from the template:

```shell
cp env.template .env
```

Create the logs directory:

```shell
mkdir -p logs
```

Run the application:

```shell
python -m src
```

## Configuration

Runtime configuration is controlled through `.env`.

Common development values include:

```env
SERVER__HOST=0.0.0.0
SERVER__PORT=8000
SERVER__RELOAD=false
SERVER__LOG_LEVEL=debug
LOGGING__TO_CONSOLE=true
LOGGING__TO_FILE=true
```

After changing `.env`, restart the application for changes to take effect.

## Notes

- Run the script from the project root.
- Do not commit `.env`.
- Do not commit `.venv`.
- Do not commit generated logs.
- If dependencies change, rerun `./run_dev.sh` to reinstall them.
- The application starts with `python -m src`, so the `src` package must be executable as a module.
```
