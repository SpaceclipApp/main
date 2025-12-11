#!/bin/bash

# SpaceClip Development Server Script
# Starts all services for local development

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
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

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama is running${NC}"
else
    echo -e "${RED}⚠️  Ollama is not running. Starting it...${NC}"
    ollama serve &
    sleep 3
fi

# Start backend
echo -e "${BLUE}Starting backend...${NC}"
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "Waiting for backend..."
until curl -s http://localhost:8000/health > /dev/null 2>&1; do
    sleep 1
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






