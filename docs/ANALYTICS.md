# First-party product analytics

Showcase Maker records a small allowlist of product events in its own database. It does not use Google Analytics or another analytics provider.

## Events

| Event | Source | Meaning |
|---|---|---|
| `home_view` | browser, after consent | Landing page visited once per browser session |
| `tool_open` | browser, after consent | A workspace tool was opened |
| `file_added` | browser, after consent | One or more files were selected; only general type, size range and count are sent |
| `process_success` | worker | Processing finished successfully |
| `process_failed` | worker/browser | Processing failed, with a safe reason category |
| `zip_download` | server | A finished result ZIP was downloaded |
| `extension_launch_clicked` | browser, after consent | The Steam-extension upload action was requested |
| `extension_launch_confirmed` | browser, after consent | The installed extension accepted the upload action |
| `registration_success` | server | A new email, Discord, Google, Telegram or Steam account was created |
| `pro_activated` | server | Pro was granted by a code, trial, Gumroad or Stripe |

The analytics table has no columns for IP address, user agent, email, Steam ID, filename or media content. Session and account identifiers are HMAC hashes. Dynamic profile/preview path values are removed before storage.

## Consent and retention

Optional browser events are sent only after the visitor chooses **Allow** in the compact consent banner. The choice is stored in `localStorage`; the random session identifier is stored in `sessionStorage`. Necessary server-side operational events are recorded independently.

Detailed events are deleted automatically after `ANALYTICS_RETENTION_DAYS` (90 by default, allowed range 30–365). Cleanup runs at most once an hour while new events are recorded.

## Dashboard

Open `/admin/analytics`, enter the same `ADMIN_SECRET` configured for the server and choose 7, 30 or 90 days. The secret remains in the current tab's `sessionStorage`. The API returns aggregates only; there is no endpoint that returns raw event rows.

The database table and indexes are created automatically during application startup for both SQLite and PostgreSQL. A normal application/worker rebuild and restart is enough after deployment.
