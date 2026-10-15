import base64
import email
import email.policy
import io
import os
import socketserver
import sqlite3
import sys
import threading
from datetime import datetime, timezone

import pikepdf
import psycopg
import pytest
from fastapi.testclient import TestClient
from pikepdf import Array, Dictionary, Name, String
from starlette.requests import Request

import app as web
import audit
import leads
import mailer
import store

# Every API test runs on SQLite; set TEST_DATABASE_URL to also run them on a throwaway Postgres.
BACKENDS = ["sqlite"] + (["postgres"] if os.environ.get("TEST_DATABASE_URL") else [])


def make_pdf(*, pages=1, text=True, image=False, tagged=False, figure_alt=None,
             lang=None, title=None, form_field=False, encryption=None, embed_font=False, pdfua=False) -> bytes:
    pdf = pikepdf.new()
    font = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    if embed_font:
        font.FontDescriptor = Dictionary(Type=Name.FontDescriptor, FontName=Name.Helvetica,
                                         FontFile2=pdf.make_stream(b"x"))
    img = pdf.make_stream(b"\x80" * 64, Type=Name.XObject, Subtype=Name.Image, Width=8, Height=8,
                          ColorSpace=Name.DeviceGray, BitsPerComponent=8)
    for _ in range(pages):
        ops, res = [], Dictionary(Font=Dictionary(F1=font))
        if text:
            ops.append(b"BT /F1 12 Tf 72 720 Td (Hello) Tj ET")
        if image:
            ops.append(b"q 200 0 0 200 72 400 cm /Im0 Do Q")
            res.XObject = Dictionary(Im0=img)
        page = Dictionary(Type=Name.Page, MediaBox=[0, 0, 612, 792], Resources=res,
                          Contents=pdf.make_stream(b"\n".join(ops)))
        pdf.pages.append(pikepdf.Page(pdf.make_indirect(page)))
    if tagged:
        fig = Dictionary(Type=Name.StructElem, S=Name.Figure)
        if figure_alt:
            fig.Alt = String(figure_alt)
        doc = Dictionary(Type=Name.StructElem, S=Name.Document, K=Array([pdf.make_indirect(fig)]))
        pdf.Root.StructTreeRoot = Dictionary(Type=Name.StructTreeRoot, K=pdf.make_indirect(doc))
        pdf.Root.MarkInfo = Dictionary(Marked=True)
    if lang:
        pdf.Root.Lang = String(lang)
    if title:
        pdf.docinfo[Name.Title] = String(title)
        pdf.Root.ViewerPreferences = Dictionary(DisplayDocTitle=True)
    if form_field:
        widget = pdf.make_indirect(Dictionary(Type=Name.Annot, Subtype=Name.Widget, FT=Name.Tx,
                                              T=String("name"), Rect=[72, 600, 300, 620]))
        pdf.pages[0].obj.Annots = Array([widget])
        pdf.Root.AcroForm = Dictionary(Fields=Array([widget]))
    if pdfua:
        pdf.Root.Metadata = pdf.make_stream(
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            b'<rdf:Description xmlns:pdfuaid="http://www.aiim.org/pdfua/ns/id/"><pdfuaid:part>1</pdfuaid:part>'
            b'</rdf:Description></rdf:RDF></x:xmpmeta>', Type=Name.Metadata, Subtype=Name.XML)
    out = io.BytesIO()
    pdf.save(out, encryption=encryption)
    return out.getvalue()


GOOD = dict(tagged=True, figure_alt="City logo", lang="en-US", title="Budget 2025", embed_font=True, pdfua=True)


def status(result, check_id):
    return next(c.status for c in result.checks if c.id == check_id)


def test_rejects_non_pdf():
    with pytest.raises(audit.AuditError, match="not a PDF"):
        audit.audit_pdf(b"hello, I am a text file")


def test_rejects_password_protected_pdf():
    data = make_pdf(encryption=pikepdf.Encryption(user="secret", owner="owner"))
    with pytest.raises(audit.AuditError, match="password"):
        audit.audit_pdf(data)


def test_untagged_long_text_pdf_fails_structure_checks_and_quotes_text_rate():
    r = audit.audit_pdf(make_pdf(pages=40))
    assert (r.pages, r.scanned_pages) == (40, 0)
    for check_id in ("tagged", "title", "language", "bookmarks"):
        assert status(r, check_id) == "fail", check_id
    assert status(r, "scanned") == "pass"
    assert status(r, "alt_text") == "n/a"
    assert (r.quote_low, r.quote_high) == (60.0, 90.0)  # 40 x $1.50, x1.5 spread


