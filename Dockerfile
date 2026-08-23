FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# gifski (Linux x86_64) — high-quality GIF encoder
RUN curl -fsSL -o /tmp/gifski.tar.xz \
      "https://github.com/ImageOptim/gifski/releases/download/1.32.0/gifski-1.32.0.tar.xz" \
    && tar -xJf /tmp/gifski.tar.xz -C /tmp \
    && GIFSKI_BIN="$(find /tmp -type f -name gifski | head -1)" \
    && test -n "$GIFSKI_BIN" \
    && mv "$GIFSKI_BIN" /usr/local/bin/gifski \
    && chmod +x /usr/local/bin/gifski \
    && rm -rf /tmp/gifski* \
    && gifski --version

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# ignore broken Windows binaries in bin/; use apt ffmpeg
RUN rm -f /app/bin/ffmpeg /app/bin/ffmpeg.exe /app/bin/ffprobe /app/bin/ffprobe.exe 2>/dev/null || true
RUN which ffmpeg && ffmpeg -version | head -1
RUN which gifski && gifski --version

ENV HOST=0.0.0.0
ENV PORT=8080
ENV DATA_DIR=/data
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
