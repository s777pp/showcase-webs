FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# ignore broken Windows binaries in bin/; use apt ffmpeg
RUN rm -f /app/bin/ffmpeg /app/bin/ffmpeg.exe /app/bin/ffprobe /app/bin/ffprobe.exe 2>/dev/null || true
RUN which ffmpeg && ffmpeg -version | head -1

ENV HOST=0.0.0.0
ENV PORT=8080
ENV DATA_DIR=/data
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
