#!/bin/bash

# SpaceClip Kill Script
# Stops all running SpaceClip services

echo "🛑 Stopping SpaceClip services..."

# Kill backend (uvicorn)
pkill -f "uvicorn main:app" 2>/dev/null && echo "✅ Backend stopped" || echo "   Backend not running"

# Kill frontend (next dev)
pkill -f "next dev" 2>/dev/null && echo "✅ Frontend stopped" || echo "   Frontend not running"

# Kill by ports (fallback)
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null

echo "✅ All services stopped"
