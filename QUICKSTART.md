# 🚀 SpaceClip Quick Start Guide

## One-Time Setup

1. **Ensure PostgreSQL is running:**
   ```bash
   pg_isready -h localhost
   # If not running: brew services start postgresql@18
   ```

2. **Set up the database:**
   ```bash
   ./scripts/setup-db.sh
   ```

3. **Install dependencies (if not done):**
   ```bash
   ./scripts/setup.sh
   ```

## Daily Development

### Start Everything (Easiest)
```bash
./scripts/dev.sh
```
This will:
- ✅ Check PostgreSQL
- ✅ Set up database if needed
- ✅ Start Ollama
- ✅ Start backend (port 8000)
- ✅ Start frontend (port 3000)

Open http://localhost:3000 in your browser.

### Stop Everything
```bash
./scripts/kill.sh
```

Or press `Ctrl+C` if using `./scripts/dev.sh`

## Troubleshooting

### "PostgreSQL is not running"
```bash
brew services start postgresql@18
# or
pg_ctl -D /opt/homebrew/var/postgresql@18 start
```

### "Database connection failed"
```bash
# Re-run database setup
./scripts/setup-db.sh
```

### "Port already in use"
```bash
# Kill everything
./scripts/kill.sh

# Or kill specific ports
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### "Docker daemon not running"
**You don't need Docker!** SpaceClip uses local PostgreSQL. Just make sure PostgreSQL is running locally.

## Manual Start (if scripts don't work)

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
export SECRET_KEY="dev-secret-key-12345"
export DATABASE_URL="postgresql+asyncpg://spaceclip:spaceclip@localhost:5432/spaceclip"
export FRONTEND_URL="http://localhost:3000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

## Environment Variables

The `dev.sh` script automatically sets:
- `SECRET_KEY` - Randomly generated if not set
- `DATABASE_URL` - Points to local PostgreSQL
- `FRONTEND_URL` - http://localhost:3000

You can override these by setting them before running `./scripts/dev.sh`:
```bash
export SECRET_KEY="my-secret-key"
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db"
./scripts/dev.sh
```
