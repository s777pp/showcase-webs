# SteamShowcase — revert to original image-only Upscale

These are the original files from before the video-upscale experiments.
Replace the corresponding files in the repository:

- main.py
- processor.py
- worker.py
- app.html
- requirements.txt (optional; included for consistency)

This restores the original image-only Upscale flow. Video support for the Upscale tool is not included.

If you added these environment variables only for video/Modal/Hugging Face video upscaling, remove them:
- MODAL_VIDEO_UPSCALE_URL
- MODAL_VIDEO_UPSCALE_SECRET
- MODAL_VIDEO_MODEL
- UPSCALE_VIDEO_MAX_SEC
- UPSCALE_VIDEO_MAX_MB
- UPSCALE_VIDEO_MAX_PIXELS
- UPSCALE_GIF_FPS
- UPSCALE_GIF_WIDTH
- MAX_UPSCALE_JOBS_PER_USER
- UPSCALE_JOB_TTL
- HF_VIDEO_UPSCALE_SPACE

Do not remove unrelated Redis/worker variables used by the rest of the site.
