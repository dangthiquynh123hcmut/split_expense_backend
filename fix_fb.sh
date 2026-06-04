#!/bin/bash
# ============================================================
# Fix Firebase credentials on EC2 and restart Docker Compose
# Run via SSM Send Command hoặc SSH vào EC2
# ============================================================
set -euo pipefail

PROJECT_DIR="/opt/split-expense-backend"
FIREBASE_FILE="${PROJECT_DIR}/firebase.json"
SSM_PARAM="/split-expense/prod/firebase"
REGION="ap-southeast-1"

echo "=== Fix Firebase Credentials ==="
echo "  Project dir: $PROJECT_DIR"

# ── 1. Down containers ─────────────────────────────
echo "[1] Stopping containers..."
cd "$PROJECT_DIR"
docker compose -f docker-compose.prod.yml down 2>/dev/null || true

# ── 2. Remove old firebase.json (could be a directory or invalid file) ──
echo "[2] Removing old firebase.json..."
rm -rf "$FIREBASE_FILE"

# ── 3. Fetch firebase credentials from SSM ─────────
echo "[3] Fetching Firebase credentials from SSM ($SSM_PARAM)..."
aws ssm get-parameter \
    --region "$REGION" \
    --name "$SSM_PARAM" \
    --with-decryption \
    --query "Parameter.Value" \
    --output text > "$FIREBASE_FILE"

# ── 4. Validate ────────────────────────────────────
SIZE=$(wc -c < "$FIREBASE_FILE")
echo "[4] File size: $SIZE bytes"

if [ "$SIZE" -lt 10 ]; then
    echo "ERROR: firebase.json is too small ($SIZE bytes) — SSM parameter may be empty!"
    echo "First 50 chars:"
    head -c 50 "$FIREBASE_FILE"
    echo ""
    echo "FIX: Run upload-firebase-to-ssm.ps1 from your local machine to populate the SSM parameter."
    exit 1
fi

# Validate JSON structure
if ! python3 -c "import json; json.load(open('$FIREBASE_FILE'))" 2>/dev/null; then
    echo "ERROR: firebase.json is not valid JSON!"
    echo "Content preview:"
    head -c 200 "$FIREBASE_FILE"
    echo ""
    exit 1
fi

echo "  JSON valid ✓"
chmod 600 "$FIREBASE_FILE"

# ── 5. Restart containers ──────────────────────────
echo "[5] Starting containers..."
docker compose -f docker-compose.prod.yml up -d 2>&1

# ── 6. Wait and check ──────────────────────────────
echo "[6] Waiting for Django to become healthy..."
sleep 10

# Check container status
echo "Container status:"
docker ps --filter "name=split_expense" --format "table {{.Names}}\t{{.Status}}"

# Show recent logs
echo ""
echo "=== Django logs (last 10 lines) ==="
docker logs split_expense_backend_prod 2>&1 | tail -10 || echo "(container not running yet)"

echo ""
echo "=== Nginx logs (last 5 lines) ==="
docker logs split_expense_nginx 2>&1 | tail -5 || echo "(container not running yet)"

echo ""
echo "=== Done ==="
echo "Check: curl -I http://localhost:8000/health/"
