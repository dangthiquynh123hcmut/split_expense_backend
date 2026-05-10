#!/bin/bash
# terraform/userdata.sh
# EC2 User Data – chạy 1 lần khi instance được tạo lần đầu

set -euo pipefail

# ── 1. Cài Docker ─────────────────────────────────────────────
apt-get update -y
apt-get install -y curl git awscli

curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Docker Compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ── 2. Tạo thư mục project ────────────────────────────────────
PROJECT_DIR="/opt/split-expense-backend"
mkdir -p "$PROJECT_DIR"
chown -R ubuntu:ubuntu "$PROJECT_DIR"

# ── 3. Clone repository ───────────────────────────────────────
sudo -u ubuntu git clone \
  "https://github.com/${github_repo}.git" \
  "$PROJECT_DIR" || true

# ── 4. Fetch .env.prod từ SSM Parameter Store ─────────────────
# Retry vài lần vì IAM role có thể chưa active ngay
mkdir -p "$PROJECT_DIR/env"
for i in 1 2 3 4 5; do
  if aws ssm get-parameter \
      --region ap-southeast-1 \
      --name "/split-expense/prod/env" \
      --with-decryption \
      --query "Parameter.Value" \
      --output text > "$PROJECT_DIR/env/.env.prod" 2>/dev/null; then
    chmod 600 "$PROJECT_DIR/env/.env.prod"
    echo "OK .env.prod fetched from SSM (attempt $i)"
    break
  fi
  echo "Attempt $i: SSM not ready yet, retrying in 10s..."
  sleep 10
done
chown -R ubuntu:ubuntu "$PROJECT_DIR"

# ── 5. Cài SSM agent (để GitHub Actions dùng SSM Run Command) ─
snap install amazon-ssm-agent --classic
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
systemctl start  snap.amazon-ssm-agent.amazon-ssm-agent.service

# ── 6. Swap (t3.small chỉ có 2GB RAM) ────────────────────────
if [ $(free | grep Swap | awk '{print $2}') -eq 0 ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "EC2 user data setup complete – .env.prod fetched from SSM automatically"
