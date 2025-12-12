#!/bin/bash

# SpaceClip Database Setup Script
# Sets up PostgreSQL database without Docker

set -e

echo "🗄️  Setting up SpaceClip database..."

# Check if PostgreSQL is running
if ! pg_isready -h localhost > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not running. Please start it first:"
    echo "   brew services start postgresql@18"
    echo "   or"
    echo "   pg_ctl -D /opt/homebrew/var/postgresql@18 start"
    exit 1
fi

echo "✅ PostgreSQL is running"

# Check if database exists
if psql -h localhost -U $(whoami) -lqt | cut -d \| -f 1 | grep -qw spaceclip; then
    echo "✅ Database 'spaceclip' already exists"
else
    echo "📦 Creating database and user..."
    
    # Create user if it doesn't exist
    psql -h localhost -U $(whoami) -d postgres -c "CREATE USER spaceclip WITH PASSWORD 'spaceclip';" 2>/dev/null || echo "User 'spaceclip' already exists"
    
    # Create database
    psql -h localhost -U $(whoami) -d postgres -c "CREATE DATABASE spaceclip OWNER spaceclip;" || echo "Database creation skipped (may already exist)"
    
    echo "✅ Database 'spaceclip' created"
fi

# Run migrations
echo "🔄 Running database migrations..."
cd backend
source venv/bin/activate

# Set required environment variables for migrations
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-migration}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://spaceclip:spaceclip@localhost:5432/spaceclip}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

alembic upgrade head
deactivate
cd ..

echo ""
echo "✅ Database setup complete!"
echo ""
echo "Connection string:"
echo "  postgresql+asyncpg://spaceclip:spaceclip@localhost:5432/spaceclip"