def test_scanned_pages_detected_and_priced_higher():
    r = audit.audit_pdf(make_pdf(pages=20, text=False, image=True))
    assert r.scanned_pages == 20
    assert status(r, "scanned") == "fail"
    assert status(r, "alt_text") == "fail"  # images but no tags to carry alt text
    assert (r.quote_low, r.quote_high) == (60.0, 90.0)  # 20 x $3.00


def test_small_job_hits_minimum_order():
    r = audit.audit_pdf(make_pdf())
    assert r.quote_low == audit.MIN_ORDER


def test_tagged_pdf_with_lang_title_and_alt_passes_those_checks():
    good = audit.audit_pdf(make_pdf(image=True, tagged=True, figure_alt="Bar chart of 2025 budget",
                                    lang="en-US", title="Budget 2025"))
    for check_id in ("tagged", "title", "language", "alt_text"):
        assert status(good, check_id) == "pass", check_id
    assert good.score > audit.audit_pdf(make_pdf(image=True)).score


def test_figure_without_alt_text_fails():
    r = audit.audit_pdf(make_pdf(image=True, tagged=True))
    assert status(r, "alt_text") == "fail"
    assert "1 of 1" in next(c.detail for c in r.checks if c.id == "alt_text")


def test_accessibility_permission_off_fails():
    # qpdf always grants accessibility for AES (R>=4), so mimic an old Acrobat file with RC4 R3.
    enc = pikepdf.Encryption(user="", owner="owner", R=3, aes=False, metadata=False,
                             allow=pikepdf.Permissions(accessibility=False, extract=False))
    r = audit.audit_pdf(make_pdf(encryption=enc))
    assert status(r, "encryption") == "fail"


def test_form_field_without_label_and_missing_tab_order_fail():
    r = audit.audit_pdf(make_pdf(form_field=True))
    assert status(r, "form_labels") == "fail"
    assert status(r, "tab_order") == "fail"


def test_encryption_that_allows_screen_readers_scores_same_as_no_encryption():
    plain = audit.audit_pdf(make_pdf())
    locked = audit.audit_pdf(make_pdf(encryption=pikepdf.Encryption(user="", owner="owner")))
    assert status(plain, "encryption") == status(locked, "encryption") == "pass"
    assert plain.score == locked.score


def test_file_that_passes_every_check_gets_no_fix_price():
    r = audit.audit_pdf(make_pdf(pages=20, **GOOD))
    assert r.score == 100
    assert (r.quote_low, r.quote_high) == (0, 0)


def test_settings_only_failures_get_a_flat_minimum_price():
    r = audit.audit_pdf(make_pdf(pages=20, **{**GOOD, "lang": None, "pdfua": False}))
    assert {c.id for c in r.checks if c.status == "fail"} == {"language", "pdfua_id"}
    assert (r.quote_low, r.quote_high) == (audit.MIN_ORDER, audit.MIN_ORDER)


def test_blocking_failure_caps_the_score():
    r = audit.audit_pdf(make_pdf(form_field=True, **GOOD))
    assert status(r, "form_labels") == "fail"
    assert r.score <= audit.BLOCKING_SCORE_CAP


def detail(result, check_id):
    return next(c.detail for c in result.checks if c.id == check_id)


def test_blank_pages_do_not_claim_a_text_layer():
    r = audit.audit_pdf(make_pdf(text=False))
    assert status(r, "scanned") == "n/a"
    assert "text layer" not in detail(r, "scanned")


def test_not_needed_rows_have_true_copy():
    pdf, out = pikepdf.new(), io.BytesIO()
    pdf.add_blank_page()  # no fonts, no text, no images
    pdf.save(out)
    r = audit.audit_pdf(out.getvalue())
    assert status(r, "bookmarks") == "n/a" and "must scroll" not in detail(r, "bookmarks")
    assert status(r, "fonts") == "n/a" and detail(r, "fonts") == "No fonts."


@pytest.fixture(params=BACKENDS)
def client(request, tmp_path, monkeypatch):
    if request.param == "postgres":
        url = os.environ["TEST_DATABASE_URL"]
        with psycopg.connect(url) as conn:
            conn.execute("DROP TABLE IF EXISTS leads, audits")
        monkeypatch.setattr(store, "DATABASE_URL", url)
    else:
        monkeypatch.setattr(store, "DB_PATH", tmp_path / "leads.db")
        monkeypatch.setattr(store, "DATABASE_URL", "")
    web._hits.clear()
    with TestClient(web.app) as c:
        yield c


