FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# gifski Linux amd64
RUN curl -fsSL -o /tmp/gifski.deb \
      "https://github.com/ImageOptim/gifski/releases/download/1.32.0/gifski_1.32.0-1_amd64.deb" \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/gifski.deb \
    && rm -f /tmp/gifski.deb \
    && rm -rf /var/lib/apt/lists/* \
    && gifski --version

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Drop Windows-only binaries from image
RUN rm -f /app/bin/ffmpeg /app/bin/ffmpeg.exe /app/bin/ffprobe /app/bin/ffprobe.exe \
         /app/bin/gifski.exe /app/bin/ffplay.exe /app/bin/gifdiff.exe /app/bin/gifsicle.exe 2>/dev/null || true

RUN which ffmpeg && ffmpeg -version | head -1
RUN which gifski && gifski --version

ENV HOST=0.0.0.0
ENV PORT=8080
ENV DATA_DIR=/data
ENV PYTHONUNBUFFERED=1
# Job state and result ZIPs live in the process that produced them, so more than
# one uvicorn worker makes /api/process/status hit a process that never saw the
# job. Raise this only together with an external worker + shared storage.
ENV UVICORN_WORKERS=1
# embedded = process jobs in this container's pool (correct for single-service
# platforms such as Railway). external = a separate `python worker.py` drains Redis.
ENV WORKER_MODE=embedded
ENV MAX_JOB_WORKERS=2

# non-root
RUN useradd -m -u 10001 appuser && mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8080

# default: API (override command for worker)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${UVICORN_WORKERS:-1} --timeout-keep-alive 30
