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



