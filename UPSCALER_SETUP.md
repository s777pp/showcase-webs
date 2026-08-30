# Smart Upscale

The Upscale tool now supports:

- Images: automatic model selection using the existing image Space.
- Video: up to 8 seconds, processed through `kramp/video-upscaler`.
- Long videos are split into chunks of at most 90 frames because the ZeroGPU Space enforces that per-request limit.
- Inputs are normalized to MP4 and max 1024x1024 before the remote video call, matching the Space's ZeroGPU constraints.
- The upscaled chunks are merged, the original audio is restored when present, and a GIF is generated automatically from the final upscaled video.
- The UI exposes both `Download Video` and `Download GIF`.

## Environment

```env
HF_VIDEO_UPSCALE_SPACE=kramp/video-upscaler
HF_IMAGE_UPSCALE_SPACE=Phips/Upscaler
HF_TOKEN=hf_...
UPSCALE_VIDEO_MAX_SEC=8
UPSCALE_VIDEO_MAX_MB=100
UPSCALE_VIDEO_MAX_PIXELS=8294400
HF_VIDEO_UPSCALE_FACTOR=2.0
HF_VIDEO_UPSCALER_MODEL=R-ESRGAN AnimeVideo
HF_VIDEO_UPSCALE_WORKERS=8
UPSCALE_GIF_FPS=12
UPSCALE_GIF_WIDTH=750
MAX_UPSCALE_JOBS_PER_USER=1
UPSCALE_JOB_TTL=86400
```

`HF_TOKEN` is recommended for public ZeroGPU Spaces because authenticated requests use the token owner's quota rather than the shared anonymous pool.

## Deployment

For the current project architecture, keep `worker.py` enabled in external mode when possible:

```env
WORKER_MODE=external
MAX_JOB_WORKERS=2
```

The API creates an `upscale` job, Redis stores the status, and the worker performs the CPU/FFmpeg + Hugging Face work.

## Important

The video Space currently accepts only short clips per ZeroGPU request. The application therefore chunks an 8-second upload into several requests when necessary. This preserves the full video duration instead of silently reducing the frame rate.
