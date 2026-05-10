#!/bin/bash
# ============================================================
# Deploy script – chạy trên EC2 instance (gọi bởi GitHub Actions/SSM)
# Biến môi trường cần có:
#   IMAGE_TAG        – git sha ngắn (vd: a1b2c3d)
#   DOCKER_USERNAME  – Docker Hub username
# ============================================================
set -euo pipefail

PROJECT_DIR="/opt/split-expense-backend"
DOCKER_IMAGE="${DOCKER_USERNAME}/split-expense-backend"
FULL_IMAGE="${DOCKER_IMAGE}:${IMAGE_TAG}"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Kiểm tra biến môi trường ──────────────────────────────────
if [[ -z "${IMAGE_TAG:-}" || -z "${DOCKER_USERNAME:-}" ]]; then
  log_error "IMAGE_TAG and DOCKER_USERNAME must be set"
  exit 1
fi

cd "$PROJECT_DIR"

log_info "====================================="
log_info "  Split Expense – EC2 Deploy"
log_info "  Image : $FULL_IMAGE"
log_info "  Host  : $(hostname)"
log_info "====================================="

# ── 1. Git pull để lấy code mới nhất (bao gồm docker-compose.prod.yml) ──
log_info "Pulling latest code from git..."
git -C "$PROJECT_DIR" fetch --all
git -C "$PROJECT_DIR" reset --hard origin/main

# ── 2. Tự động fetch .env.prod từ SSM Parameter Store nếu chưa có ──────
ENV_FILE="${PROJECT_DIR}/env/.env.prod"
if [[ ! -f "$ENV_FILE" ]]; then
  log_warn ".env.prod not found locally – fetching from SSM Parameter Store..."
  mkdir -p "${PROJECT_DIR}/env"
  aws ssm get-parameter \
    --region "${AWS_REGION:-ap-southeast-1}" \
    --name "/split-expense/prod/env" \
    --with-decryption \
    --query "Parameter.Value" \
    --output text > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  log_info ".env.prod fetched from SSM ✓"
fi

# ── 3. Pull image mới từ Docker Hub ──────────────────────────
log_info "Pulling image: $FULL_IMAGE"
docker pull "$FULL_IMAGE"

# ── 4. Export biến để docker-compose đọc ─────────────────────
export BACKEND_IMAGE="$FULL_IMAGE"

# ── 5. Zero-downtime restart ──────────────────────────────────
log_info "Running database migrations..."
docker compose -f "$COMPOSE_FILE" run --rm --no-deps django \
  sh -c "cd src && python manage.py migrate --noinput"

log_info "Collecting static files..."
docker compose -f "$COMPOSE_FILE" run --rm --no-deps django \
  sh -c "cd src && python manage.py collectstatic --noinput"

log_info "Restarting Django container with new image..."
docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate django

# ── 6. Health check ───────────────────────────────────────────
log_info "Waiting for service to become healthy..."
for i in {1..15}; do
  HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout 5 http://localhost:8000/health/ 2>/dev/null || echo "000")

  if [[ "$HTTP_STATUS" == "200" ]]; then
    log_info "Service is healthy after $i attempt(s) ✓"
    break
  fi

  if [[ $i -eq 15 ]]; then
    log_error "Health check failed after 15 attempts!"
    log_error "Container logs:"
    docker compose -f "$COMPOSE_FILE" logs --tail=50 django
    exit 1
  fi

  log_warn "Attempt $i/15: HTTP $HTTP_STATUS – retrying in 10s..."
  sleep 10
done

# ── 7. Reload nginx (nếu có) ─────────────────────────────────
if docker compose -f "$COMPOSE_FILE" ps nginx 2>/dev/null | grep -q "Up"; then
  log_info "Reloading nginx..."
  docker compose -f "$COMPOSE_FILE" exec -T nginx nginx -s reload || true
fi

# ── 8. Dọn dẹp image cũ ──────────────────────────────────────
log_info "Pruning dangling images..."
docker image prune -f

log_info "====================================="
log_info "  Deployment successful! 🚀"
log_info "  Running image: $FULL_IMAGE"
log_info "====================================="
