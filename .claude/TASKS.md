# TASKS (ordered; each independently verifiable)

## QA bug fixes (2026-10-14 QA report, `.gstack/qa-reports/`)
- [x] T1 Lead form hides after send (`style.css`; done when the form is invisible next to "Request sent")
- [x] T2 No duplicate leads (`app.py` unique (audit_id, email) + upsert; done when a double POST gives 1 row)
- [x] T3 Contact address on the page and in "can't help here" errors (`app.py`, `index.html`, `app.js`; `CONTACT_EMAIL`)
- [x] T4 Unencrypted files pass the security check (`audit.py`; encrypted and plain score the same)
- [x] T5 Honest text check on blank pages (`audit.py`; no "readable text layer" claim when there is no text)
- [x] T6 Rejected uploads don't use the check quota (`app.py`; junk uploads then N good ones all succeed)
- [x] T7 Dropping several files says only the first was checked (`app.js`)
- [x] T8 Shown price matches the API to the cent (`app.js`; $37.50 not $38)
- [x] T9 True copy on "Not needed" rows (`audit.py` bookmarks, fonts)
- [x] T10 Keep the previous report visible when a new upload fails (`app.js`)
- [x] T11 HTML 404 page for unknown pages (`app.py`, `static/404.html`)
- [x] T12 Deadline line names both dates, 2027 and 2028 (`index.html`)

## QA round 2 bugs (`.gstack/qa-reports/qa-report-localhost-2026-10-14-round2.md`)
- [x] T27 Ignore stale upload responses; keep "Checking…" until the latest finishes (`app.js`; done when big-then-small shows small)
- [x] T28 No fix price on a 100 score; quote from failed checks (`audit.py`, `app.js`; done when web-rule.pdf shows no price)
- [x] T29 `leads.py` survives non-ASCII names when piped (`leads.py`; done when `leads.py > out.txt` exits 0 with "李雷")
- [x] T30 Severity-aware verdict: a failed tags/real-text/form-labels check can't be green (`audit.py`, `app.js`; W-9 not "Nearly there")
- [x] T31 Buttons keep an edge in forced-colors mode (`style.css`; transparent border)
- [x] T32 HEAD support on `/`, `/health`, `/ready` (`app.py`; `curl -I /health` → 200)
- [x] T33 `Cache-Control: no-cache` on the page and static files (`app.py`)
- [x] T34 Print styles: hide the upload box and lead form (`style.css`)
- [x] T35 Keep the last report across reload (now via `/r/<id>` links from T21; sessionStorage removed)

## Next (launch)
- [~] T13 Set `CONTACT_EMAIL` on the host (`render.yaml` lists every setting; needs your real values)
- [x] T14 Postgres via `DATABASE_URL` (`store.py`; every API test also runs on Postgres with TEST_DATABASE_URL)
- [x] T15 Email the owner on every new lead + fixed-text confirmation to the buyer (`mailer.py`, SMTP_* settings)
- [x] T16 Privacy page `/privacy`, linked in the footer and under the lead form
- [x] T17 SEO: robots.txt, sitemap.xml, canonical + OG + Twitter tags, JSON-LD WebApplication, favicon (`SITE_URL`)
- [x] T18 Analytics: Plausible (cookie-free) behind `PLAUSIBLE_DOMAIN`; events Check done / Lead sent
- [x] T19 Client IP behind proxies: `PROXY_HOPS` / `CLIENT_IP_HEADER`, checked from /admin, warning when unset
- [x] T20 HSTS + Permissions-Policy headers

## Later (features)
- [x] T21 Shareable report link `/r/<id>` + copy link + print / save as PDF
- [x] T22 Batch check: up to 20 files, per-file table, one total quote, one lead for all (site-URL scan not built)
- [ ] T23 Self-serve fix: business decision (it would give away the flat $25 tier); not built
- [ ] T24 Stripe Checkout: needs your Stripe account, keys and prices; not built
- [x] T25 Admin page `/admin` (Basic auth, `ADMIN_PASSWORD`, lockout after 10 wrong tries, CSV export)
- [x] T26 Dark theme (screen only; every text pair checked at 4.5:1)
