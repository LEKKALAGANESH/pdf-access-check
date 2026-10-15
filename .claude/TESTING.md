# TESTING

## Command
`.venv\Scripts\python -m pytest -q` (all must pass; 0 skips). With `TEST_DATABASE_URL` set (throwaway
Postgres, see README) every API test runs a second time on Postgres.

## Strategy
- Unit: each audit rule in `audit.py` on PDFs built in memory by `make_pdf()` in `test_app.py`.
- API: FastAPI TestClient with a temp DB (`client` fixture clears rate-limit state; parametrized sqlite/postgres).
- Email: `smtp` fixture runs an in-process SMTP sink; assert on the real messages.
- UI: no JS test runner. Verify in a real browser (Playwright): upload each file in `samples/`,
  send a lead, double-click send, drop 2 files, check 375px width and keyboard-only use, 0 console errors.
- Floor: every check id has a pass and a fail test; every bug fix has a regression test that fails
  on the old code.

## Verify before "done"
1. pytest green.
2. Boot uvicorn, run the UI pass above, re-read `leads.db` to confirm writes.
3. Delete any test rows you created in `leads.db`.

## Self-review checklist
- [ ] Copy true for pass, fail and "Not needed".
- [ ] Error has a next step (and contact address if we can't help in the tool).
- [ ] No duplicate rows from repeated requests.
- [ ] `[hidden]` elements are actually invisible.
- [ ] No PII in logs.
