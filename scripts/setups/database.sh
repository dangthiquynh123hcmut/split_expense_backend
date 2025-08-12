#!/bin/bash
set -e

MODE=$1

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$(dirname "${BASH_SOURCE[0]}")/../utils.sh"

ENV="$BASE_DIR/../../env/.env.$MODE"

POSTGRES_DB=$(grep -E '^POSTGRES_DB=' "$ENV" | cut -d '=' -f2-)
POSTGRES_USER=$(grep -E '^POSTGRES_USER=' "$ENV" | cut -d '=' -f2-)
POSTGRES_PASSWORD=$(grep -E '^POSTGRES_PASSWORD=' "$ENV" | cut -d '=' -f2-)
POSTGRES_HOST=$(grep -E '^POSTGRES_HOST=' "$ENV" | cut -d '=' -f2-)
POSTGRES_PORT=$(grep -E '^POSTGRES_PORT=' "$ENV" | cut -d '=' -f2-)

print "> Checking if PostgreSQL is installed..."

if command -v psql >/dev/null 2>&1; then
    print_msg "> PostgreSQL client (psql) found."
else
    print_err "> PostgreSQL client (psql) is NOT installed."
    print "> Please install PostgreSQL before proceeding."
    exit 1
fi

print "> Checking if PostgreSQL database exists..."
if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" >/dev/null 2>&1; then
    print_msg "> PostgreSQL database exists."
else
    print_err "> PostgreSQL database does NOT exist."

    print "> Creating PostgreSQL database..."
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"
    print_msg "> PostgreSQL database created."
fi

print_msg "✅ Done"
