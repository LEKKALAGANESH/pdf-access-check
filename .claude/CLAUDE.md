# PDF Access Check — agent config

Free PDF accessibility pre-check (WCAG 2.1/2.2 AA + PDF/UA-1) that turns into a fix quote and a lead.
Python 3.14 · FastAPI · pikepdf · SQLite · plain HTML/CSS/JS (no build step, no framework).

## Commands (Windows, from the project root)
- Install: `py -3.14 -m venv .venv` then `.venv\Scripts\python -m pip install -r requirements-dev.txt`
- Run: `.venv\Scripts\python -m uvicorn app:app --port 8000` → http://127.0.0.1:8000
- Test: `.venv\Scripts\python -m pytest -q`
- Leads: `.venv\Scripts\python leads.py`

## Standards
- Smallest diff that fixes the root cause. No new dependencies without a reason in one line.
- Prices, limits and weights are constants at the top of `audit.py`; app limits at the top of `app.py`.
- Every user-facing error is a plain sentence plus what to do next. Never show stack traces.
- Copy must be exactly true in every case (pass, fail and "Not needed" rows alike).
- Frontend: vanilla JS, `textContent` only (never `innerHTML` with data), design tokens from `style.css :root`.
- The page must itself meet WCAG 2.1 AA: keyboard path, visible focus, live regions, 375px with no sideways scroll.
- Every bug fix gets a regression test in `test_app.py` that fails on the old code (UI-only fixes: verify in a browser).

## Forbidden
- Writing uploaded PDFs to disk. Logging names, emails or file contents.
- Claiming PDF/UA conformance a file does not have.
- `continue-on-error`, skipped tests, placeholder handlers, dead code.
- Putting the user's personal email on the public site. The contact address comes from `CONTACT_EMAIL`.

## Memory (read on demand: PRD.md, DESIGN.md, ARCHITECTURE.md, TESTING.md, TASKS.md)
@PROGRESS.md
@CONTEXT.md
