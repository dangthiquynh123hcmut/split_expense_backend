#!/usr/bin/env bash
# exit on error
set -o errexit

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"
SRC_DIR="$PROJECT_ROOT/src"

# Print debug information
echo "=== Build Script Debug Info ==="
echo "Script directory: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "Source directory: $SRC_DIR"

# Install dependencies
pip install -r requirements.txt

# List files in the project root for debugging
echo -e "\n=== Project Root Contents ==="
ls -la "$PROJECT_ROOT"

# List files in the src directory
echo -e "\n=== Source Directory Contents ==="
ls -la "$SRC_DIR"

# Run Django management commands
echo -e "\n=== Running Django Commands ==="
cd "$PROJECT_ROOT"

# Set Python path to include src directory
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:$PYTHONPATH"
echo "PYTHONPATH set to: $PYTHONPATH"

# Verify Python can find the module
echo -e "\n=== Verifying Python module import ==="
python -c "import sys; print('\n'.join(sys.path))"
python -c "from split_expense_system.wsgi import application; print('Successfully imported WSGI application')" || echo "Failed to import WSGI application"

# Check if manage.py exists and is executable
if [ -f "$SRC_DIR/manage.py" ]; then
    echo "Found manage.py at $SRC_DIR/manage.py"

    # Set default email settings if not provided
    if [ -z "$EMAIL_BACKEND" ]; then
        echo "WARNING: EMAIL_BACKEND not set. Using console backend for email."
        export EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend"
    fi

    # Run collectstatic
    echo "Running collectstatic..."
    python "$SRC_DIR/manage.py" collectstatic --no-input || echo "Warning: collectstatic failed, but continuing..."

    # Run migrations
    echo "Running migrations..."
    python "$SRC_DIR/manage.py" migrate || echo "Warning: Migrations failed, but continuing..."

    # Install django-crontab if not already installed
    echo "Installing django-crontab..."
    pip install django-crontab || echo "Warning: Failed to install django-crontab, but continuing..."

    # Add and verify cron job for token cleanup
    echo "Setting up cron job for token cleanup..."
    if python "$SRC_DIR/manage.py" crontab add 2>/dev/null; then
        echo "Cron job added successfully"
        echo "Current registered cron jobs:"
        python "$SRC_DIR/manage.py" crontab show || echo "Failed to show cron jobs"
    else
        echo "Warning: Failed to add cron job. Make sure django-crontab is installed and configured in settings.py"
    fi
else
    echo "Error: manage.py not found in $SRC_DIR"
    echo "Current directory: $(pwd)"
    echo "Contents of current directory:"
    ls -la
    exit 1
fi
