# Multi-stage build for production
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim AS runner

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r spaceclip && useradd -r -g spaceclip -u 1000 spaceclip

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/spaceclip/.local

# Copy application code
COPY --chown=spaceclip:spaceclip . .

# Create upload and output directories with proper permissions
RUN mkdir -p uploads outputs && \
    chown -R spaceclip:spaceclip uploads outputs

# Add local bin to PATH for non-root user
ENV PATH=/home/spaceclip/.local/bin:$PATH

# Switch to non-root user
USER spaceclip

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]





