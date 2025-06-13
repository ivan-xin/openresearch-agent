#!/bin/bash
echo "Resetting PostgreSQL..."

# Stop all PostgreSQL services
sudo systemctl stop postgresql
sudo pkill -f postgres

# Delete existing cluster
sudo pg_dropcluster --stop 16 main 2>/dev/null || true

# Delete data directory
sudo rm -rf /var/lib/postgresql/16/main

# Recreate cluster
sudo pg_createcluster 16 main

# Start cluster
sudo pg_ctlcluster 16 main start

# Enable auto-start
sudo systemctl enable postgresql

echo "Checking status..."
sudo pg_lsclusters
sudo ss -tlnp | grep 5432

# Set password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '1234qwer';"

# Create database
sudo -u postgres createdb openrearch

echo "Testing connection..."
PGPASSWORD=1234qwer psql -h localhost -p 5432 -U postgres -d openrearch -c "SELECT version();"