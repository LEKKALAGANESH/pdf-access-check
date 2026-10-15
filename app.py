"""Web app: upload a PDF, get an accessibility audit and a quote, leave contact details.

Uploaded PDFs are read in memory and never written to disk; only the audit result is kept.
Run: .venv\\Scripts\\python -m uvicorn app:app --port 8000
"""
from __future__ import annotations

import base64
import binascii
import csv
import html
import io
import json
import logging
import math
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

import audit
import mailer
import store

HERE = Path(__file__).parent
STATIC = HERE / "static"
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "").strip()
SITE_URL = os.environ.get("SITE_URL", "").strip().rstrip("/")  # e.g. https://pdfaccesscheck.com
PLAUSIBLE_DOMAIN = os.environ.get("PLAUSIBLE_DOMAIN", "").strip()  # analytics off when empty
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")  # /admin is a 404 when empty
PROXY_HOPS = int(os.environ.get("PROXY_HOPS", "0"))  # proxies that append to X-Forwarded-For
CLIENT_IP_HEADER = os.environ.get("CLIENT_IP_HEADER", "").strip().lower()  # e.g. cf-connecting-ip, set by the proxy
UPLOAD_LIMIT = 60  # upload attempts of any kind per IP per window
AUDIT_LIMIT = 30  # successful checks per IP per window; rejected files don't count
LEAD_LIMIT = 5
ADMIN_FAIL_LIMIT = 10  # wrong admin passwords per IP per window
LIMIT_WINDOW_S = 600
WINDOW_TEXT = f"{LIMIT_WINDOW_S // 60} minutes"
BATCH_MAX = 20  # files one lead can cover
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
PLACEHOLDER_EMAIL = "hello@example.com"
TITLE = "Free PDF accessibility check · ADA Title II"
DESCRIPTION = ("Upload a PDF and get a free WCAG 2.1 AA and PDF/UA accessibility check in seconds, "
               "plus a fixed price to make it compliant.")
PUBLIC_PAGES = ("/", "/privacy")

STATIC_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000",  # browsers ignore it over plain http
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "pdf-accessibility",
            "trace_id": getattr(record, "trace_id", None),
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["error"] = self.formatException(record.exc_info)
        return json.dumps(entry)


log = logging.getLogger("pdf-accessibility")
_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
log.addHandler(_handler)
log.setLevel(logging.INFO)
log.propagate = False


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.migrate()
    for missing, effect in ((not CONTACT_EMAIL, "CONTACT_EMAIL is not set; the page shows a placeholder address"),
                            (not mailer.SMTP_HOST, "SMTP_HOST is not set; new leads are not emailed"),
                            (not store.DATABASE_URL, "DATABASE_URL is not set; leads are kept in the local leads.db")):
        if missing:
            log.warning(effect)
    yield