def query(sql, params=()):
    with store.connect() as conn:
        return [tuple(r) for r in conn.execute(sql, params).fetchall()]


def upload(client, data, name="report.pdf"):
    return client.post("/api/audit", files={"file": (name, data, "application/pdf")})


def test_audit_then_lead_is_saved(client):
    res = upload(client, make_pdf(pages=3))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["pages"] == 3 and body["checks"]
    lead = {"audit_id": body["audit_id"], "name": "Ana Ruiz", "email": "ana@city.gov",
            "organization": "City of Springfield", "message": "Need 40 PDFs fixed"}
    assert client.post("/api/leads", json=lead).status_code == 200
    assert query("SELECT l.email, a.pages, a.filename FROM leads l JOIN audits a ON a.id = l.audit_id") == [
        ("ana@city.gov", 3, "report.pdf")]


def test_lead_with_bad_email_gets_readable_error(client):
    audit_id = upload(client, make_pdf()).json()["audit_id"]
    res = client.post("/api/leads", json={"audit_id": audit_id, "name": "A", "email": "nope",
                                          "organization": "Org"})
    assert res.status_code == 422
    assert "email" in res.json()["detail"]


def test_lead_for_unknown_audit_is_rejected(client):
    res = client.post("/api/leads", json={"audit_id": "00000000-0000-4000-8000-000000000000",
                                          "name": "A", "email": "a@b.co", "organization": "Org"})
    assert res.status_code == 404


def test_bad_file_and_oversize_file_are_rejected(client, monkeypatch):
    assert upload(client, b"not a pdf", "x.pdf").status_code == 422
    monkeypatch.setattr(audit, "MAX_BYTES", 100)
    assert upload(client, make_pdf()).status_code == 413


def test_audit_rate_limit_counts_only_successful_checks(client):
    assert all(upload(client, b"junk").status_code == 422 for _ in range(5))
    codes = [upload(client, make_pdf()).status_code for _ in range(web.AUDIT_LIMIT + 1)]
    assert codes[-1] == 429 and 429 not in codes[:-1]


def test_upload_attempts_have_their_own_ceiling(client):
    codes = [upload(client, b"junk").status_code for _ in range(web.UPLOAD_LIMIT + 1)]
    assert codes[-1] == 429 and 429 not in codes[:-1]


def test_rate_limit_explains_why_and_when_to_retry(client):
    for _ in range(web.AUDIT_LIMIT):
        upload(client, make_pdf())
    res = upload(client, make_pdf())
    assert res.status_code == 429
    message = res.json()["detail"]
    assert f"{web.AUDIT_LIMIT} files in the last 10 minutes" in message
    assert "try again in 10 minutes" in message and "bulk quote" in message
    assert 590 <= int(res.headers["retry-after"]) <= 600


def test_audit_result_records_when_it_was_checked(client):
    body = upload(client, make_pdf()).json()
    assert body["checked_at"].startswith(str(datetime.now(timezone.utc).year))
    assert client.get(f"/api/audit/{body['audit_id']}").json()["checked_at"] == body["checked_at"]


def test_fix_advice_is_plain_language():
    r = audit.audit_pdf(make_pdf(form_field=True, image=True))
    advice = " ".join(c.fix for c in r.checks)
    for jargon in ("(TU)", "XMP", "DisplayDocTitle", "Unicode", "artifact", "tag tree"):
        assert jargon not in advice, jargon


def test_resent_lead_updates_one_row_instead_of_duplicating(client):
    audit_id = upload(client, make_pdf()).json()["audit_id"]
    lead = {"audit_id": audit_id, "name": "Ana", "email": "ana@city.gov", "organization": "City"}
    assert client.post("/api/leads", json=lead).status_code == 200
    assert client.post("/api/leads", json={**lead, "email": "ANA@city.gov", "message": "40 PDFs"}).status_code == 200
    assert query("SELECT email, message FROM leads") == [("ana@city.gov", "40 PDFs")]


def test_page_shows_contact_email_and_both_deadlines(client, monkeypatch):
    monkeypatch.setattr(web, "CONTACT_EMAIL", "help@pdfcheck.test")
    page = client.get("/").text
    assert 'href="mailto:help@pdfcheck.test"' in page and "{{" not in page
    assert "2027" in page and "2028" in page


def test_head_requests_work_for_uptime_monitors(client):
    for path in ("/", "/health", "/ready"):
        assert client.head(path).status_code == 200, path


