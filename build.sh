#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Print current directory and list files (for debugging)
pwd
ls -la

# Run Django management commands from the src directory
python /src/manage.py collectstatic --no-input
python /src/manage.py migrate
