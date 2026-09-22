# ShowcaseMaker threat model

Last reviewed: 2026-09-22  
Scope: the FastAPI application, classic browser frontend, worker, PostgreSQL,
Redis, nginx, Cloudflare Tunnel/R2 integration and the provider integrations
implemented in this repository. The separately distributed browser-extension
source, provider dashboards and deployed Modal runtime are outside the code
review boundary; their server-facing contracts are included.

## Executive summary

ShowcaseMaker is a public, multi-user media-processing application. Its most
important security boundaries are untrusted uploads and remote URLs entering
media workers, browser sessions crossing the public Cloudflare/nginx boundary,
and privileged admin/provider credentials reaching external services. The
current design has useful layered controls: private Docker networking,
Cloudflare Tunnel, nginx body limits, host/origin validation, HttpOnly secure
cookies, per-route throttles, capability-style job IDs, owner binding, isolated
job directories, output allow-listing and non-public provider credentials.

The highest remaining risks are operational rather than a confirmed exploit:
remote-download workers intentionally fetch user-supplied public URLs and need
an egress boundary that cannot reach private metadata/services; quota checks
across concurrent start routes are not proven atomic; and a release must keep
public API documentation disabled, secrets non-default and backup restoration
tested. These are release gates or monitored residual risks, not evidence that
production has been compromised.

## System and trust boundaries

```text
Untrusted browser / extension
        |
        v
Cloudflare edge + Tunnel  --->  R2 public model/assets
        |
        v
nginx (loopback host port, body/cache/proxy policy)
        |
        v
FastAPI app  <----> PostgreSQL (accounts, durable metadata)
     |       <----> Redis (jobs, quotas, ephemeral coordination)
     |
     +----> worker / FFmpeg / gifski / image decoders
     +----> remove.bg, OAuth, Steam, Resend, Stripe/Gumroad,
            Modal/Groq/DeviantArt and remote media hosts
```

Boundary assumptions verified for the reviewed production topology:

- app, worker, PostgreSQL and Redis are not published directly on the host;
  nginx is bound to loopback and Cloudflare Tunnel is the public path;
- production reports custom PostgreSQL, application and admin secrets as set;
- cookies are HttpOnly, SameSite and secure on HTTPS; unsafe cookie-authenticated
  requests pass origin validation;
- nginx enforces a 100 MB request limit and the app also has request/upload
  limits; direct deployment without nginx is not an equivalent boundary;
- user media and remote content are adversarial even when their extension or
  MIME header appears valid.

## Assets and security objectives

| Asset | Security objective |
| --- | --- |
| Password hashes, OAuth identities, sessions | Prevent account takeover, session theft and cross-account access |
| User uploads, generated jobs and profile/gallery content | Keep private jobs owner-bound; prevent traversal, unsafe publication and unintended retention |
| Admin session and actions | Strong separation from normal accounts; origin checks, auditability and least privilege |
| Provider/API secrets and payment state | Never expose to clients/logs; prevent forged entitlement and uncontrolled paid calls |
| PostgreSQL, Redis, backups and R2 objects | Confidentiality, integrity, bounded retention and recoverability |
| Worker CPU, memory, disk and provider budget | Prevent decompression bombs, queue starvation, quota races and paid-API abuse |
| Public pages and downloads | Prevent stored/reflected script injection, content-type confusion and cache leaks |

## Threats and mitigations

