# PRD — PDF Access Check

## Users
- Primary: staff at US state/local governments, school districts and public colleges (clerks, web
  coordinators, ADA coordinators) who must meet ADA Title II (WCAG 2.1 AA). Deadlines (DOJ interim
  rule): 2027-04-26 for entities serving 50k+ people, 2028-04-26 for smaller ones.
- Secondary: the owner, who fixes the PDFs by hand after a lead arrives.

## Problem
Buyers don't know if their PDFs pass, or what fixing them costs. Agencies charge $5–$12 a page and
quote slowly.

## User stories
1. As a clerk, I upload one PDF and see in seconds which accessibility checks it fails and why.
2. As a clerk, I see a price range to fix it before I talk to anyone.
3. As a clerk, I leave my name, work email and organization to request the fix.
4. As a clerk with a file the free check can't handle, I can still reach a person.
5. As the owner, I see every lead with its audit summary.

## MVP features (built)
11 structural checks with a 0–100 score · quote ($1.50 text page, $3.00 scanned page, $25 minimum,
×1.5 high end) · lead form with honeypot · per-IP rate limits · security headers · JSON logs.

## Acceptance criteria
- A tagged, titled, language-set PDF with alt text scores higher than the same file untagged.
- The same content scores the same whether or not it is encrypted (when screen readers are allowed).
- Non-PDF, empty, damaged, password-protected, >300-page and >25 MB files each get a specific message.
- Every "we can't do this here" message shows a contact address.
- One lead per (check, email): double clicks and re-sends never create duplicate rows.
- After a lead is sent, the form is gone and only "Request sent" shows.
- Rejected uploads don't use up the successful-check quota.
- Shown prices equal the API prices to the cent.

## Out of scope (for now)
Fixing PDFs automatically, payments, accounts, batch upload. See TASKS.md.
