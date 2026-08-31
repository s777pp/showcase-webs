# SteamShowcase cinematic landing

This package replaces the existing landing page only. It does **not** change the FastAPI backend, tools, profile routes or gallery routes.

## Files

- `static/index.html` — new cinematic homepage.
- `static/landing.css` — visual system, responsive layout and motion-friendly styles.
- `static/landing.js` — scroll choreography + mouse parallax.
- `static/img/*.png` — the screenshots supplied for the design.

## Existing routes used

- `/app` — existing Showcase Maker
- `/profile` — existing profile
- `/gallery` — existing gallery

## Install

Copy the files into the repository so that:

```text
static/
  index.html
  landing.css
  landing.js
  img/
    Process.png
    character.png
    steam.png
    deviantart.png
    converter.png
```

The existing FastAPI `/` route already serves `static/index.html`, so `main.py` does not need to be changed.

## Notes

The layout intentionally follows the cinematic reference style:

- sticky 100vh stage
- long scroll timeline
- layered screenshot cards
- smooth mouse parallax
- fade/translate scene transitions
- responsive mobile treatment
- `prefers-reduced-motion` support

The existing product functionality stays on `/app`, `/profile`, and `/gallery`.

Before deploying, test the following:

1. `/`
2. `/app`
3. `/profile`
4. `/gallery`
5. mobile width around 390px
6. desktop 1440px+
