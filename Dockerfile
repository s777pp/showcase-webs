FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# gifski Linux amd64 (.deb) — NOT the .tar.xz (that one is macOS → Exec format error)
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

# Windows binaries in bin/ do not run on Linux Railway — use apt ffmpeg + deb gifski
RUN rm -f /app/bin/ffmpeg /app/bin/ffmpeg.exe /app/bin/ffprobe /app/bin/ffprobe.exe \
         /app/bin/gifski.exe 2>/dev/null || true
RUN which ffmpeg && ffmpeg -version | head -1
RUN which gifski && gifski --version

ENV HOST=0.0.0.0
ENV PORT=8080
ENV DATA_DIR=/data
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
