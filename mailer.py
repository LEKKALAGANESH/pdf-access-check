"""Lead emails over SMTP (stdlib). Off until SMTP_HOST is set.

Every new lead emails the owner, so a lead survives even if the database is lost, and sends the
buyer a fixed-text confirmation. Buyer-typed text never goes into the buyer email, so the form
can't be used to send spam from our address.
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_SECURITY = os.environ.get("SMTP_SECURITY", "starttls").strip().lower()  # starttls | ssl | none
LEADS_TO = os.environ.get("LEADS_TO", "").strip()  # owner inbox; defaults to the contact address


def _money(value: float) -> str:
    return f"${value:,.2f}".replace(".00", "")


def quote_text(low: float, high: float) -> str:
    if not high:
        return "passes, review only"
    return _money(low) if low == high else f"{_money(low)}–{_money(high)}"


def _pages(n: int) -> str:
    return f"{n} page" if n == 1 else f"{n} pages"


def _file_line(f: dict) -> str:
    """Server-made facts about one checked file; no buyer-typed text."""
    return f"{_pages(f['pages'])}, score {f['score']}/100, {quote_text(f['quote_low'], f['quote_high'])}"


def lead_emails(*, sender: str, owner: str, lead: dict, files: list[dict]) -> list[EmailMessage]:
    """files: dicts with filename, pages, score, quote_low, quote_high, url (url may be empty)."""
    lines = [f"- {f['filename']}: {_file_line(f)}" + (f"\n  {f['url']}" if f["url"] else "") for f in files]
    to_owner = EmailMessage()
    organization = " ".join(lead["organization"].split())  # a header can't hold a typed line break
    to_owner["Subject"] = f"New PDF fix request: {organization} ({len(files)} {'file' if len(files) == 1 else 'files'})"
    to_owner["From"] = sender
    to_owner["To"] = owner
    to_owner["Reply-To"] = lead["email"]
    to_owner.set_content(
        f"Name: {lead['name']}\nEmail: {lead['email']}\nOrganization: {lead['organization']}\n"
        f"Message: {lead['message'] or '(none)'}\n\nFiles:\n" + "\n".join(lines) + "\n")

    to_buyer = EmailMessage()
    to_buyer["Subject"] = "We got your PDF accessibility request"
    to_buyer["From"] = sender
    to_buyer["To"] = lead["email"]
    to_buyer["Reply-To"] = sender
    count = f"{len(files)} files" if len(files) > 1 else "your file"
    # File names are buyer-supplied, so the buyer email lists each report by its facts and link only.
    reports = [f"- Report {i}: {_file_line(f)}\n  {f['url']}" for i, f in enumerate(files, 1) if f["url"]]
    heading = "Your report:\n" if len(reports) == 1 else "Your reports:\n"
    to_buyer.set_content(
        f"Thanks for your request. We received the free check results for {count} and will email you "
        "within one business day with a confirmed price and delivery date.\n\n"
        + (heading + "\n".join(reports) + "\n\n" if reports else "")
        + f"Questions? Reply to this email or write to {sender}.\n")
    return [to_owner, to_buyer]


def send(messages: list[EmailMessage]) -> None:
    smtp_class = smtplib.SMTP_SSL if SMTP_SECURITY == "ssl" else smtplib.SMTP
    with smtp_class(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
        if SMTP_SECURITY == "starttls":
            smtp.starttls()
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        for message in messages:
            smtp.send_message(message)
