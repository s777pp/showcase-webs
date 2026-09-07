# Privacy release / Chrome Web Store resubmission

Prepared 2026-09-07. Local changes only; not yet pushed or deployed.

## Deliverables

- Public policy: `https://showcasemaker.com/privacy` (English default),
  `https://showcasemaker.com/privacy?lang=ru` (Russian).
- Both are full server-served documents, no JavaScript/login required.
- Website links: landing footer, Tools footer, shared profile footer. The full-screen
  gallery has no existing footer; do not inject a normal-flow footer over its canvas.
- Extension: `C:\Users\n1t1337\Downloads\0.9.8`, manifest now **0.9.9**.
  Localized popup link sits immediately above `SteamShowcase Helper · n1t1337`.
- Original backup: `C:\Users\n1t1337\Downloads\SteamShowcase-Helper-0.9.8-before-privacy.zip`.
- New upload package: `C:\Users\n1t1337\Downloads\SteamShowcase-Helper-0.9.9-privacy.zip`.
  Extension sources/archives are outside this repository; deploy them separately.

## Audit evidence / limitations

Inspected extension manifest, background bridge, profile collector, Browser Engine,
popup/storage, network and preview credential/storage code, plus site import handler.

- `background.js:captureAndUpload`: sends SteamID/profile snapshot to the approved
  site with an ImportTicket; user initiates this from the website editor.
- `content-profile-import.js:collectProfile`: URL, name, realname, summary, status,
  level, media URLs, frame/background, badges, awards, groups, stats and showcases.
- `preview_elems/preview.js:getApiKey`: reads Steam page loyalty_webapi_token;
  catalog calls send it to api.steampowered.com, not Showcase Maker.
- `browser-engine.js`: in-browser file decoding/canvas/GIF/ZIP, no fetch upload.
- `sshUploadFlow` persists filename/dimension/order metadata, not local file bytes.
- Preview snapshots use Steam-origin localStorage and can survive uninstall.
- `smweb/routers/profile.py:api_profile_extension_import`: stores account snapshot,
  can enrich from Steam and cache avatar to R2 or local DATA, updates name/avatar.
- Website AI/media services are separate optional flows, not automatic extension
  telemetry. Groq is the website support provider, NOT xAI Grok.
- No claim of blanket seven-day deletion, encrypted-at-rest infrastructure audit,
  or guaranteed zero provider retention. Production log/backup rotation and R2
  lifecycle settings were not inspected; do not fabricate those settings.
- The policy is a truthful technical disclosure, not a guarantee of legal/store
  approval. The operator must keep contact routes usable, honour deletion requests
  and Limited Use commitments, and supply formal operator details where required.

## 1. Publish website code

PowerShell, only after reviewing `git diff` and `git status --short`:

```powershell
cd "C:\Users\n1t1337\Documents\Codex\showcasemaker-current"
git diff --check
git add AGENTS.md PRIVACY_RELEASE.md smweb/routers/pages.py static/privacy-en.html static/privacy-ru.html static/css/privacy.css static/ss.css static/ss-shell.js static/index.html static/app.html static/gallery.html static/profile.html static/profile-view.html tests/test_privacy_page.py
git diff --cached --stat
git commit -m "Add bilingual privacy policy and site footer links"
git push origin main
```

Do not use `git add .`: `data/steam_cache.json` was already modified and is runtime
data. If push is rejected, fetch/review divergence; do not force-push.

## 2. VPS rollout

No migrations, secrets or dependencies changed. Rebuild only app for the new page
route and HTML; nginx already mounts static files. Do not run `down -v`.

```bash
cd /opt/showcasemaker
git rev-parse HEAD
git status --short
git pull --ff-only origin main
sudo docker compose config --quiet
sudo docker compose up -d --build --no-deps app
sudo docker compose ps
sudo docker compose exec -T app curl -fsS http://127.0.0.1:8080/api/ready
sudo docker compose exec -T app curl -fsS 'http://127.0.0.1:8080/privacy?lang=en' | head -c 250
sudo docker compose logs --since=5m --tail=80 app
```

Run steps individually; stop if pull/build/config checks fail. Preserve `.env`,
production Compose overrides, volumes and backup files. Allow startup to complete
before health checks. No worker, Modal or R2 deployment is needed for this release.

## 3. Cloudflare / public checks

Existing root-domain tunnel routes to nginx, so no new DNS record, tunnel, Worker
or R2 bucket is required. Do not change lifecycle rules for this policy release.