def test_cache_headers(client):
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/static/app.js").headers["cache-control"] == "no-cache"
    assert upload(client, make_pdf()).headers["cache-control"] == "no-store"


def test_leads_report_prints_non_ascii_names_on_a_cp1252_stream(client, monkeypatch):
    audit_id = upload(client, make_pdf(), "Acta – Junta.pdf").json()["audit_id"]
    client.post("/api/leads", json={"audit_id": audit_id, "name": "José Núñez 李雷", "email": "jn@city.gov",
                                    "organization": "Ciudad de Peñasco"})
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")  # what Windows gives a piped or redirected script
    monkeypatch.setattr(sys, "stdout", out)
    leads.main()
    out.flush()
    assert "José Núñez 李雷" in out.buffer.getvalue().decode("utf-8")


def test_unknown_page_gets_html_404_and_unknown_api_gets_json(client):
    res = client.get("/no-such-page")
    assert res.status_code == 404 and res.headers["content-type"].startswith("text/html")
    assert client.get("/api/no-such-thing").json() == {"detail": "Not Found"}


def test_health_and_security_headers(client):
    res = client.get("/health")
    assert res.json() == {"status": "ok"}
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["x-content-type-options"] == "nosniff"
    assert client.get("/ready").status_code == 200


# ---------- shareable reports and batches ----------

def test_report_is_saved_and_shareable(client):
    body = upload(client, make_pdf(pages=3), "minutes.pdf").json()
    saved = client.get(f"/api/audit/{body['audit_id']}")
    assert saved.status_code == 200 and saved.json() == body
    assert saved.json()["filename"] == "minutes.pdf"
    shared = client.get(f"/r/{body['audit_id']}")
    assert shared.status_code == 200 and '<meta name="robots" content="noindex">' in shared.text
    assert client.get("/r/not-a-uuid").headers["content-type"].startswith("text/html")
    missing = client.get("/api/audit/00000000-0000-4000-8000-000000000000")
    assert missing.status_code == 404 and "expired" in missing.json()["detail"]


def test_old_sqlite_file_gets_the_report_column(tmp_path, monkeypatch):
    old = tmp_path / "old.db"
    with sqlite3.connect(old) as conn:  # the schema before reports were stored
        conn.execute("CREATE TABLE audits (id TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT (datetime('now')), "
                     "filename TEXT NOT NULL, pages INTEGER NOT NULL, scanned_pages INTEGER NOT NULL, "
                     "score INTEGER NOT NULL, quote_low REAL NOT NULL, quote_high REAL NOT NULL, "
                     "failed_checks TEXT NOT NULL)")
        conn.execute("INSERT INTO audits VALUES ('00000000-0000-4000-8000-0000000000a1', '2026-01-01', "
                     "'old.pdf', 1, 0, 50, 25, 37.5, '')")
    monkeypatch.setattr(store, "DB_PATH", old)
    monkeypatch.setattr(store, "DATABASE_URL", "")
    web._hits.clear()
    with TestClient(web.app) as c:
        assert query("SELECT filename, result FROM audits") == [("old.pdf", None)]
        assert c.get("/api/audit/00000000-0000-4000-8000-0000000000a1").status_code == 404


def test_batch_lead_covers_every_file(client):
    first, second = (upload(client, make_pdf(), n).json()["audit_id"] for n in ("a.pdf", "b.pdf"))
    lead = {"audit_id": first, "more_audit_ids": [second, first], "name": "Ana", "email": "ana@city.gov",
            "organization": "City"}
    assert client.post("/api/leads", json=lead).status_code == 200
    assert sorted(query("SELECT a.filename FROM leads l JOIN audits a ON a.id = l.audit_id")) == [
        ("a.pdf",), ("b.pdf",)]
    unknown = {**lead, "more_audit_ids": ["00000000-0000-4000-8000-000000000000"]}
    assert client.post("/api/leads", json=unknown).status_code == 404
    too_many = {**lead, "more_audit_ids": [second] * web.BATCH_MAX}
    assert client.post("/api/leads", json=too_many).status_code == 422


# ---------- lead emails ----------

