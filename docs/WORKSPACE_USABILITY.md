# Workspace usability — local implementation, 2026-09-10

The existing theme and encoding pipeline are preserved. No database migration or external service is required.

- `workspace-help.js` moves selected explanatory nodes into accessible question-mark popovers, retaining their existing translation bindings. Translation-owned headings must never contain the button: their text is replaced by the existing i18n scripts. Hover, focus, tap, Escape and outside-click are supported. Errors, empty states and retention limits stay visible.
- `builder-history.js` owns up to 60 editor snapshots, groups typing/slider changes, and handles undo/redo without intercepting native input editing. A draft is written atomically to IndexedDB after edits. It includes media up to 100 MiB, and keeps the last complete draft if storage fails. Restoration is explicit; restored server projects are copies with no server project ID. Blob sources are uploaded again when the user saves to their account. The browser draft is separate from server project retention and is not cross-device storage.
- `process-result.js` displays final archive images with original/result/side-by-side views, fit/native-size output, dimensions, weights and ZIP download. It reuses the Steam readiness report and extension actions for authenticated jobs. Guest jobs also get a visible result screen. Individual GIF playback is browser-controlled, not a timing verification; the existing Sync report verifies the generated files. Only one group's decoded images are retained when switching output groups.
- `/api/process/preview/{job_id}` and `/api/process/preview/{job_id}/{entry_index}` use the same owner checks and expiry as existing Process downloads. They read only allowlisted generated image names from the existing ZIP, never extract arbitrary paths, and bound entry count and decompressed size. Responses are private/no-store. No frame encoding, quality or quota rules change.
- `workspace-copy.js` holds hand-written strings for all eight languages. `check_i18n.js` checks completeness alongside the existing dictionaries. German baseline profile recommendations now have their own server-side copy.

Verification: `python -m pytest -q`, `node scripts/check_i18n.js`, JS syntax checks, and `python scripts/qa_workspace.py` against a local server. Browser QA mocks APIs and covers tooltips, undo/redo, media recovery, integrated results, guest results, mobile layout and language variants. It does not exercise a live Steam extension or a production account.

## Finishing pass — local, 2026-09-10

- Process now has a four-step route: showcase type, settings, files, and result. Steam-safe defaults remain visible while watermark, encoder, all-modes and outline controls live in one expandable advanced section.
- `process-guide.js` is the single browser-side inspection interface. It checks every source locally for supported type, non-empty size, the 40 MB upload cap, decoded dimensions and video duration. Errors block submission; low resolution and video beyond the eight-second Steam window remain explicit warnings.
- The Builder adds three non-destructive decoration templates, per-layer duplicate/lock controls, smart centre/edge snapping, one-pixel or Shift-ten-pixel keyboard movement, and Ctrl/Cmd+D duplication.
- Dark, light and checkerboard edge-check backgrounds are preview-only. They temporarily hide the project background so chromakey fringes are visible; export always forces the real project background.
- Static chromakey frames are cached. Moving video is re-keyed at a bounded refresh rate, and the canvas stops painting while the Builder tab is hidden. Local inspection time and end-to-end Process UI time are measurable without analytics or uploads.
- All new copy is hand-written for EN/RU/DE/TR/FR/UK/ES/PT. The static audit validates manual Builder key parity as well as the generated language packs; browser QA opens all eight routes at mobile width.
