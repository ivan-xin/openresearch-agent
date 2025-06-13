#!/bin/bash
echo "Installing PostgreSQL..."

# Update package list
sudo apt update

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Wait for service to start
sleep 5

# Check service status
sudo systemctl status postgresql

# Check port listening
sudo ss -tlnp | grep 5432

# Set password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '1234qwer';"

# Create database
sudo -u postgres createdb openrearch

# Test connection
echo "Testing connection..."
PGPASSWORD=1234qwer psql -h localhost -p 5432 -U postgres -d openrearch -c "SELECT version();"

echo "PostgreSQL installation completed!"
