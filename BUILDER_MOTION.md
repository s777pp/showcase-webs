# Builder motion experiment

Implemented locally on 2026-09-13. No GitHub push or VPS deployment was performed.

## Where to find it

Open Tools → Builder. Expand **Scene motion** above the canvas. Select an effect or a static media layer to see its additional inspector controls. New copy is supplied in EN/RU/DE/TR/FR/UK/ES/PT.

- **Scene intensity** changes linked effects' speed/density, artistic light and local animation amplitude. It does not change layer position, scale, rotation or opacity. A layer can opt out with its intensity-link switch. The baseline is 50.
- **Effect depth** places an effect behind characters, in front, or in both planes. Background layers form the background plane when depth is enabled; titles and frames stay readable above foreground weather. The mixed setting uses separate smaller/softer distant and larger near passes.
- **Protected area**: enable the effect's protection brush, drag a rectangle on the canvas and finish painting. It suppresses foreground particles inside that region with a softened boundary. This is manual protection, not face detection.
- **Effect light**: enable it and adjust colour, radius and strength. Lightning light uses the same pulse timing as the lightning texture; other effects use a gentle pulse. This is a screen-blended artistic treatment, not relighting reconstructed 3D geometry.
- **Local motion**: select a static image, expand the experimental section, paint a small region, add fixed pins if needed, then press Done. Direction and strength affect that region only. Eraser/clear remove the painted motion. Small amplitudes work best for hair, cloth and water; this is lightweight masked deformation, not AI video generation. Animated GIF/video layers keep their original animation rather than receiving this brush deformation.
- **Steam gaps**: the switch simulates narrow cut gaps in the preview and adds horizontal-position snap targets at the Workshop/Split cuts. Those black preview strips are not baked into exported media. Keyboard movement and ordinary smart guides remain available.
- **Loop**: select Crossfade or Forward/backward, duration and (for Crossfade) overlap. Preview join renders a real joined clip and plays around its end/start boundary. Crossfade consumes overlapping time, so its result can be shorter than the selected duration when the source does not include extra tail frames. Neither method can make arbitrary moving subjects perfectly continuous; Crossfade can show ghosting, and Forward/backward deliberately reverses motion.

## Export and access

Ordinary Builder export retains the existing authenticated Free/Pro quota. Animated seamless export and the rendered join preview use the existing **Pro-only** `/api/loop/start` endpoint. They do not bypass its authentication, limits or owner-only downloads. No new subscription rules were added.

The browser records the complete scene once, then the loop worker builds one shared timeline. Process subsequently cuts that whole clip using its unchanged synchronized Workshop/Split encoding path. There is no separate looping, FPS fitting or quality fitting per panel. The MP4 loop intermediate uses the existing H.264 encoder settings; final GIF output still uses gifski.

The live canvas previews procedural/brush motion with the selected loop clock. GIF/video playback is not sought/reversed by the live canvas; use **Preview join** to inspect their actual joined result. Recording takes approximately eight seconds, followed by worker processing. New depth/light/brush passes add browser rendering work; brush processing is capped at 1024 pixels on the longest side and masks are cached. No claim is made that performance is unchanged on weak devices.

Motion settings, protected regions, painted strokes and pins are validated and saved with projects and included in local history/drafts. Switching intensity does not destructively rewrite layers. While recording/exporting, canvas controls are disabled to keep the scene stable.

## Local verification

```powershell
python -m unittest discover -s tests -v
node scripts/check_i18n.js
node --check static/js/builder-motion.js
node --check static/js/builder-motion-copy.js
node --check static/js/showcase-builder.js
node --check static/js/seamless-loop.js
git diff --check
```

At implementation time: 104 tests passed, including GIF and MP4 sources, both loop methods, both GIF and MP4 outputs, API mode validation and the Pro gate. Browser checks covered effect controls, the static brush/pins and a 390px viewport without document-level horizontal overflow. The authenticated Builder-record → worker → Process flow still needs a manual check on a real Pro account; API and worker tests do not replace that check.

Suggested manual acceptance:

1. Put a character over a background. Add petals; compare Back, Front and Mixed, including adding a background after the effect.
2. Protect a face/title rectangle. Confirm distant particles remain visible and foreground particles avoid it.
3. Add lightning and turn on its light. Confirm flash timing, then disable intensity linking and change global intensity.
4. Paint a static image region, pin its edge and finish. Try undo/redo, save/reopen and duplicated/locked layers.
5. Switch all three Steam layouts and move a layer near a cut. Confirm gaps never influence vertical-position snapping.
6. With Pro, render both join methods on GIF/video. Inspect the actual end/start, send it to Process, download the ZIP and confirm related panels stay synchronized.
7. With Free, confirm regular export remains available within quota and seamless export is rejected without charging a Builder export reservation.
8. Check narrow screens and longer FR/DE labels; ensure controls wrap instead of widening the document.

## Files and deployment notes

`builder-motion.js` is the scene/brush/depth module, `builder-motion-copy.js` owns its eight-language copy, and `builder-motion.css` is scoped to the Builder. `showcase-builder.js` supplies the adapter and export integration. Saved-project validation lives in `smweb/routers/builder.py`; looping lives in `smweb/routers/seamless_loop.py` and `smweb/loop_jobs.py`.

If this experiment is approved later, deploy both app and worker changes together, with updated static cache keys. No database migration or additional model/API key is required. Do not publish the runtime `data/steam_cache.json` change produced by local startup as part of this feature.