class _SmtpHandler(socketserver.StreamRequestHandler):
    """Just enough SMTP for smtplib: accepts every message and keeps it."""

    def handle(self):
        def reply(text):
            self.wfile.write(text.encode() + b"\r\n")

        reply("220 test sink")
        while line := self.rfile.readline():
            command = line.decode().strip().upper()
            if command.startswith(("EHLO", "HELO")):
                reply("250 test sink")
            elif command.startswith(("MAIL", "RCPT", "RSET", "NOOP")):
                reply("250 ok")
            elif command == "DATA":
                reply("354 go ahead")
                data = b""
                while (chunk := self.rfile.readline()) not in (b".\r\n", b""):
                    data += chunk
                self.server.messages.append(email.message_from_bytes(data, policy=email.policy.default))
                reply("250 queued")
            elif command == "QUIT":
                reply("221 bye")
                return
            else:
                reply("502 not here")


@pytest.fixture
def smtp(monkeypatch):
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _SmtpHandler)
    server.daemon_threads = True
    server.messages = []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(mailer, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(mailer, "SMTP_PORT", server.server_address[1])
    monkeypatch.setattr(mailer, "SMTP_SECURITY", "none")
    monkeypatch.setattr(web, "CONTACT_EMAIL", "help@pdfcheck.test")
    monkeypatch.setattr(web, "SITE_URL", "https://pdfcheck.test")
    yield server
    server.shutdown()
    server.server_close()


def test_new_lead_emails_the_owner_and_confirms_to_the_buyer(client, smtp):
    audit_id = upload(client, make_pdf(), "budget.pdf").json()["audit_id"]
    lead = {"audit_id": audit_id, "name": "Ana <b>Ruiz</b>", "email": "Ana@City.gov", "organization": "City",
            "message": "Visit http://spam.example now"}
    assert client.post("/api/leads", json=lead).status_code == 200
    owner, buyer = smtp.messages
    assert owner["To"] == "help@pdfcheck.test" and owner["Reply-To"] == "ana@city.gov"
    assert "Ana <b>Ruiz</b>" in owner.get_content() and "budget.pdf" in owner.get_content()
    assert f"https://pdfcheck.test/r/{audit_id}" in owner.get_content()
    assert buyer["To"] == "ana@city.gov"
    body = buyer.get_content()
    assert f"https://pdfcheck.test/r/{audit_id}" in body
    assert "Ruiz" not in body and "spam.example" not in body  # buyer-typed text never goes out from our address


def test_batch_lead_emails_list_every_report(client, smtp):
    ids = [upload(client, make_pdf(pages=n), f"file{n}.pdf").json()["audit_id"] for n in (1, 3)]
    lead = {"audit_id": ids[0], "more_audit_ids": ids[1:], "name": "Ana", "email": "ana@city.gov",
            "organization": "City of\nSpringfield"}
    assert client.post("/api/leads", json=lead).status_code == 200
    owner, buyer = smtp.messages
    assert owner["Subject"] == "New PDF fix request: City of Springfield (2 files)"
    assert "file1.pdf: 1 page," in owner.get_content() and "file3.pdf: 3 pages," in owner.get_content()
    body = buyer.get_content()
    assert all(f"https://pdfcheck.test/r/{i}" in body for i in ids)
    assert "1 page, score" in body and "file1.pdf" not in body  # file names are buyer-supplied text


def test_mail_outage_still_saves_the_lead(client, monkeypatch):
    monkeypatch.setattr(mailer, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(mailer, "SMTP_PORT", 9)  # nothing listens here
    monkeypatch.setattr(mailer, "SMTP_SECURITY", "none")
    monkeypatch.setattr(web, "CONTACT_EMAIL", "help@pdfcheck.test")
    audit_id = upload(client, make_pdf()).json()["audit_id"]
    lead = {"audit_id": audit_id, "name": "Ana", "email": "ana@city.gov", "organization": "City"}
    assert client.post("/api/leads", json=lead).status_code == 200
    assert query("SELECT email FROM leads") == [("ana@city.gov",)]


# ---------- public site: privacy, SEO, headers, analytics ----------

def test_privacy_page_and_footer_link(client):
    res = client.get("/privacy")
    assert res.status_code == 200 and "never saved" in res.text and "{{" not in res.text
    assert 'href="/privacy"' in client.get("/").text


def test_seo_tags_follow_site_url(client, monkeypatch):
    page = client.get("/").text
    assert 'property="og:title"' in page and "application/ld+json" in page and 'rel="canonical"' not in page
    assert client.get("/sitemap.xml").status_code == 404
    assert "Sitemap:" not in client.get("/robots.txt").text
    monkeypatch.setattr(web, "SITE_URL", "https://pdfcheck.test")
    page = client.get("/").text
    assert '<link rel="canonical" href="https://pdfcheck.test/">' in page
    assert "application/ld+json" not in client.get("/privacy").text
    sitemap = client.get("/sitemap.xml").text
    assert "<loc>https://pdfcheck.test/</loc>" in sitemap and "<loc>https://pdfcheck.test/privacy</loc>" in sitemap
    robots = client.get("/robots.txt").text
    assert "Disallow: /api/" in robots and "Disallow: /admin" in robots
    assert "Sitemap: https://pdfcheck.test/sitemap.xml" in robots


def test_hardening_headers_and_optional_analytics(client, monkeypatch):
    res = client.get("/")
    assert res.headers["strict-transport-security"] == "max-age=31536000"
    assert "camera=()" in res.headers["permissions-policy"]
    assert "plausible" not in res.headers["content-security-policy"] and "plausible" not in res.text
    monkeypatch.setattr(web, "PLAUSIBLE_DOMAIN", "pdfcheck.test")
    res = client.get("/")
    assert 'data-domain="pdfcheck.test"' in res.text
    assert "script-src 'self' https://plausible.io" in res.headers["content-security-policy"]


def make_request(xff, peer="10.0.0.1"):
    headers = [(b"x-forwarded-for", xff.encode())] if xff else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234)})


