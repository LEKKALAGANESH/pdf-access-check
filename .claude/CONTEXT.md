# CONTEXT (rewrite each session; ~40 lines max)

## Active focus
Launch: fill the values in `render.yaml` (T13), then set PROXY_HOPS from /admin. Open: T23 self-serve fix, T24 Stripe (owner decisions).
Pending tasks T14–T22, T25, T26 done 2026-10-14 (42 tests on SQLite, 66 with Postgres).
Real-PDF test set: IRS fw9/f1040/p17/i1040gi, DOJ web-rule, W3C table (re-download from irs.gov/ada.gov/w3.org).

## Recent (2026-10-14)
- Fixed 11 QA bugs + deadline copy. 8 new regression tests; all fail on the pre-fix code.
- Scores changed on purpose: "not encrypted" now passes (was Not needed), blank pages no longer get
  "real text" credit. `tagged-good.pdf` is 90 (was 89), a blank page is 10 (was 32).
- New `CONTACT_EMAIL` env var; the page falls back to `hello@example.com` with a startup warning.
- Limits now: 60 upload attempts, 30 successful checks, 5 leads per IP per 10 minutes.
- Leads: unique `(audit_id, email)`, re-send updates the row.
- QA report + before/after screenshots: `.gstack/qa-reports/`.

- Round 2 fixes: newest upload wins (ticket counter in `app.js`); score 100 → no price ("Request a review");
  settings-only failures → flat $25; blocking failures cap the score at 60; HEAD on `/`, `/health`, `/ready`;
  Cache-Control no-cache (pages) / no-store (API); print CSS fits a report on 2 Letter pages; last report in sessionStorage.

- 2026-10-14 pendings: `store.py` (SQLite/Postgres), `mailer.py` (SMTP), `/privacy`, `/r/<id>` share links
  (replace the sessionStorage restore), batch upload (20 files), `/admin` + CSV, SEO files, Plausible option, dark theme.

## Gotchas
- Postgres tests: `docker run ... postgres:17-alpine` on port 55432, then TEST_DATABASE_URL (see README). Docker Desktop
  must be running (it was started for this session).
- `.env*` files are blocked by the user's permission rules: document settings in README / render.yaml instead.
- Render's X-Forwarded-For order is unverified; set PROXY_HOPS only after reading /admin > "Check the rate-limit address".
- PowerShell 5.1 `>` garbles UTF-8 from any program; `leads.py` no longer crashes, see README for the fix.
- The Bash tool halves backslashes inside Python heredocs; use the Edit tool or a script file for escapes.
- Not a git repo. No worktrees; back up files before big edits.
- `leads.db` holds the owner's real rows (1 lead, 2 audits as of 2026-10-14). Delete only rows you created.
- If a DB ever has duplicate (audit_id, email) leads, the unique index fails at startup: dedupe first.
- `[hidden] { display: none !important }` in `style.css` is load-bearing (`.lead` is a grid).
- qpdf always grants the accessibility permission for AES (R≥4); test blocked access with RC4 R3.
- `make_pdf()` always adds a Helvetica resource; use `pikepdf.new().add_blank_page()` for "no fonts".
- Playwright `setInputFiles` doesn't focus or scroll; a leftover file chooser blocks `run_code`
  (cancel with `browser_file_upload` and no paths).
- In-memory rate limits: restart uvicorn to reset them during manual QA.
- Playwright MCP can only read files under the project dir (`.playwright-mcp/` is gitignored scratch).

## Blockers
- Real public contact address unknown. Set `CONTACT_EMAIL` before launch.
