"""Print saved leads with their audit results.  Run: .venv\\Scripts\\python leads.py"""
import sys

import mailer
import store


def main() -> None:
    # Windows gives a piped or redirected script a cp1252 stdout, which can't print names like "李雷".
    sys.stdout.reconfigure(encoding="utf-8")
    with store.connect() as conn:
        rows = conn.execute(store.LEADS_QUERY).fetchall()
    if not rows:
        print("No leads yet.")
    for when, name, email, org, file, pages, scanned, score, low, high, msg, _audit_id in rows:
        print(f"{str(when)[:19]}  {name} <{email}>  {org}")
        print(f"    {file}: {pages} pages ({scanned} scanned), score {score}, {mailer.quote_text(float(low), float(high))}")
        if msg:
            print(f"    {msg}")


if __name__ == "__main__":
    main()