def test_client_ip_trusts_only_the_proxy_hops(monkeypatch):
    assert web.client_ip(make_request("6.6.6.6, 9.9.9.9")) == "10.0.0.1"  # no proxy configured
    monkeypatch.setattr(web, "PROXY_HOPS", 1)
    assert web.client_ip(make_request("6.6.6.6, 9.9.9.9")) == "9.9.9.9"  # spoofed 6.6.6.6 ignored
    assert web.client_ip(make_request("")) == "10.0.0.1"


def test_client_ip_from_a_proxy_set_header(monkeypatch):
    monkeypatch.setattr(web, "CLIENT_IP_HEADER", "cf-connecting-ip")
    req = Request({"type": "http", "client": ("10.0.0.1", 1),
                   "headers": [(b"cf-connecting-ip", b"7.7.7.7"), (b"x-forwarded-for", b"6.6.6.6")]})
    assert web.client_ip(req) == "7.7.7.7"
    assert web.client_ip(make_request("6.6.6.6")) == "10.0.0.1"  # header missing: fall back to the peer


def test_admin_shows_how_it_sees_your_address(client, monkeypatch):
    monkeypatch.setattr(web, "ADMIN_PASSWORD", "s3cret-pass")
    page = client.get("/admin", headers={**basic("s3cret-pass"), "X-Forwarded-For": "203.0.113.9"}).text
    assert "Address used for rate limits" in page and "<code>203.0.113.9</code>" in page


# ---------- admin ----------

def basic(password):
    return {"Authorization": "Basic " + base64.b64encode(f"owner:{password}".encode()).decode()}


def test_admin_is_off_without_a_password(client):
    assert client.get("/admin").status_code == 404


def test_admin_lists_and_exports_leads(client, monkeypatch):
    monkeypatch.setattr(web, "ADMIN_PASSWORD", "s3cret-pass")
    audit_id = upload(client, make_pdf(), "<b>x</b>.pdf").json()["audit_id"]
    client.post("/api/leads", json={"audit_id": audit_id, "name": '=HYPERLINK("http://evil")',
                                    "email": "ana@city.gov", "organization": "City"})
    denied = client.get("/admin")
    assert denied.status_code == 401 and "Basic" in denied.headers["www-authenticate"]
    assert client.get("/admin", headers=basic("wrong")).status_code == 401
    page = client.get("/admin", headers=basic("s3cret-pass"))
    assert page.status_code == 200 and "ana@city.gov" in page.text
    assert "&lt;b&gt;x&lt;/b&gt;.pdf" in page.text and "<b>x</b>" not in page.text
    assert page.headers["cache-control"] == "no-store"
    exported = client.get("/admin/leads.csv", headers=basic("s3cret-pass"))
    assert exported.text.startswith("﻿created_at,") and "'=HYPERLINK" in exported.text


def test_admin_locks_out_password_guessing(client, monkeypatch):
    monkeypatch.setattr(web, "ADMIN_PASSWORD", "s3cret-pass")
    codes = [client.get("/admin", headers=basic(f"guess{i}")).status_code for i in range(web.ADMIN_FAIL_LIMIT + 1)]
    assert codes[-1] == 429 and set(codes[:-1]) == {401}
    assert client.get("/admin", headers=basic("s3cret-pass")).status_code == 429  # locked for the window
