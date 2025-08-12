#!/bin/bash
set -e

MODE=$1

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$(dirname "${BASH_SOURCE[0]}")/../utils.sh"

ENV_DIR="$BASE_DIR/../../env"
EXAMPLE_ENV_FILE="$ENV_DIR/.env.sample"

# Create env directory if not exists
mkdir -p "$ENV_DIR"

TARGET_ENV_FILE="$ENV_DIR/.env.$MODE"

# Check if .env file exists
if [[ -f "$TARGET_ENV_FILE" ]]; then
  print_warn "Found .env.$MODE — skipping environment setup."
  return 0 2>/dev/null || exit 0
fi

cp "$EXAMPLE_ENV_FILE" "$TARGET_ENV_FILE"

print "> Checking if you want to override environment variables."

# Function to read variable from .env file
get_env_var() {
  local var_name=$1
  grep "^$var_name=" "$TARGET_ENV_FILE" | cut -d '=' -f2-
}

# Function to replace variable in .env file
set_env_var() {
  local var_name=$1
  local var_value=$2
  if grep -q "^$var_name=" "$TARGET_ENV_FILE"; then
    # Replace existing line
    sed -i.bak "s/^$var_name=.*/$var_name=$var_value/" "$TARGET_ENV_FILE"
    rm -f "$TARGET_ENV_FILE.bak"
  else
    # Append if not exists
    echo "$var_name=$var_value" >> "$TARGET_ENV_FILE"
  fi
}

read -p "❓ Do you want to override environment variables? (y/N):" override_answer
override_answer=$(echo "$override_answer" | tr '[:upper:]' '[:lower:]')

if [[ "$override_answer" == "y" || "$override_answer" == "yes" ]]; then
  # List of env variables to ask about
  vars=("POSTGRES_DB" "POSTGRES_USER" "POSTGRES_PASSWORD" "POSTGRES_HOST" "POSTGRES_PORT")

  for var in "${vars[@]}"; do
    current_val=$(get_env_var "$var")
    read -p "Enter value for $var [$current_val]: " new_val
    if [[ -n "$new_val" ]]; then
      set_env_var "$var" "$new_val"
    fi
  done
  print_msg "> Environment variables updated in $TARGET_ENV_FILE."
else
  print_msg "> Skipping environment variable override."
fi

# Generate Django SECRET_KEY
generate_django_secret_key() {
  python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
}

SECRET_KEY=$(generate_django_secret_key)
print_warn "Generated SECRET_KEY: $SECRET_KEY"
set_env_var "SECRET_KEY" "$SECRET_KEY"

print_msg "✅ Done"
