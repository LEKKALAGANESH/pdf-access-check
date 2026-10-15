# Deploy PDF Access Check

This guide puts the app online for free. Pick one host:

| | Render (recommended) | Vercel |
|---|---|---|
| Works as-is | Yes | No, needs a small code change first ([see below](#vercel)) |
| Largest PDF | 25 MB | About 4 MB (Vercel's hard cap is 4.5 MB per request) |
| Lead emails | Yes, through Resend on port 2587 | Yes, but confirm after deploy |
| Upload limits | Strict (one copy of the app) | Looser (each running copy keeps its own count) |
| Catch on the free plan | Sleeps after 15 minutes idle; the next visitor waits about 30 seconds | None for this app beyond the limits above |

Both hosts need the same three free accounts first (step 1).

---

## 1. Before you start (both hosts)

### 1a. Database: Supabase (free Postgres)

Free hosts wipe their disk on every deploy, so leads must live in a real database.

1. Sign up at [supabase.com](https://supabase.com) and create a project. Choose a region near your buyers
   (for US public bodies, an `us-east` region). Save the database password it asks you to set.
2. Click **Connect** at the top of the project, open the connection string tab, and pick the right pooler:

   | Your host | Pick | Port | Looks like |
   |---|---|---|---|
   | Render | **Session pooler** | 5432 | `postgresql://postgres.abcdefgh:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres` |
   | Vercel | **Transaction pooler** | 6543 | the same, but ending `:6543/postgres` |

   Don't use the **Direct connection** (`db.abcdefgh.supabase.co`). It only works over IPv6, which Render
   and Vercel don't have, so the app can't reach the database.
3. Replace `[YOUR-PASSWORD]` with your database password. If the password has symbols like `@`, `#` or `/`,
   reset it in **Project Settings → Database** to letters and numbers only, or the address breaks.
4. That is your `DATABASE_URL`. The app creates its two tables (`audits`, `leads`) on first start and
   turns on Row Level Security for both, so Supabase's public API can't read your leads.

> **Free projects pause after a week with no activity.** A paused database takes the site down until
> you click **Restore** in the Supabase dashboard. Step 4.4 sets up a daily ping that keeps it awake.

### 1b. Email: Resend (free, 3,000 emails a month)

Every new lead emails you, and the buyer gets a confirmation.

1. Sign up at [resend.com](https://resend.com).
2. **Domains → Add domain**, then add the DNS records it shows at your domain registrar. Wait until it says *Verified*.
3. **API Keys → Create**. Copy the key (starts with `re_`).
4. Your `CONTACT_EMAIL` must be an address on that verified domain, for example `hello@yourdomain.com`.

No domain yet? Skip email for now. Leads are still saved and listed at `/admin`.

> Why not Gmail? Render's free plan blocks the usual email ports (25, 465, 587) since September 2025.
> Resend also listens on port **2587**, which is not blocked. `render.yaml` already uses 2587.

### 1c. Admin password

Run this in PowerShell and keep the result somewhere safe:

```powershell
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 32 | % {[char]$_})
```

### 1d. Settings you will paste into the host

| Setting | Value | Needed? |
|---|---|---|
| `CONTACT_EMAIL` | `hello@yourdomain.com` | Yes |
| `SITE_URL` | Your site address with no trailing slash, for example `https://pdf-access-check.onrender.com` | Yes (fill in after the first deploy if you don't know it yet) |
| `DATABASE_URL` | The Supabase pooler string from step 1a | Yes |
| `SMTP_HOST` | `smtp.resend.com` | For email |
| `SMTP_PORT` | `2587` (Render, already in `render.yaml`) or `587` (Vercel) | For email |
| `SMTP_USER` | `resend` | For email |
| `SMTP_PASSWORD` | Your Resend API key | For email |
| `ADMIN_PASSWORD` | The password from step 1c | Yes |
| `LEADS_TO` | Inbox for new leads, if different from `CONTACT_EMAIL` | No |
| `PROXY_HOPS` or `CLIENT_IP_HEADER` | Set after deploy (step 4) | After deploy |
| `PLAUSIBLE_DOMAIN` | Your domain as added in Plausible, for visit counts | No |

---

## 2. Render

1. Sign in at [render.com](https://render.com) with GitHub.
2. **New → Blueprint**, pick `LEKKALAGANESH/pdf-access-check`. Render reads `render.yaml`
   (build command, start command, health check, Python 3.14.6, free plan).
3. Fill in the values from table 1d. Leave the optional ones blank.
4. Click **Apply** and wait for the build (about 3 minutes). Your address is
   `https://pdf-access-check.onrender.com` unless Render picks a different name.
5. If you left `SITE_URL` blank, set it now under **Environment**. Render redeploys on its own.
6. Go to [step 4](#4-after-the-first-deploy-both-hosts).

**Custom domain (optional):** **Settings → Custom Domains → Add**, add the DNS record Render shows,
then change `SITE_URL` to the new address.

**Paid upgrade ($7 a month, Starter):** no sleeping, and port 587 works too.

---

## 3. Vercel

### 3a. Code changes needed first

Vercel accepts at most 4.5 MB per request. The app currently allows 25 MB, so a larger PDF gets Vercel's
raw "413" error instead of the app's own message. Before deploying to Vercel:

1. Make the upload cap a setting (for example `MAX_UPLOAD_MB`, default 25), used by `audit.py`,
   `static/app.js` and the "each up to 25 MB" text in `static/index.html`. Set it to `4` on Vercel.
2. Add a file named `.python-version` containing `3.14`. Without it Vercel uses Python 3.12.

### 3b. Deploy

1. Sign in at [vercel.com](https://vercel.com) with GitHub.
2. **Add New → Project**, import `LEKKALAGANESH/pdf-access-check`. Vercel detects FastAPI from `app.py`;
   change no build settings.
3. Under **Environment Variables**, add table 1d plus `MAX_UPLOAD_MB=4`. Use the **Transaction pooler**
   string (port 6543) for `DATABASE_URL`, `SMTP_PORT=587` and `SMTP_SECURITY=starttls`.
4. Click **Deploy**. Your address is `https://pdf-access-check.vercel.app` or similar.
5. Set `SITE_URL` to that address, then **Deployments → Redeploy**.
6. Go to [step 4](#4-after-the-first-deploy-both-hosts).

Known limits on Vercel:

- PDFs over about 4 MB cannot be checked. Buyers with bigger files have to email them.
- Upload limits are counted per running copy of the app, so a busy visitor may get more than 30 checks.
- Lead emails are sent just after the page answers. Vercel does not document whether that always finishes,
  so test it in step 4 and watch the logs for `lead email failed`.

---

## 4. After the first deploy (both hosts)

| Check | Open | You should see |
|---|---|---|
| App is up | `https://your-site/health` | `{"status":"ok"}` |
| Database works | `https://your-site/ready` | `{"status":"ready"}` |
| Admin works | `https://your-site/admin` | A sign-in box (any user name, the admin password), then "0 leads" |

Then:

1. **Rate-limit address.** On `/admin`, expand **Check the rate-limit address**. The first line must be
   your own public IP (search "what is my IP" to compare). If it isn't, set `PROXY_HOPS` or
   `CLIENT_IP_HEADER` as the panel explains, then check again. Without this, every visitor shares one
   upload limit.
2. **Full run.** Upload a PDF from `samples/`, read the report, and send **Request the fix** with your
   own email. Confirm that:
   - you receive "New PDF fix request: …" at `CONTACT_EMAIL` (or `LEADS_TO`),
   - you receive "We got your PDF accessibility request" at the email you typed,
   - the lead appears on `/admin`, and **Download CSV** works.
3. **Share link.** Click **Copy link to this report** and open it in a private window. The same report
   should load.
4. **Keep Supabase awake.** On GitHub, open the repo's **Settings → Secrets and variables → Actions →
   Variables → New repository variable**. Name it `SITE_URL` and set it to your site address (same as
   step 1d). The workflow in `.github/workflows/keep-awake.yml` then opens `/ready` once a day, which
   wakes the site and touches the database. To test it now: **Actions → Keep the database awake →
   Run workflow**, and it should finish green.
5. **Check the database.** In Supabase, open **Table Editor**: you should see `audits` and `leads`,
   each marked as protected by RLS. **Advisors → Security Advisor** should show no "RLS disabled" warning.

## 5. If something goes wrong

| What you see | Likely cause | Fix |
|---|---|---|
| `/ready` errors, logs say "Network is unreachable" | Direct connection string (`db.xxxx.supabase.co`), which is IPv6 only | Use the **Session pooler** (Render) or **Transaction pooler** (Vercel) string from step 1a |
| `/ready` errors, logs say "password authentication failed" | Wrong password, or the user isn't `postgres.yourref` | Copy the pooler string again; reset the database password if needed |
| Site down, `/ready` times out after a quiet week | Supabase paused the free project | Supabase dashboard → **Restore project**, then set up step 4.4 |
| Logs say "prepared statement … already exists" | An old version of the app on the Transaction pooler | Redeploy the latest code; it turns prepared statements off |
| No emails, logs say `lead email failed` | Email settings or blocked port | Render: keep `SMTP_PORT=2587`. Check the Resend key and that the domain is verified |
| Emails go to spam | Domain not fully verified | Finish all DNS records in Resend |
| Site shows `hello@example.com` | `CONTACT_EMAIL` not set | Add it and redeploy |
| `/admin` shows "Page not found" | `ADMIN_PASSWORD` not set | Add it and redeploy |
| "Too many requests" for everyone at once | Proxy not set up | Do step 4.1 |
| First visit takes about 30 seconds (Render) | Free plan woke up from sleep | Normal on free; Starter plan removes it |
| Vercel shows "413" for a PDF | File over 4.5 MB | Expected on Vercel; use Render for big files |

Logs: Render → your service → **Logs**. Vercel → your project → **Logs**. Each line is JSON with a
`trace_id`; the same ID is in the `X-Trace-Id` response header.

## Sources

- [Supabase: connecting to Postgres (poolers, IPv6, prepared statements)](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Supabase: securing your API (grants and RLS)](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase changelog: tables no longer exposed to the Data API automatically](https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically)

- [Render: free web services block SMTP ports](https://render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports)
- [Vercel Functions limits (4.5 MB request body)](https://vercel.com/docs/functions/limitations)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Ship a FastAPI app on Vercel](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel)
