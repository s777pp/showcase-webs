# File-first Process and Builder workspace

## Interaction model

- Process starts with a file, then an illustrated Steam showcase choice, then
  preparation and download. Appearance/quality controls remain available in a
  closed disclosure with their original defaults.
- Builder separates adding elements (left), composition (centre), and the layer
  list/selected element settings (right). Empty states explain the first action.
- The mobile layout becomes linear, with Add / Canvas / Edit shortcuts for the
  Builder. Controls have keyboard focus styles; upload and layer selection work
  from the keyboard. Reduced motion is respected.
- New interface copy covers EN/RU/DE/TR/FR/UK/ES/PT. Existing processing IDs,
  state, upload/export handlers and API contracts are preserved.

Presentation files: `static/css/workspace-editor.css`,
`static/js/workspace-editor.js`, `static/js/workspace-editor-copy.js`.
The frontend-design skill informed the consistent SVG icon set, hierarchy and
progressive disclosure; this is not a replacement of the media pipeline.

## Verification

Run the repository's local static QA server (including the `/<lang>/app` mapping)
on port 8091, or set `QA_BASE_URL`, then:

```powershell
python scripts/qa_workspace.py
python scripts/qa_workspace_editor.py
$env:PYTHONPATH='.'
python -m pytest -q tests/test_process_preview.py tests/test_builder_projects.py tests/test_builder_motion.py
node --test tests/builder-motion.test.js
node scripts/check_i18n.js
```

Browser tests use mocked APIs, not production accounts or paid processing.
They check keyboard upload, validation, rotation, submitted encoder/FPS/mode,
the ZIP result UI, Builder hand-off, and overflow in eight languages at
360/768/1440/2328 px. They do not constitute a live server render/ZIP-download test.
Screenshots go to the system temporary directory (`showcase-editor-*.png`).

The global i18n audit currently reports seven pre-existing English literals
missing from each extra-language pack (including console diagnostics). Running
the HEAD version of both the checker and its inputs reproduces the same list;
the new workspace dictionary adds no missing translations.

No backend, codec, subscription, storage or database changes are included.
This work is local until separately committed and deployed. HTML and changed
frontend cache keys use `20260920-editor1`.

## Wide workspace follow-up

The Process/Builder workspace now uses the available desktop width instead of
the 1560px cap. Builder side panels and the canvas are larger on wide screens.
Steam backgrounds open inside the centre panel with large, uncropped previews,
visible names and a bounded scrolling grid. Selecting an item returns to the
canvas; Escape closes the catalogue and returns keyboard focus to its opener.
New catalogue labels cover all eight languages. The relevant frontend cache
keys are bumped to `20260920-editor2`.

Catalogue browser QA uses local image fixtures, checks thumbnail width at
360/768/1440/1920/2328 px, selection, Escape and focus return. It does not call
Steam or change the catalogue's API/data source.
