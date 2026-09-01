#!/usr/bin/env bash
set -euo pipefail
echo "📦 Extracting frontend files..."
sudo mkdir -p /var/www/mobility-health/frontend-simple
sudo rm -rf /var/www/mobility-health/frontend-simple/*
sudo tar xzf /tmp/frontend.tar.gz -C /var/www/mobility-health/frontend-simple/
if id deployer >/dev/null 2>&1; then
  sudo chown -R deployer:deployer /var/www/mobility-health/frontend-simple
fi
rm -f /tmp/frontend.tar.gz
if [ -f "/var/www/mobility-health/frontend-simple/login.html" ]; then
  echo "✅ Frontend files found"
  echo "📅 File date: $(stat -c %y /var/www/mobility-health/frontend-simple/login.html)"
else
  echo "❌ Frontend files not found!"
  exit 1
fi
echo "✅ Frontend deployment completed!"
