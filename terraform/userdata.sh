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

# ── 4. Cài SSM agent (để GitHub Actions dùng SSM Run Command) ─
snap install amazon-ssm-agent --classic
systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
systemctl start  snap.amazon-ssm-agent.amazon-ssm-agent.service

# ── 5. Swap (t3.small chỉ có 2GB RAM) ────────────────────────
if [ $(free | grep Swap | awk '{print $2}') -eq 0 ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "EC2 user data setup complete – waiting for .env.prod to be placed before deploying"
