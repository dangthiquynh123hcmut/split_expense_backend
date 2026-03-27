#!/bin/bash

# Split Expense Backend - Production Deployment Script
# Usage: ./scripts/deploy-prod.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "================================"
echo "Split Expense Backend Deployment"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    if [ ! -f "$PROJECT_ROOT/env/.env.prod" ]; then
        log_error "env/.env.prod file not found"
        log_warn "Please create env/.env.prod from env/.env.sample"
        exit 1
    fi

    log_info "All requirements met ✓"
}

build_and_deploy() {
    log_info "Building Docker images..."
    cd "$PROJECT_ROOT"
    docker-compose build --no-cache

    log_info "Starting services..."
    docker-compose up -d

    log_info "Waiting for services to be healthy..."
    sleep 10

    # Check if django service is healthy
    if docker-compose exec django curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
        log_info "Django service is healthy ✓"
    else
        log_warn "Django service might still be starting, check logs with: docker-compose logs -f django"
    fi
}

create_superuser() {
    read -p "Do you want to create a superuser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Creating superuser..."
        cd "$PROJECT_ROOT"
        docker-compose exec django sh -c "cd src && python manage.py createsuperuser"
    fi
}

show_status() {
    log_info "Service Status:"
    cd "$PROJECT_ROOT"
    docker-compose ps

    log_info "Logs (last 20 lines):"
    docker-compose logs --tail=20
}

show_help() {
    cat << EOF
Usage: ./scripts/deploy-prod.sh [COMMAND]

Commands:
    (no command)  - Full deployment
    build         - Build Docker images only
    start         - Start services
    stop          - Stop services
    restart       - Restart services
    logs          - Show logs
    status        - Show status
    cleanup       - Clean up stopped containers and unused images
    backup        - Backup database
    restore       - Restore database from backup

Examples:
    ./scripts/deploy-prod.sh              # Full deployment
    ./scripts/deploy-prod.sh logs         # View logs
    ./scripts/deploy-prod.sh stop         # Stop services
EOF
}

# Parse arguments
case "${1:-}" in
    build)
        check_requirements
        cd "$PROJECT_ROOT"
        docker-compose build --no-cache
        ;;
    start)
        check_requirements
        cd "$PROJECT_ROOT"
        docker-compose up -d
        log_info "Services started"
        show_status
        ;;
    stop)
        cd "$PROJECT_ROOT"
        docker-compose down
        log_info "Services stopped"
        ;;
    restart)
        cd "$PROJECT_ROOT"
        docker-compose restart
        log_info "Services restarted"
        show_status
        ;;
    logs)
        cd "$PROJECT_ROOT"
        docker-compose logs -f
        ;;
    status)
        show_status
        ;;
    cleanup)
        log_warn "Cleaning up..."
        docker system prune -f
        docker volume prune -f
        log_info "Cleanup complete"
        ;;
    backup)
        log_info "Backing up database..."
        cd "$PROJECT_ROOT"
        mkdir -p backups
        docker-compose exec postgres pg_dump -U $(grep POSTGRES_USER env/.env.prod | cut -d '=' -f2) $(grep POSTGRES_DB env/.env.prod | cut -d '=' -f2) | gzip > "backups/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
        log_info "Database backed up"
        ;;
    restore)
        if [ -z "$2" ]; then
            log_error "Usage: $0 restore <backup-file>"
            exit 1
        fi
        log_warn "Restoring database from $2..."
        cd "$PROJECT_ROOT"
        gunzip < "$2" | docker-compose exec -T postgres psql -U $(grep POSTGRES_USER env/.env.prod | cut -d '=' -f2) $(grep POSTGRES_DB env/.env.prod | cut -d '=' -f2)
        log_info "Database restored"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        check_requirements
        build_and_deploy
        show_status
        create_superuser
        log_info "Deployment complete!"
        log_info "Access your application at: https://yourdomain.com"
        ;;
esac
