# SpaceClip 🚀

**Transform your podcasts, videos, and X Spaces into viral clips with AI**

SpaceClip is a local-first, privacy-focused media clipping platform that uses AI to identify highlights, generate transcriptions, and create platform-optimized content.

## Features

- 📁 **Multi-source Input**: Upload videos, audio files, or paste URLs from X Spaces, YouTube
- 🤖 **AI-Powered**: Local AI processing with Ollama for highlight detection
- 📝 **Auto-Transcription**: Whisper-powered transcription with speaker detection
- 🎨 **Audiogram Generation**: Beautiful waveform visualizations
- 📱 **Multi-Platform Export**: One-click optimization for Instagram, TikTok, LinkedIn, YouTube Shorts

## Architecture

```
spaceclip/
├── frontend/          # Next.js 14 web application
├── backend/           # Python FastAPI server
│   ├── services/      # Core processing services
│   ├── api/           # API routes
│   └── models/        # Data models
└── shared/            # Shared types and utilities
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- FFmpeg
- Ollama (with llama3.2 or similar model)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Ollama Setup

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.2
ollama serve
```

## Starting and Stopping Servers

### Start Servers

**Option 1: Use the dev script (Recommended)**
```bash
./scripts/dev.sh
```
This starts both backend and frontend automatically. Press `Ctrl+C` to stop all services.

**Option 2: Start manually**

Backend (in one terminal):
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (in another terminal):
```bash
cd frontend
npm run dev
```

### Stop Servers

**If using the dev script:**
- Press `Ctrl+C` in the terminal running the script

**If running manually:**
- Press `Ctrl+C` in each terminal, or
- Kill processes by port:
```bash
# Kill both backend and frontend
lsof -ti:8000,3000 | xargs kill -9

# Or use pkill
pkill -f "uvicorn main:app" && pkill -f "npm run dev"
```

## Environment Variables

Create `.env` files in both `frontend/` and `backend/` directories:

### Backend `.env`
```
OLLAMA_HOST=http://localhost:11434
WHISPER_MODEL=base
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
```

### Frontend `.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## License

MIT