- Open `/privacy` and `?lang=ru` in a signed-out/incognito browser: both must show
  full text, HTTP 200, working RU/EN navigation and no login/Access gate.
- If an old 404/page is cached, purge only the affected policy/page URLs. Static
  CSS/JS references have new version query strings.
- If a specific Cloudflare Access/WAF rule blocks the policy, adjust the narrow
  public policy path as appropriate; do not disable protection site-wide.
- Verify footer links on the home page, Tools and profile. Test RU and EN.

## 4. Extension QA and upload

Load/reload the local folder unpacked in Chrome; manifest must show 0.9.9. Open
popup, scroll to bottom, check RU/EN link text and destination. Public URLs will
work only after the website deployment. Smoke-test one existing Steam tool.

Upload `SteamShowcase-Helper-0.9.9-privacy.zip` to the EXISTING item
`nopmeakgeongafdhgmlpllalpcfpedej`, not a new listing. Manifest is at ZIP root.
Do not upload the original backup ZIP. Website deployment cannot update installed
extensions; the Chrome Web Store review/distribution is a separate step.

## 5. Chrome Web Store Privacy practices

**Required field:** Privacy policy URL = `https://showcasemaker.com/privacy`.
Pasting it only into the description or ZIP does not fix Purple Nickel.

Single purpose (English, ready to adapt/paste):

> Help users prepare and preview Steam profile showcases and upload their selected
> media to Steam, with optional user-initiated profile import into Showcase Maker.

Permission justifications:

- **scripting:** Inject packaged scripts into supported Steam pages to configure
  upload fields, provide profile previews and capture a requested profile.
- **activeTab:** Access the current tab when the user invokes a Steam helper tool.
- **tabs:** Find an existing Steam profile tab and open/follow the relevant Steam
  profile, upload and showcase-selection pages; read their URLs/titles as needed.
- **storage:** Save local language/theme preferences, preview configuration and
  filename/order/progress metadata for guided uploads.
- **Host access:** steamcommunity.com for the on-page helpers; showcasemaker.com
  and www.showcasemaker.com for the constrained integration and requested import.
  localhost/127.0.0.1 entries support the local development website. These remain
  in the provided source; if the reviewer flags them, prepare/test a production
  manifest without local-development access rather than claiming it is unused
  production functionality. Do not add wildcard access.

Data declarations must reflect BOTH local handling and import. Do not certify
"no user data" merely because local Browser Engine has no upload endpoint.
Compare the current dashboard's category definitions to these actual data types:

- Personally identifiable information: SteamID, profile display/real name and
  profile URL imported at the user's request.
- Website content: profile/showcase text and media URLs, selected media/preview.
- Authentication information: Steam page token used with Steam API, and a
  single-use Showcase Maker import ticket. No password export to the website.
- Web history/URLs: relevant Steam/site URLs are accessed to implement the tools;
  no general browsing-history collection. Describe this narrow scope if the
  dashboard category includes accessed page URLs.
- Do not add health, financial, precise location or private correspondence
  declarations merely because these categories exist; the extension is distinct
  from optional website payment/support flows.

Check Limited Use certifications only after confirming you follow them. The
extension executes bundled scripts, not downloaded JavaScript; fetching catalog
JSON or images is not by itself executing remotely hosted code.

Suggested reviewer note:

> The Purple Nickel issue has been addressed by publishing a publicly accessible
> privacy policy at https://showcasemaker.com/privacy and entering that URL in the
> dedicated Privacy practices field. Version 0.9.9 also adds a localized policy
> link to the popup footer. The policy discloses local processing/storage, Steam
> API access and user-initiated profile import into Showcase Maker. No new browser
> permissions were added in this update.

Save and resubmit after the PUBLIC URL works. Review may reveal other issues;
the change addresses the specific missing-URL rejection, not guaranteed approval.

Official references:

- https://developer.chrome.com/docs/webstore/cws-dashboard-privacy
- https://developer.chrome.com/docs/webstore/program-policies/user-data-faq

## Verification

```powershell
py -m unittest discover -s tests -p "test_*.py"
py -m py_compile smweb/routers/pages.py
node --check static/ss-shell.js
node --check "C:\Users\n1t1337\Downloads\0.9.8\popup.js"
node scripts/check_i18n.js
git diff --check
```

At implementation: 59 Python tests pass (3 policy tests); JS syntax and RU/EN
checks pass. Anonymous local HTTP and browser policy language/link checks pass.
Actual CWS submission, VPS rollout and installed-extension smoke test are manual.
