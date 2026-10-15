# ARCHITECTURE

## Stack
Python 3.14, FastAPI 0.143, uvicorn, python-multipart, pikepdf 10.17 (qpdf), SQLite (stdlib) or
Postgres via psycopg 3.3 (`DATABASE_URL`), SMTP via stdlib smtplib.
Frontend: one static page, vanilla JS, no build. Tests: pytest + httpx TestClient.

## Files
| Path | Job |
|---|---|
| `audit.py` | Pure domain logic: 11 checks, score, quote. No web/IO imports. Constants at top. |
| `app.py` | FastAPI app: pages, API, `/r/<id>`, `/admin`, robots/sitemap, rate limits, headers, JSON logs. |
| `store.py` | `connect()` for SQLite or Postgres with one call shape (`?` placeholders); `migrate()` on startup. |
| `mailer.py` | Lead emails (owner + fixed-text buyer confirmation) over SMTP. |
| `static/index.html`, `privacy.html` | Pages; `{{CONTACT_EMAIL}}`, `{{HEAD}}`, `{{ANALYTICS_NOTE}}` filled per request. |
| `static/app.js` · `style.css` · `404.html` · `favicon.svg` · `fonts/` | Behavior, light/dark styles, not-found page, icon, font. |
| `render.yaml` | Render blueprint listing every setting. |
| `leads.py` | CLI that prints leads joined to their audits. |
| `test_app.py` | Builds PDFs with pikepdf and tests every rule plus the API. |
| `samples/` | Demo PDFs. `research/` market notes (not code). |

## Data (SQLite `leads.db` or Postgres, created on startup)
- `audits(id TEXT PK uuid, created_at, filename, pages, scanned_pages, score, quote_low, quote_high, failed_checks csv, result json)`
  (`result` is NULL for audits made before share links; Postgres uses timestamptz, numeric(10,2), CHECKs)
- `leads(id INTEGER PK, created_at, audit_id → audits.id, name, email lowercased, organization, message)`
  with unique index `(audit_id, email)`; a re-send updates that row instead of adding one.

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET, HEAD | `/` | Page with the contact email filled in |
| GET, HEAD | `/health`, `/ready` | Liveness; readiness touches the DB |
| POST | `/api/audit` | multipart `file`; 413 >25 MB, 422 unreadable, 429 limits; returns audit JSON + `audit_id` |
| GET | `/api/audit/{id}` | Saved result for share links; 404 when unknown or pre-share |
| POST | `/api/leads` | JSON lead (+ `more_audit_ids` for a batch, max 20 files); 404 unknown audit, 422 invalid, 429 limit; emails in background |
| GET, HEAD | `/privacy` | Privacy page |
| GET | `/r/{id}` | Page that loads a saved report (noindex) |
| GET | `/robots.txt`, `/sitemap.xml` | Sitemap only when SITE_URL is set |
| GET | `/admin`, `/admin/leads.csv` | Basic auth with ADMIN_PASSWORD; 404 when unset |
| GET | any unknown non-API path | HTML 404 page |

## Limits (per IP, 10 min window, in memory, per process)
`UPLOAD_LIMIT` attempts of any kind · `AUDIT_LIMIT` successful checks · `LEAD_LIMIT` leads · `ADMIN_FAIL_LIMIT` wrong admin passwords.
Client IP: `CLIENT_IP_HEADER`, else `PROXY_HOPS` from the right of X-Forwarded-For, else the peer.

## Scoring and pricing (`audit.py` constants)
Weighted pass share of applicable checks; any `BLOCKING_CHECKS` failure caps it at `BLOCKING_SCORE_CAP` (60).
Quote: nothing failed → 0 (review offer); only `QUICK_FIX_CHECKS` failed → flat `MIN_ORDER`; else per page × spread.

## Config
All environment variables, defaults and effects: README > Settings. Startup logs a warning for each of
CONTACT_EMAIL, SMTP_HOST and DATABASE_URL that is unset.
