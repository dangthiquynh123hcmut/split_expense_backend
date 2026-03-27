#!/bin/bash

# Setup SSL Certificate with Let's Encrypt
# Usage: ./scripts/setup-ssl.sh yourdomain.com

set -e

DOMAIN=${1:-yourdomain.com}

echo "================================"
echo "Setup SSL Certificate"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ -z "$DOMAIN" ]; then
    log_error "Domain argument required"
    echo "Usage: $0 <domain>"
    exit 1
fi

log_info "Installing Certbot..."
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

log_info "Creating SSL certificate for $DOMAIN..."
sudo certbot certonly --standalone \
    -d "$DOMAIN" \
    -d "www.$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email admin@"$DOMAIN"

if [ $? -eq 0 ]; then
    log_info "SSL certificate created successfully ✓"
    log_info "Certificate location: /etc/letsencrypt/live/$DOMAIN/"

    # Update nginx.conf with correct domain
    log_info "Updating nginx.conf with domain: $DOMAIN"
    sed -i "s/yourdomain.com/$DOMAIN/g" nginx.conf

    log_info "Setting up auto-renewal..."
    sudo tee /etc/cron.d/certbot > /dev/null <<EOF
0 12 * * * root test -x /usr/bin/certbot -a \! -d /run/systemd/system && perl -e 'sleep int(rand(43200))' && certbot -q renew --post-hook "cd $(pwd) && docker-compose restart nginx"
EOF

    log_info "Setup complete!"
    log_info "Your SSL certificate will auto-renew"
else
    log_error "Failed to create SSL certificate"
    exit 1
fi