app = FastAPI(title="PDF accessibility check", lifespan=lifespan, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

# ponytail: in-memory per-process limiter keyed by client IP; move to Redis when running >1 worker.
_hits: dict[str, deque] = defaultdict(deque)


_proxy_warned = False


def client_ip(request: Request) -> str:
    """The real client: a header the proxy sets (CLIENT_IP_HEADER), else the entry PROXY_HOPS from the right
    of X-Forwarded-For (entries further left are client-controlled), else the connecting peer."""
    global _proxy_warned
    if CLIENT_IP_HEADER and (value := request.headers.get(CLIENT_IP_HEADER, "").strip()):
        return value
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    if PROXY_HOPS and len(forwarded) >= PROXY_HOPS:
        return forwarded[-PROXY_HOPS]
    if forwarded and not PROXY_HOPS and not _proxy_warned:
        _proxy_warned = True  # behind an unconfigured proxy every visitor shares one rate limit
        log.warning("requests arrive through a proxy; set PROXY_HOPS or CLIENT_IP_HEADER (see /admin)")
    return request.client.host if request.client else "unknown"


def recent_hits(request: Request, bucket: str) -> deque:
    now = time.monotonic()
    hits = _hits[f"{bucket}:{client_ip(request)}"]
    while hits and now - hits[0] > LIMIT_WINDOW_S:
        hits.popleft()
    return hits


def rate_limit(request: Request, bucket: str, max_hits: int, why: str, record: bool = True) -> None:
    """`why` tells the visitor which limit they hit; the reply adds when they can try again."""
    hits = recent_hits(request, bucket)
    if len(hits) >= max_hits:
        wait_s = max(1, math.ceil(LIMIT_WINDOW_S - (time.monotonic() - hits[0])))
        minutes = math.ceil(wait_s / 60)
        raise HTTPException(429, f"{why} You can try again in {minutes} minute{'' if minutes == 1 else 's'}.",
                            headers={"Retry-After": str(wait_s)})
    if record:
        hits.append(time.monotonic())


def content_security_policy() -> str:
    scripts = "'self' https://plausible.io" if PLAUSIBLE_DOMAIN else "'self'"
    return (f"default-src 'self'; script-src {scripts}; connect-src {scripts}; img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


@app.middleware("http")
async def trace_and_headers(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    started = time.perf_counter()
    response = await call_next(request)
    response.headers.update(STATIC_HEADERS)
    response.headers["Content-Security-Policy"] = content_security_policy()
    # Pages and assets revalidate on every load so a deploy never mixes old JS with new HTML;
    # API results and the admin page (names, emails, file names) are never stored by the browser.
    private = request.url.path.startswith(("/api/", "/admin"))
    response.headers["Cache-Control"] = "no-store" if private else "no-cache"
    response.headers["X-Trace-Id"] = trace_id
    log.info("request", extra={"trace_id": trace_id, "fields": {
        "method": request.method, "path": request.url.path, "status": response.status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 1)}})
    return response


@app.exception_handler(RequestValidationError)
async def readable_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = sorted({str(e["loc"][-1]) for e in exc.errors()})
    return JSONResponse({"detail": f"Please check: {', '.join(fields)}."}, status_code=422)


@app.exception_handler(StarletteHTTPException)
async def html_not_found(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and not request.url.path.startswith(("/api/", "/static/")):
        return FileResponse(STATIC / "404.html", status_code=404)
    return await http_exception_handler(request, exc)


# ---------- pages ----------

def head_tags(path: str, *, indexable: bool) -> str:
    esc = html.escape
    tags = [f'<meta property="og:title" content="{esc(TITLE)}">',
            f'<meta property="og:description" content="{esc(DESCRIPTION)}">',
            '<meta property="og:type" content="website">',
            '<meta name="twitter:card" content="summary">']
    if SITE_URL:
        tags += [f'<link rel="canonical" href="{esc(SITE_URL + path)}">',
                 f'<meta property="og:url" content="{esc(SITE_URL + path)}">']
    if not indexable:
        tags.append('<meta name="robots" content="noindex">')
    if path == "/":
        data = {"@context": "https://schema.org", "@type": "WebApplication", "name": "PDF Access Check",
                "description": DESCRIPTION, "applicationCategory": "BusinessApplication",
                "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
        if SITE_URL:
            data["url"] = SITE_URL + "/"
        # A data block, not a script, so CSP doesn't apply; escaping "</" keeps SITE_URL from closing the tag.
        tags.append(f'<script type="application/ld+json">{json.dumps(data).replace("</", "<\\/")}</script>')
    if PLAUSIBLE_DOMAIN:
        # No SRI hash: Plausible updates script.js in place, so a pinned hash would silently stop analytics.
        tags.append(f'<script defer data-domain="{esc(PLAUSIBLE_DOMAIN)}" src="https://plausible.io/js/script.js"></script>')
    return "\n  ".join(tags)


def page(name: str, path: str, *, indexable: bool = True) -> HTMLResponse:
    text = (STATIC / name).read_text(encoding="utf-8")  # read per request so edits need no restart
    text = text.replace("{{HEAD}}", head_tags(path, indexable=indexable))
    text = text.replace("{{ANALYTICS_NOTE}}", "We count visits with Plausible Analytics, which uses no cookies and "
                        "stores no personal data." if PLAUSIBLE_DOMAIN else "We don't use analytics or tracking.")
    # ponytail: placeholder until CONTACT_EMAIL is set on the host; startup logs a warning
    return HTMLResponse(text.replace("{{CONTACT_EMAIL}}", html.escape(CONTACT_EMAIL or PLACEHOLDER_EMAIL)))


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def index() -> HTMLResponse:
    return page("index.html", "/")


@app.api_route("/privacy", methods=["GET", "HEAD"], include_in_schema=False)
def privacy() -> HTMLResponse:
    return page("privacy.html", "/privacy")


@app.get("/r/{audit_id}", include_in_schema=False)
def shared_report(audit_id: str) -> HTMLResponse:
    """A saved report. The page loads the result from /api/audit/{id}; links are never indexed."""
    try:
        uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(404) from None
    return page("index.html", f"/r/{audit_id}", indexable=False)


@app.get("/robots.txt", include_in_schema=False)
def robots() -> PlainTextResponse:
    lines = ["User-agent: *", "Allow: /", "Disallow: /api/", "Disallow: /admin", "Disallow: /r/"]
    if SITE_URL:
        lines.append(f"Sitemap: {SITE_URL}/sitemap.xml")
    return PlainTextResponse("\n".join(lines) + "\n")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap() -> Response:
    if not SITE_URL:
        raise HTTPException(404)  # a sitemap needs absolute URLs
    urls = "".join(f"<url><loc>{html.escape(SITE_URL + p)}</loc></url>" for p in PUBLIC_PAGES)
    return Response('<?xml version="1.0" encoding="UTF-8"?>'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>',
                    media_type="application/xml")


@app.api_route("/health", methods=["GET", "HEAD"])
def health() -> dict:
    return {"status": "ok"}


@app.api_route("/ready", methods=["GET", "HEAD"])
def ready() -> dict:
    with store.connect() as conn:
        conn.execute("SELECT 1 FROM leads LIMIT 1")
    return {"status": "ready"}


# ---------- API ----------

@app.post("/api/audit")
def run_audit(request: Request, file: UploadFile = File(...)) -> dict:
    rate_limit(request, "upload", UPLOAD_LIMIT,
               f"Your network sent {UPLOAD_LIMIT} uploads in the last {WINDOW_TEXT}, the most we accept.")
    rate_limit(request, "audit", AUDIT_LIMIT,
               f"You've checked {AUDIT_LIMIT} files in the last {WINDOW_TEXT}, the most the free check allows, "
               "so it stays fast for everyone. To check more right away, email the files to us for a bulk quote.",
               record=False)
    data = file.file.read(audit.MAX_BYTES + 1)
    if len(data) > audit.MAX_BYTES:
        raise HTTPException(413, f"File is larger than {audit.MAX_BYTES // (1024 * 1024)} MB.")
    trace_id = request.state.trace_id
    try:
        result = audit.audit_pdf(data)
    except audit.AuditError as e:
        raise HTTPException(422, str(e)) from None
    except Exception:
        log.exception("audit crashed", extra={"trace_id": trace_id, "fields": {"bytes": len(data)}})
        raise HTTPException(422, "We couldn't read this PDF. It may use features we don't support yet; "
                                 "email it to us and we'll check it by hand.") from None
    audit_id = str(uuid.uuid4())
    filename = (file.filename or "upload.pdf")[:200]
    saved = {"filename": filename, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             **result.to_dict()}
    failed = [c.id for c in result.checks if c.status == "fail"]
    with store.connect() as conn:
        conn.execute("INSERT INTO audits (id, filename, pages, scanned_pages, score, quote_low, quote_high, "
                     "failed_checks, result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (audit_id, filename, result.pages, result.scanned_pages, result.score,
                      result.quote_low, result.quote_high, ",".join(failed), json.dumps(saved)))
    recent_hits(request, "audit").append(time.monotonic())
    log.info("audit done", extra={"trace_id": trace_id, "fields": {
        "pages": result.pages, "scanned": result.scanned_pages, "score": result.score}})
    return {"audit_id": audit_id, **saved}


@app.get("/api/audit/{audit_id}")
def get_audit(audit_id: uuid.UUID) -> dict:
    with store.connect() as conn:
        row = conn.execute("SELECT result FROM audits WHERE id = ?", (str(audit_id),)).fetchone()
    if row is None or row[0] is None:  # unknown, or saved before reports were stored
        raise HTTPException(404, "This report link has expired. Upload the PDF again to get a new one.")
    return {"audit_id": str(audit_id), **json.loads(row[0])}


class LeadIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    audit_id: uuid.UUID
    more_audit_ids: list[uuid.UUID] = Field(default_factory=list, max_length=BATCH_MAX - 1)  # rest of a batch
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    organization: str = Field(min_length=1, max_length=150)
    message: str = Field(default="", max_length=2000)
    website: str = Field(default="", max_length=200)  # honeypot: humans never see this field


def report_url(audit_id: str) -> str:
    return f"{SITE_URL}/r/{audit_id}" if SITE_URL else ""


def email_lead(lead: dict, files: list[dict], trace_id: str) -> None:
    """Runs after the response; the lead is already saved, so a mail failure only gets logged."""
    sender = CONTACT_EMAIL
    try:
        mailer.send(mailer.lead_emails(sender=sender, owner=mailer.LEADS_TO or sender, lead=lead, files=files))
        log.info("lead emailed", extra={"trace_id": trace_id, "fields": {"audit_id": files[0]["id"]}})
    except Exception as e:  # never log the exception text: SMTP errors echo email addresses
        log.error("lead email failed", extra={"trace_id": trace_id, "fields": {"error": type(e).__name__}})


@app.post("/api/leads")
def create_lead(request: Request, lead: LeadIn, background: BackgroundTasks) -> dict:
    rate_limit(request, "lead", LEAD_LIMIT, f"You've sent {LEAD_LIMIT} requests in the last {WINDOW_TEXT}, so the form is "
               "paused. Your earlier requests reached us; for anything else, email us.")
    if lead.website:
        return {"ok": True}  # bot filled the hidden field; pretend success, store nothing
    ids = list(dict.fromkeys(str(i) for i in [lead.audit_id, *lead.more_audit_ids]))
    email = lead.email.lower()
    with store.connect() as conn:
        rows = conn.execute("SELECT id, filename, pages, score, quote_low, quote_high FROM audits "
                            f"WHERE id IN ({', '.join('?' * len(ids))})", ids).fetchall()
        if len(rows) != len(ids):
            raise HTTPException(404, "That check has expired. Please upload the PDF again.")
        for audit_id in ids:
            # A re-send (double click, edited message) updates the same lead instead of adding a duplicate.
            conn.execute("INSERT INTO leads (audit_id, name, email, organization, message) VALUES (?, ?, ?, ?, ?) "
                         "ON CONFLICT (audit_id, email) DO UPDATE SET name = excluded.name, "
                         "organization = excluded.organization, message = excluded.message",
                         (audit_id, lead.name, email, lead.organization, lead.message))
    trace_id = request.state.trace_id
    log.info("lead saved", extra={"trace_id": trace_id, "fields": {"audit_id": ids[0], "files": len(ids)}})
    if mailer.SMTP_HOST and CONTACT_EMAIL:
        by_id = {r[0]: r for r in rows}
        files = [{"id": i, "filename": by_id[i][1], "pages": by_id[i][2], "score": by_id[i][3],
                  "quote_low": by_id[i][4], "quote_high": by_id[i][5], "url": report_url(i)} for i in ids]
        background.add_task(email_lead, {"name": lead.name, "email": email, "organization": lead.organization,
                                         "message": lead.message}, files, trace_id)
    return {"ok": True}


# ---------- admin ----------

def require_admin(request: Request) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(404)
    rate_limit(request, "admin-fail", ADMIN_FAIL_LIMIT, "Too many wrong passwords.", record=False)
    scheme, _, encoded = request.headers.get("authorization", "").partition(" ")
    password = ""
    if scheme.lower() == "basic":
        try:
            password = base64.b64decode(encoded, validate=True).decode("utf-8").partition(":")[2]
        except (binascii.Error, UnicodeDecodeError):
            pass
    if not secrets.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
        recent_hits(request, "admin-fail").append(time.monotonic())
        raise HTTPException(401, "Sign in to see leads.", headers={"WWW-Authenticate": 'Basic realm="leads", charset="UTF-8"'})


def lead_rows() -> list[tuple]:
    with store.connect() as conn:
        return conn.execute(store.LEADS_QUERY + " LIMIT 1000").fetchall()


def ip_check(request: Request) -> str:
    """Owner-only: shows how the app sees your own address, to set PROXY_HOPS or CLIENT_IP_HEADER after deploy."""
    esc = html.escape
    seen = [("Address used for rate limits", client_ip(request)),
            ("Connecting peer", request.client.host if request.client else "unknown"),
            *((name, request.headers[name]) for name in ("x-forwarded-for", "cf-connecting-ip", "true-client-ip", "x-real-ip")
              if name in request.headers)]
    items = "".join(f"<li>{esc(label)}: <code>{esc(value)}</code></li>" for label, value in seen)
    return (f'<details class="ip-check"><summary>Check the rate-limit address</summary><ul>{items}</ul>'
            "<p>The first line must be your own public IP. If it isn't, set <code>PROXY_HOPS</code> to how many "
            "entries from the right of X-Forwarded-For your IP sits, or set <code>CLIENT_IP_HEADER</code> to a "
            "header above that shows it.</p></details>")


@app.get("/admin", include_in_schema=False)
def admin(request: Request) -> HTMLResponse:
    require_admin(request)
    esc = html.escape
    rows = lead_rows()
    body = "".join(
        f"<tr><td>{esc(str(when)[:16])}</td><td>{esc(name)}</td>"
        f'<td><a href="mailto:{esc(email)}">{esc(email)}</a></td><td>{esc(org)}</td>'
        f'<td><a href="/r/{esc(audit_id)}">{esc(file)}</a></td><td>{pages}</td><td>{score}</td>'
        f"<td>{esc(mailer.quote_text(float(low), float(high)))}</td><td>{esc(msg)}</td></tr>"
        for when, name, email, org, file, pages, _scanned, score, low, high, msg, audit_id in rows)
    table = (f'<table class="data-table"><thead><tr><th scope="col">Date (UTC)</th><th scope="col">Name</th>'
             '<th scope="col">Email</th><th scope="col">Organization</th><th scope="col">File</th>'
             '<th scope="col">Pages</th><th scope="col">Score</th><th scope="col">Quote</th>'
             f'<th scope="col">Message</th></tr></thead><tbody>{body}</tbody></table>'
             if rows else "<p>No leads yet.</p>")
    return HTMLResponse(f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <meta name="color-scheme" content="light dark">
  <title>Leads · PDF Access Check</title>
  <link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <main id="main" class="admin">
    <h1>Leads</h1>
    <p>{len(rows)} {"lead" if len(rows) == 1 else "leads"}, newest first. <a href="/admin/leads.csv">Download CSV</a></p>
    {ip_check(request)}
    <div class="table-scroll" tabindex="0" role="region" aria-label="Leads table">{table}</div>
  </main>
</body>
</html>""")


def _csv_cell(value) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text  # no spreadsheet formulas


@app.get("/admin/leads.csv", include_in_schema=False)
def admin_csv(request: Request) -> Response:
    require_admin(request)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["created_at", "name", "email", "organization", "file", "pages", "scanned_pages", "score",
                     "quote_low", "quote_high", "message", "report"])
    for row in lead_rows():
        writer.writerow([_csv_cell(v) for v in row[:11]] + [f"{SITE_URL}/r/{row[11]}" if SITE_URL else f"/r/{row[11]}"])
    return Response("﻿" + out.getvalue(), media_type="text/csv; charset=utf-8",  # BOM so Excel reads UTF-8
                    headers={"Content-Disposition": 'attachment; filename="leads.csv"'})
