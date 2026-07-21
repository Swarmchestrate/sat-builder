#!/usr/bin/env bash

set -euo pipefail

VENV_DIR=".venv"
RESET_VENV=false

if [[ "${1:-}" == "--reset-venv" ]]; then
  RESET_VENV=true
fi

echo "Starting SAT Builder local development setup..."

if [[ "${RESET_VENV}" == true ]]; then
  echo "Resetting virtual environment..."
  rm -rf "${VENV_DIR}"
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating virtual environment..."
  python3 -m venv "${VENV_DIR}"
fi

echo "Activating virtual environment..."
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing dependencies..."

if [[ ! -f "requirements.txt" ]]; then
  echo "Error: requirements.txt not found. Run this script from the project root."
  exit 1
fi

pip install -r requirements.txt

if [[ -f "requirements-dev.txt" ]]; then
  pip install -r requirements-dev.txt
else
  echo "Warning: requirements-dev.txt not found. Skipping development dependencies."
fi

if [[ ! -f ".env" ]]; then
  if [[ -f "env.template" ]]; then
    echo "Creating .env from env.template..."
    cp env.template .env
  else
    echo "Warning: env.template not found. Skipping .env creation."
  fi
else
  echo ".env already exists. Keeping existing file."
fi

echo "Creating logs directory..."
mkdir -p logs

echo "Starting application..."
python -m src