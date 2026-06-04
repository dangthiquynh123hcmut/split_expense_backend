#!/bin/bash

set -euxo pipefail

LOG_FILE="/var/log/userdata.log"
exec > >(tee -a "$${LOG_FILE}") 2>&1

echo "===== USER DATA START ====="

# =====================================================
# Update OS
# =====================================================

apt-get update -y

apt-get install -y \
    curl \
    git \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release

# =====================================================
# Install Docker
# =====================================================

curl -fsSL https://get.docker.com | sh

systemctl enable docker
systemctl start docker

usermod -aG docker ubuntu

docker --version

# =====================================================
# Install Docker Compose v2
# =====================================================

mkdir -p /usr/local/lib/docker/cli-plugins

curl -SL \
    https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose

chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

docker compose version || true

# =====================================================
# Install AWS CLI v2
# =====================================================

cd /tmp

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" \
    -o "awscliv2.zip"

unzip -q awscliv2.zip

./aws/install --update

/usr/local/bin/aws --version

ln -sf /usr/local/bin/aws /usr/bin/aws

aws --version

# =====================================================
# Install SSM Agent (only if missing)
# =====================================================

if ! systemctl status amazon-ssm-agent &> /dev/null; then
    snap install amazon-ssm-agent --classic
    systemctl enable snap.amazon-ssm-agent.amazon-ssm-agent.service
    systemctl restart snap.amazon-ssm-agent.amazon-ssm-agent.service
fi

# =====================================================
# Project directory
# =====================================================

PROJECT_DIR="/opt/split-expense-backend"

mkdir -p "$${PROJECT_DIR}"

chown -R ubuntu:ubuntu "$${PROJECT_DIR}"

# =====================================================
# Clone repository (using Terraform var)
# =====================================================

if [ ! -d "$${PROJECT_DIR}/.git" ]; then
    sudo -u ubuntu git clone \
        "https://github.com/${github_repo}.git" \
        "$${PROJECT_DIR}"
fi

# =====================================================
# Fetch ENV from Parameter Store
# =====================================================

mkdir -p "$${PROJECT_DIR}/env"

for i in 1 2 3 4 5; do
    if aws ssm get-parameter \
        --region ap-southeast-1 \
        --name "/split-expense/prod/env" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text \
        > "$${PROJECT_DIR}/env/.env.prod"
    then
        chmod 600 "$${PROJECT_DIR}/env/.env.prod"
        echo "Fetched .env.prod successfully"
        break
    fi

    echo "Attempt $${i}: waiting IAM role propagation..."
    sleep 10

    if [ $i -eq 5 ]; then
        echo "ERROR: Failed to fetch .env.prod after 5 attempts"
        exit 1
    fi
done

# Fetch DATABASE_URL (RDS connection string) from SSM
for i in 1 2 3 4 5; do
    if DB_URL=$(aws ssm get-parameter \
        --region ap-southeast-1 \
        --name "/split-expense/prod/database-url" \
        --with-decryption \
        --query "Parameter.Value" \
        --output text 2>/dev/null)
    then
        # Append to .env.prod (DATABASE_URL sẽ override nếu đã có)
        if grep -q "^DATABASE_URL=" "$${PROJECT_DIR}/env/.env.prod"; then
            sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$${DB_URL}|" "$${PROJECT_DIR}/env/.env.prod"
        else
            echo "DATABASE_URL=$${DB_URL}" >> "$${PROJECT_DIR}/env/.env.prod"
        fi
        echo "Fetched DATABASE_URL from SSM successfully"
        break
    fi

    echo "Attempt $${i}: waiting for DATABASE_URL SSM parameter..."
    sleep 10

    if [ $i -eq 5 ]; then
        echo "WARNING: Failed to fetch DATABASE_URL — app will fail to connect to DB"
    fi
done

chown -R ubuntu:ubuntu "$${PROJECT_DIR}"

# =====================================================
# Create Swap (2GB)
# =====================================================

if [ "$(free | awk '/Swap:/ {print $2}')" = "0" ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# =====================================================
# Verification
# =====================================================

echo "===== VERIFY ====="

aws --version || true
docker --version || true
docker compose version || true
systemctl status docker --no-pager || true

echo "===== USER DATA COMPLETE ====="
