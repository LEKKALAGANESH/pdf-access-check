# PDF Access Check

A buyer uploads one PDF, or up to 20 at once, and gets in seconds:

1. a free accessibility check against WCAG 2.1/2.2 AA and PDF/UA-1 (11 checks, score 0–100),
2. a price to fix it: $1.50 per text page, $3.00 per scanned page, $25 minimum per file.
   A file that fails only document settings (title, language, tab order, security, PDF/UA flag)
   gets a flat $25. A file that passes every check gets no price, only an offer of a manual review.
   A failed tags, real-text, alt-text or form-label check caps the score at 60 ("Needs work").
3. a report link to share with a manager, a printable report, and a form to request the fix.

Every request is saved as a lead, emailed to you, and listed at `/admin`.

Target buyers: US state and local governments, schools and colleges facing the ADA Title II
web accessibility rule. Background research is in `research/`.

Uploaded PDFs are read in memory and never written to disk. Only the results are stored
(file name, pages, score, each check's result, quote). See `/privacy`.

## Run locally (Windows PowerShell)

```powershell
cd D:\Desktop\pdf-accessibility
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:CONTACT_EMAIL = "you@yourdomain.com"
.venv\Scripts\python -m uvicorn app:app --port 8000
```

Open http://127.0.0.1:8000 and drop files from `samples/`. Without `DATABASE_URL`, leads go to `leads.db`.

See leads: open `/admin` (needs `ADMIN_PASSWORD`) or run `.venv\Scripts\python leads.py`. To save
`leads.py` output to a file from Windows PowerShell 5.1, run
`[Console]::OutputEncoding = [Text.UTF8Encoding]::new()` first, or non-English names come out garbled.

## Settings (environment variables, all optional locally)

| Variable | What it does |
|---|---|
| `CONTACT_EMAIL` | Public address on the site and the sender of lead emails. Unset: shows `hello@example.com` and logs a warning. |
| `SITE_URL` | `https://your-domain`, no trailing slash. Turns on canonical links, `og:url`, `sitemap.xml` and report links in emails. |
| `DATABASE_URL` | Supabase pooler connection string (see DEPLOY.md); any Postgres works. Unset: local `leads.db`, which free hosts wipe on every deploy. |
| `SMTP_HOST`, `SMTP_PORT` (587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_SECURITY` (`starttls`, `ssl` or `none`) | Email every new lead to you and send the buyer a fixed-text confirmation. Unset: no emails. |
| `LEADS_TO` | Inbox for new leads. Default: `CONTACT_EMAIL`. |
| `ADMIN_PASSWORD` | Turns on `/admin` (leads table and CSV export, HTTP Basic sign-in, any user name). Unset: `/admin` is a 404. |
| `PROXY_HOPS` / `CLIENT_IP_HEADER` | How to find the visitor's IP behind your host's proxy, for rate limits. Set them after deploy with `/admin` > "Check the rate-limit address". Only use `CLIENT_IP_HEADER` if the proxy always overwrites that header. |
| `PLAUSIBLE_DOMAIN` | Cookie-free visit counts with Plausible, plus "Check done" and "Lead sent" events. Unset: no analytics. |

## Test

```powershell
.venv\Scripts\python -m pytest -q
```

To also run every API test on Postgres, start a throwaway one and point the tests at it:

```powershell
docker run -d --name pdfcheck-pg-test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=pdfcheck -p 55432:5432 postgres:17-alpine
$env:TEST_DATABASE_URL = "postgresql://postgres:test@127.0.0.1:55432/pdfcheck"
.venv\Scripts\python -m pytest -q
docker rm -f pdfcheck-pg-test
```

## Files

| File | Job |
|---|---|
| `audit.py` | The 11 checks, score and quote. Prices, limits and weights are constants at the top. |
| `app.py` | Web server: pages, `/api/audit`, `/api/leads`, `/r/<id>` report links, `/admin`, robots/sitemap, headers, rate limits, JSON logs. |
| `store.py` | SQLite or Postgres, same calls for both. Creates the tables on startup. |
| `mailer.py` | Lead emails over SMTP. |
| `static/` | `index.html`, `privacy.html`, `404.html`, `style.css` (light and dark), `app.js`, favicon, Public Sans font. |
| `leads.py` | Prints saved leads. |
| `render.yaml` | Render blueprint with every setting listed. |
| `.github/workflows/keep-awake.yml` | Daily ping of `/ready` so the free Supabase project never pauses (needs the repo variable `SITE_URL`). |
| `test_app.py` | Builds test PDFs and checks every rule plus the API. |

## Limits of this version

- It reads document structure only. It does not judge reading order, table headers or whether
  alt text is good. A real job still ends with veraPDF + PAC and a human review.
- It does not fix PDFs. You fix them after a lead comes in.
- Rate limits live in memory, per process. Per IP per 10 minutes: 60 upload attempts, 30 successful
  checks (rejected files don't count), 5 leads and 10 wrong admin passwords. A visitor who hits one sees
  which limit it was and how many minutes to wait (also sent as `Retry-After`); a batch stops at the limit,
  keeps the reports already done and marks the rest "Not checked yet".
- One lead per check and email: sending again updates that lead instead of adding a duplicate.

## Deploy for free

See [DEPLOY.md](DEPLOY.md): Render (recommended, works as-is) or Vercel (4 MB file limit, needs a small
code change first), with Supabase for the database and Resend for email.
