#!/bin/bash

# Initial Server Setup for Production
# Run this script on a fresh Ubuntu EC2 instance

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

echo "================================"
echo "Server Initial Setup"
echo "================================"

# Update system
log_info "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install basic tools
log_info "Installing basic tools..."
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    htop \
    tmux \
    net-tools \
    build-essential

# Install Docker
log_info "Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Add ubuntu user to docker group
log_info "Adding user to docker group..."
usermod -aG docker ubuntu

# Install Docker Compose
log_info "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Certbot for SSL
log_info "Installing Certbot..."
apt-get install -y certbot python3-certbot-nginx

# Create non-root user for deployment
log_info "Creating deployment user..."
if ! id deploy &>/dev/null; then
    useradd -m -s /bin/bash -G docker deploy
    log_info "User 'deploy' created"
else
    log_info "User 'deploy' already exists"
fi

# Setup security
log_info "Configuring security..."
apt-get install -y fail2ban
systemctl start fail2ban
systemctl enable fail2ban

# Install monitoring tools (optional)
log_info "Installing monitoring tools..."
apt-get install -y prometheus-node-exporter

# Create necessary directories
log_info "Creating necessary directories..."
mkdir -p /opt/split-expense-backend
mkdir -p /backups/database
mkdir -p /var/log/split-expense

# Set permissions
log_info "Setting permissions..."
chown -R ubuntu:ubuntu /opt/split-expense-backend
chown -R deploy:deploy /backups/database
chmod 755 /backups/database

# Setup swap (if needed)
log_info "Checking swap..."
if [ $(free | grep Swap | awk '{print $2}') -eq 0 ]; then
    log_warn "No swap found, creating 2GB swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    log_info "Swap created"
fi

# Cleanup
log_info "Cleanup..."
apt-get autoremove -y
apt-get autoclean -y

log_info "================================"
log_info "Server setup complete!"
log_info "================================"
log_info "Next steps:"
log_info "1. Switch to ubuntu user: su - ubuntu"
log_info "2. Clone the repository"
log_info "3. Create env/.env.prod file"
log_info "4. Run: ./scripts/deploy-prod.sh"
log_info ""
log_info "Setup SSL: ./scripts/setup-ssl.sh yourdomain.com"
