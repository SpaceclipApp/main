#!/bin/bash

# SpaceClip Development Server Script
# Starts all services for local development

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting SpaceClip Development Environment${NC}"
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo -e "${BLUE}Shutting down...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check PostgreSQL
if ! pg_isready -h localhost > /dev/null 2>&1; then
    echo -e "${RED}❌ PostgreSQL is not running${NC}"
    echo -e "${YELLOW}   Start it with: brew services start postgresql@18${NC}"
    exit 1
fi
echo -e "${GREEN}✅ PostgreSQL is running${NC}"

# Check if database exists, if not run setup
if ! psql -h localhost -U $(whoami) -lqt | cut -d \| -f 1 | grep -qw spaceclip; then
    echo -e "${YELLOW}⚠️  Database not found. Running setup...${NC}"
    ./scripts/setup-db.sh
fi

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama is not running. Starting it...${NC}"
    ollama serve &
    sleep 3
fi

# Set environment variables
export SECRET_KEY="${SECRET_KEY:-dev-secret-key-$(openssl rand -hex 16)}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://spaceclip:spaceclip@localhost:5432/spaceclip}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

# Start backend
echo -e "${BLUE}Starting backend...${NC}"
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "Waiting for backend..."
MAX_WAIT=30
WAIT_COUNT=0
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
        echo -e "${RED}❌ Backend failed to start${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ Backend running on http://localhost:8000${NC}"

# Start frontend
echo -e "${BLUE}Starting frontend...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
sleep 5
echo -e "${GREEN}✅ Frontend running on http://localhost:3000${NC}"

echo ""
echo -e "${GREEN}🎉 SpaceClip is ready!${NC}"
echo -e "   Open ${BLUE}http://localhost:3000${NC} in your browser"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for processes
wait







