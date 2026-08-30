# Smart Upscale — Nick088 Real-ESRGAN video

Set:

```env
HF_VIDEO_UPSCALE_SPACE=Nick088/Real-ESRGAN_Pytorch
HF_VIDEO_MODEL=
UPSCALE_VIDEO_MAX_SEC=8
UPSCALE_VIDEO_MAX_MB=100
HF_VIDEO_MAX_INPUT_LONG=1280
HF_VIDEO_TIMEOUT=1200
UPSCALE_GIF_FPS=12
UPSCALE_GIF_WIDTH=750
MAX_UPSCALE_JOBS_PER_USER=1
```

Video is detected automatically. The video model is selected automatically (4x for small inputs, 2x for HD+). The original audio is reattached after upscaling. The final GIF is created locally from the upscaled video.

The Space is called through its Gradio `inference_video` endpoint with `2x/4x/8x`.
