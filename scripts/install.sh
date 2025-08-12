#!/bin/bash
set -e

MODE=$1

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXECUTE_BASH_DIR=$(dirname "${BASH_SOURCE[0]}")/setups/

source "$(dirname "${BASH_SOURCE[0]}")/utils.sh"

export ENV=$MODE

STEP=1

if [[ -z "$MODE" ]]; then
  print_err "Usage: $0 [dev|prod]"
  exit 1
fi

if [[ "$MODE" != "dev" && "$MODE" != "prod" ]]; then
  print_err "Invalid mode: $MODE. Use 'dev' or 'prod'."
  exit 1
fi

# Python setup
print "[$STEP] Setting up Python environment..."
source "$EXECUTE_BASH_DIR/python.sh" $MODE
((STEP++))

# Env setup
print "[$STEP] Setting up environment variables..."
source "$EXECUTE_BASH_DIR/env.sh" $MODE
((STEP++))

# PostgreSQL setup
print "[$STEP] Setting up PostgreSQL database..."
source "$EXECUTE_BASH_DIR/database.sh" $MODE
((STEP++))
