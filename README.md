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

## ⚠️ Authentication System Directive

**IMPORTANT: SpaceClip uses an opaque session-token authentication system.**

- Session tokens are stored in the database (`sessions` table)
- Backend verifies tokens by DB lookups, **NOT** by cryptographic claims
- Tokens are generated randomly and validated only server-side

**Do NOT replace the existing session-token system with JWT-based login.**
**Do NOT remove or bypass the sessions table.**
**Do NOT introduce stateless authentication for primary sign-in.**

JWTs may ONLY be introduced later as:
- Optional, separate authentication for enterprise SSO (Google, Azure, Okta, etc.)
- Short-lived access tokens layered on top of existing sessions
- Verification-only tokens issued by external IdPs

**Do NOT convert SpaceClip's internal auth system to JWTs.**
**Opaque DB-backed sessions remain the source of truth.**

See [`docs/AUTH_SYSTEM.md`](docs/AUTH_SYSTEM.md) for detailed architecture documentation.

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

### Prerequisites

1. **PostgreSQL must be running:**
   ```bash
   # Check if running
   pg_isready -h localhost
   
   # If not running, start it:
   brew services start postgresql@18
   # or
   pg_ctl -D /opt/homebrew/var/postgresql@18 start
   ```

2. **Set up the database (first time only):**
   ```bash
   ./scripts/setup-db.sh
   ```
   This creates the `spaceclip` database and user, and runs migrations.

### Start Servers

**Option 1: Use the dev script (Recommended)**
```bash
./scripts/dev.sh
```
This script will:
- Check PostgreSQL is running
- Set up database if needed
- Start Ollama (if not running)
- Start backend with proper environment variables
- Start frontend
- Wait for both to be ready

Press `Ctrl+C` to stop all services.

**Option 2: Start manually**

First, ensure environment variables are set:
```bash
export SECRET_KEY="dev-secret-key-$(openssl rand -hex 16)"
export DATABASE_URL="postgresql+asyncpg://spaceclip:spaceclip@localhost:5432/spaceclip"
export FRONTEND_URL="http://localhost:3000"
```

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

**Quick kill script:**
```bash
./scripts/kill.sh
```

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

## Production Deployment: HTTPS/TLS Configuration

**⚠️ IMPORTANT: Production deployments MUST use HTTPS/TLS.**

SpaceClip requires HTTPS in production for:
- Secure session token transmission
- Cookie security (Secure flag)
- CORS and API security
- Browser security requirements

### Cookie Requirements

In production, cookies (if used) **must** have:
- `Secure` flag: Ensures cookies are only sent over HTTPS
- `SameSite=None`: Required for cross-origin requests (if frontend and backend are on different domains)

The backend automatically sets these flags when `ENVIRONMENT=production`.

### Reverse Proxy Setup

SpaceClip should be deployed behind a reverse proxy (nginx, Caddy, Traefik, etc.) that:
1. Terminates TLS/SSL (handles HTTPS)
2. Proxies API requests to the backend (`/api/*` → `http://backend:8000`)
3. Serves the frontend statically or proxies to Next.js
4. Sets appropriate headers (`X-Forwarded-Host`, `X-Forwarded-Proto`)

### Sample nginx Configuration

Create `/etc/nginx/sites-available/spaceclip`:

```nginx
# Upstream backend service
upstream spaceclip_backend {
    server backend:8000;
}

# Upstream frontend service (if serving via Next.js)
upstream spaceclip_frontend {
    server frontend:3000;
}

# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name spaceclip.io www.spaceclip.io;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name spaceclip.io www.spaceclip.io;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/spaceclip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/spaceclip.io/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Max upload size (for media files)
    client_max_body_size 500M;

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://spaceclip_backend;
        proxy_http_version 1.1;
        
        # Headers for backend to determine public URL
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Serve static files from backend (uploads, outputs)
    location /uploads/ {
        proxy_pass http://spaceclip_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /outputs/ {
        proxy_pass http://spaceclip_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://spaceclip_backend;
        access_log off;
    }

    # Serve frontend (Next.js)
    # Option 1: Proxy to Next.js server
    location / {
        proxy_pass http://spaceclip_frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }

    # Option 2: Serve static files directly (if using static export)
    # location / {
    #     root /var/www/spaceclip-frontend;
    #     try_files $uri $uri/ /index.html;
    # }
}
```

**To enable this configuration:**
```bash
sudo ln -s /etc/nginx/sites-available/spaceclip /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

### Sample Caddyfile

Caddy automatically handles HTTPS with Let's Encrypt. Create `Caddyfile`:

```caddy
# Main domain
spaceclip.io {
    # Redirect www to non-www (or vice versa)
    www.spaceclip.io {
        redir https://spaceclip.io{uri} permanent
    }

    # Logging
    log {
        output file /var/log/caddy/spaceclip.log
        format json
    }

    # Max upload size (for media files)
    request_body_max_size 500MB

    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }

    # Proxy API requests to backend
    reverse_proxy /api/* backend:8000 {
        # Headers for backend to determine public URL
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
        header_up X-Real-IP {remote_host}
        
        # Health check
        health_uri /health
        health_interval 30s
        health_timeout 5s
    }

    # Serve static files from backend
    reverse_proxy /uploads/* backend:8000 {
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
    }

    reverse_proxy /outputs/* backend:8000 {
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
    }

    # Health check endpoint
    reverse_proxy /health backend:8000 {
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
    }

    # Serve frontend (Next.js)
    # Option 1: Proxy to Next.js server
    reverse_proxy frontend:3000 {
        header_up X-Forwarded-Host {host}
        header_up X-Forwarded-Proto {scheme}
        
        # Health check
        health_uri /
        health_interval 30s
        health_timeout 5s
    }

    # Option 2: Serve static files directly (if using static export)
    # root * /var/www/spaceclip-frontend
    # file_server
    # try_files {path} /index.html
}
```

**To run Caddy:**
```bash
# Using Docker
docker run -d \
  --name caddy \
  -p 80:80 -p 443:443 \
  -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy:latest

# Or install and run directly
caddy run
```

### Environment Variables for Production

Ensure your `.env` file includes:

```bash
# Backend
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/spaceclip
FRONTEND_URL=https://spaceclip.io
PUBLIC_API_URL=https://api.spaceclip.io  # Or https://spaceclip.io if same domain
ALLOWED_ORIGINS=https://spaceclip.io,https://www.spaceclip.io

# Frontend
NEXT_PUBLIC_API_URL=https://spaceclip.io  # Or https://api.spaceclip.io if separate
```

### Docker Compose with Reverse Proxy

See [`docker-compose.prod.yml`](docker-compose.prod.yml) for production Docker setup. Uncomment and configure the reverse proxy service (nginx/Caddy) based on your preference.

### Testing HTTPS Locally

For local HTTPS testing, you can use:
- **mkcert**: `mkcert -install` then `mkcert localhost`
- **Caddy**: Automatically handles local HTTPS with self-signed certs
- **nginx with self-signed certs**: Generate with `openssl`

## License

MIT







