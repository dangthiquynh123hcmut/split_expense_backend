#!/bin/bash
set -e

ENV=$1

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$(dirname "${BASH_SOURCE[0]}")/../utils.sh"

export ENV=$ENV

# Check for Python 3.12
if command -v python3.12 &>/dev/null; then
    PYTHON=python3.12
elif command -v python &>/dev/null && [[ "$($python --version 2>&1)" == *"Python 3.12"* ]]; then
    PYTHON=python
elif command -v python3 &>/dev/null && [[ "$($(command -v python3) --version 2>&1)" == *"Python 3.12"* ]]; then
    PYTHON=python3
else
    print_err "Python 3.12 is not installed. Please install Python 3.12 and try again."
    exit 1
fi

print "> Python 3.12 found: $($PYTHON --version)"

# Create virtual environment
print "> Creating virtual environment with Python 3.12..."
$PYTHON -m venv venv

# Activate virtual environment
print "> Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
print "> Upgrading pip..."
pip install --upgrade pip --quiet

# Install packages if requirements.txt exists
if [[ -f "requirements.txt" ]]; then
    print "> Installing dependencies from requirements.txt..."
    pip install -r requirements.txt --quiet
else
    print_err "> No requirements.txt found"
    exit 1
fi

# Install development packages if requirements-dev.txt exists
if [[ "$ENV" == "dev" ]]; then
    print "> Installing development dependencies from requirements-dev.txt..."
    if [[ -f "requirements-dev.txt" ]]; then
        pip install -r requirements-dev.txt --quiet
    else
        print_err "> No requirements-dev.txt found"
        exit 1
    fi
fi

print_msg "✅ Python 3.12 virtual environment is ready."
