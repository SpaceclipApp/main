#!/bin/bash

# SpaceClip Setup Script
# This script sets up the development environment

set -e

echo "🚀 Setting up SpaceClip..."
echo ""

# Check for required tools
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install it first."
        exit 1
    fi
    echo "✅ $1 found"
}

echo "Checking dependencies..."
check_command python3
check_command node
check_command npm
check_command ffmpeg

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama not found. Please install from https://ollama.ai"
    echo "   SpaceClip will use fallback highlight detection without Ollama."
else
    echo "✅ Ollama found"
    
    # Pull the model if not present
    if ! ollama list | grep -q "llama3.2"; then
        echo "📥 Pulling llama3.2 model..."
        ollama pull llama3.2
    fi
fi

echo ""
echo "Setting up Backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate and install dependencies
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
mkdir -p uploads outputs

# Create .env if not exists
if [ ! -f ".env" ]; then
    cat > .env << EOF
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
WHISPER_MODEL=base
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
HOST=0.0.0.0
PORT=8000
EOF
    echo "✅ Created backend/.env"
fi

deactivate
cd ..

echo ""
echo "Setting up Frontend..."
cd frontend

# Install npm dependencies
npm install

# Create .env.local if not exists
if [ ! -f ".env.local" ]; then
    cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    echo "✅ Created frontend/.env.local"
fi

cd ..

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start the development servers:"
echo ""
echo "  Terminal 1 (Ollama):"
echo "    ollama serve"
echo ""
echo "  Terminal 2 (Backend):"
echo "    cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "  Terminal 3 (Frontend):"
echo "    cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000 in your browser."





