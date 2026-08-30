# Smart Upscale patch

Заменить в репозитории:
- `main.py`
- `processor.py`
- `worker.py`
- `app.html`

`requirements.txt` и `redis_store.py` уже совместимы с патчем и менять их не требуется.

## ENV

```env
HF_VIDEO_UPSCALE_SPACE=babaTEEpe/upscale
# existing image Space; can be changed if needed
HF_IMAGE_UPSCALE_SPACE=Phips/Upscaler
# optional fallback image Space
HF_IMAGE_UPSCALE_FALLBACK_SPACE=
# optional HF token for better access/rate limits
HF_TOKEN=

UPSCALE_VIDEO_MAX_SEC=8
UPSCALE_VIDEO_MAX_MB=100
UPSCALE_VIDEO_MAX_PIXELS=8294400
UPSCALE_GIF_FPS=12
UPSCALE_GIF_WIDTH=750
MAX_UPSCALE_JOBS_PER_USER=1
UPSCALE_JOB_TTL=86400
```

## Что теперь работает

- фото: automatic image-model selection;
- видео: MP4/WEBM/MOV/MKV/AVI/M4V;
- видео не длиннее 8 секунд;
- асинхронная job через существующий Redis/worker;
- video upscale через `babaTEEpe/upscale`;
- после upscale автоматическая GIF-конвертация;
- скачивание upscaled video и GIF отдельно;
- видео preview до/после;
- аудио исходного видео сохраняется в итоговом MP4, если оно было;
- результат живёт 24 часа и затем удаляется cleanup-процессом.

## Важно про модель

Для видео supplied Space `babaTEEpe/upscale` используется как основной provider. Endpoint и его параметры определяются через Gradio `view_api()` в runtime. Если Space изменит endpoint name, код не требует ручной правки имени endpoint.

Для изображений по умолчанию сохраняется существующий image Space `Phips/Upscaler`, но выбор модели скрыт от пользователя и выполняется автоматически.
