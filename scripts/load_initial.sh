#!/bin/bash

MODE=$1

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$(dirname "${BASH_SOURCE[0]}")/utils.sh"

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

export ENV=$MODE

print "> Loading initial data..."

# Define list of initial data files
INITIAL_APPS=(
    "attachment"
)



# Load initial data
cd src
for app in "${INITIAL_APPS[@]}"; do
    echo "Loading initial data for app: $app"
    FILES=$(find ${BASE_DIR}/../src/${app}/fixtures -name "*.json")

    for fixture in $FILES; do
        python manage.py loaddata $fixture
    done
done

print_msg "✅ Initial data loaded successfully."