| ID | Threat / abuse path | Impact | Existing evidence and controls | Required or recommended action | Priority |
| --- | --- | --- | --- | --- | --- |
| T1 | Crafted image/video/archive exploits a decoder or exhausts CPU, RAM or disk | Service outage or worker compromise | Upload size/frame/duration limits, asynchronous workers, FFmpeg/gifski pipeline, bounded job directories, nginx body limit | Keep decoders/images current; apply worker CPU/RAM/PID/time limits in production; reject archive expansion above explicit file/byte ceilings | High |
| T2 | Remote URL redirects, DNS rebinding or downloader behavior reaches private services | SSRF, metadata/credential exposure | Initial public-IP validation and candidate revalidation exist | Run remote download in a network policy that blocks loopback, RFC1918, link-local and metadata ranges; validate every redirect/final peer where the downloader permits it | High |
| T3 | Concurrent job starts race quota/active-job checks | Provider-budget loss and noisy-neighbor denial of service | Route throttles, per-user limits and fail-closed provider quota exist | Move admission + quota reservation to one atomic Redis/Lua or DB transaction used by every paid/heavy start route | High |
| T4 | IDOR against jobs, files, retries or cancellations | Cross-user media disclosure/modification | 128-bit job IDs, owner marker/scoped owner checks, 404 for other owners, safe output enumeration | Keep ownership checks centralized; add authenticated multi-user E2E coverage for every file/action route | High |
| T5 | Session theft, CSRF or OAuth state abuse | Account takeover/action forgery | Secure HttpOnly SameSite cookies, origin guard, trusted hosts, state validation, login throttles | Revalidate authentication during long SSE streams; test expiry/revocation during a live stream; keep proxy-hop configuration pinned | Medium |
| T6 | Stored/reflected XSS through profile, gallery, announcement, URL or provider data | Session actions and content tampering | CSP, escaping helpers and textContent usage; avatar rendering changed from HTML concatenation to DOM properties | Continue replacing legacy `innerHTML`; remove CSP `unsafe-inline` after legacy inline handlers/scripts are migrated | Medium |
| T7 | Error responses or logs expose paths, URLs, tokens or provider internals | Information/secret disclosure | Public conversion/download errors are now generic; detailed exceptions remain server-side; secrets are environment-only | Add log redaction tests and avoid raw URL/query/body logging; set production log retention/access policy | Medium |
| T8 | Forged payment webhook, entitlement or extension handoff | Unauthorized Pro access or external action | Signed provider flows and server-side entitlement state are expected; extension uses explicit handoff contracts | Maintain signature/replay tests per provider and an audit entry for every entitlement/admin mutation; verify extension origin/version contracts | High |
| T9 | Admin endpoint misuse or stolen admin cookie | User/content/entitlement manipulation | Dedicated strict cookie path, origin check, short-lived CSRF/session flow and admin audit surfaces | Require strong admin secret rotation process; consider MFA/identity-aware access; alert on unusual admin actions | High |
| T10 | Public API schema/debug surface reveals internals | Easier endpoint reconnaissance | Local release candidate disables docs/OpenAPI unless explicitly enabled | Keep `ENABLE_API_DOCS=0` in production and regression-test `/docs`, `/redoc`, `/openapi.json` as 404 | Medium |
| T11 | Cache serves authenticated/private responses or stale removed files | Privacy leak or re-exposure | `/api/` is `no-store`; static backup suffixes are denied; protected nginx config was validated | Add edge smoke tests after deploy and purge any historically cached sensitive URL explicitly | Medium |
| T12 | Default/weak secrets or exposed data services | Full data compromise | Production PostgreSQL password is custom; DB/Redis live on internal Docker network | Fail startup in production on placeholder secrets; document and test secret rotation; never expose DB/Redis ports | High |
| T13 | Dependency/base-image compromise or known CVE | Application/host compromise | Pinned core Python packages; 2026-09-22 `pip-audit` found no known Python dependency vulnerabilities | Pin deploy images by digest or controlled version, scan built images/SBOM in CI, avoid floating `cloudflared:latest` for reproducible releases | Medium |
| T14 | Backup missing, corrupt or readable by unintended users | Irrecoverable loss or data disclosure | Backup administration exists; no destructive restore was attempted during this audit | Perform a dated restore rehearsal into an isolated database/object prefix; encrypt and restrict backups; measure RPO/RTO | High |
| T15 | Account/profile enumeration and abusive public content | Privacy abuse, harassment or moderation burden | Public/profile/gallery separation, moderation and rate limits exist | Review public fields, delete/export flows and moderation SLAs; avoid leaking email/provider IDs in public responses | Medium |

## Priority abuse cases

1. **Paid background-removal drain.** An attacker creates many sessions or races
   requests before counters settle. The service must atomically reserve quota,
   cap concurrency, charge only accepted work and retain operator-visible audit
   events without logging media or secrets.
2. **Downloader SSRF.** An attacker supplies a public URL that redirects or
   resolves later to `127.0.0.1`, RFC1918 or a cloud metadata address. Input
   validation alone is insufficient; the worker's network must make the target
   unreachable.
3. **Cross-account job access.** An attacker obtains another job ID and tries
   history, SSE, file, retry and cancel endpoints. Every route must derive the
   current owner server-side and return the same not-found result for missing
   and foreign jobs.
4. **Malicious media.** A small upload expands into excessive frames/pixels or
   triggers a native decoder bug. Processing must run outside the web event loop
   with resource/time limits and patched decoders.
5. **Admin/session compromise.** A stolen privileged cookie or forged request
   changes access, content or settings. Strict cookie scope and origin checks
   reduce CSRF; short sessions, audit logs and MFA/identity-aware access reduce
   impact.

## Release verification checklist

- `/docs`, `/redoc` and `/openapi.json` are 404 in production.
- Direct DB/Redis/app ports are not externally reachable; nginx remains
  loopback-only and the Cloudflare Tunnel targets nginx.
- Placeholder secrets cause production startup failure; rotation and emergency
  revocation steps are documented and tested without printing values.
- Authenticated two-user tests prove job/file/profile ownership and admin denial.
- Concurrent tests prove atomic limits for processing, upscale, background
  removal, imports and other paid/provider-backed work.
- Worker resource limits and egress deny rules are observable and tested.
- A backup restores successfully into isolated infrastructure; RPO/RTO and
  retention are recorded.
- Built images and Python dependencies pass vulnerability scanning; current
  media decoders are included in the scan.
- Public browser regression covers desktop/mobile, consent, announcements,
  auth expiry, uploads, error/empty/loading states and extension handoff.

## Residual risk and open questions

- Whether VPS-level firewall/egress rules block private and metadata networks
  was not proven from repository configuration.
- Provider dashboard settings, webhook signing material, Cloudflare WAF/rate
  rules and extension-store builds require operator-side verification.
- Real OAuth, email, payment, remove.bg, Modal/Groq and Steam flows were not
  invoked during this pass to avoid spending quota or changing external state.
- The application still depends on legacy inline frontend code; CSP therefore
  cannot yet be reduced to a nonce/hash-only policy without a staged migration.
- Backup integrity and disaster recovery are not certified until an isolated
  restore rehearsal succeeds.
