"""Accessibility audit of a PDF against WCAG 2.2 / PDF/UA-1, with a score and a price quote.

This is a fast pre-check for sales, not a certification: it reads document structure only.
A full job still ends with veraPDF + PAC and a human pass over reading order.
"""
from __future__ import annotations

import io
from dataclasses import asdict, dataclass

import pikepdf

MAX_BYTES = 25 * 1024 * 1024
MAX_PAGES = 300
RATE_TEXT_PAGE = 1.50     # USD per page that already has real text
RATE_SCANNED_PAGE = 3.00  # USD per page that needs OCR first
MIN_ORDER = 25.0
QUOTE_SPREAD = 1.5        # high end of the range covers complex tables and forms
# Document-level settings, fixed in minutes whatever the page count: these alone cost the minimum order.
QUICK_FIX_CHECKS = frozenset({"title", "language", "tab_order", "pdfua_id", "encryption"})
# Failures that lock a screen-reader user out of the content; any of them caps the score at "Needs work".
BLOCKING_CHECKS = frozenset({"tagged", "scanned", "alt_text", "form_labels"})
BLOCKING_SCORE_CAP = 60
BOOKMARKS_AFTER_PAGES = 20
TEXT_OPERATORS = "Tj TJ ' \""
MAX_XOBJECT_DEPTH = 3
FONT_FILES = ("/FontFile", "/FontFile2", "/FontFile3")


class AuditError(ValueError):
    """The upload can't be audited. The message is safe to show the user."""


@dataclass
class Check:
    id: str
    title: str
    weight: int
    rule: str
    status: str  # "pass" | "fail" | "n/a"
    detail: str
    fix: str


@dataclass
class Audit:
    pages: int
    scanned_pages: int
    score: int
    quote_low: float
    quote_high: float
    checks: list[Check]

    def to_dict(self) -> dict:
        return asdict(self)


def audit_pdf(data: bytes) -> Audit:
    # The PDF spec lets the header start anywhere in the first 1024 bytes.
    if b"%PDF-" not in data[:1024]:
        raise AuditError("This file is not a PDF.")
    try:
        pdf = pikepdf.open(io.BytesIO(data))
    except pikepdf.PasswordError:
        raise AuditError("This PDF needs a password to open. Remove the password and upload it again.") from None
    except pikepdf.PdfError:
        raise AuditError("This PDF is damaged and could not be read.") from None
    with pdf:
        pages = len(pdf.pages)
        if pages == 0:
            raise AuditError("This PDF has no pages.")
        if pages > MAX_PAGES:
            raise AuditError(f"This PDF has {pages} pages. The free check handles up to {MAX_PAGES}; "
                             "contact us for a quote on larger files.")
        scanned = sum(_is_scanned(p) for p in pdf.pages)
        has_text = any(_has_text(p) for p in pdf.pages)
        checks = [
            _tagged(pdf), _scanned_check(scanned, pages, has_text), _alt_text(pdf), _title(pdf), _language(pdf),
            _fonts(pdf), _encryption(pdf), _form_labels(pdf), _bookmarks(pdf, pages), _tab_order(pdf),
            _pdfua_id(pdf),
        ]
    applicable = [c for c in checks if c.status != "n/a"]
    total = sum(c.weight for c in applicable)
    earned = sum(c.weight for c in applicable if c.status == "pass")
    score = round(100 * earned / total) if total else 100
    failed = {c.id for c in checks if c.status == "fail"}
    if failed & BLOCKING_CHECKS:
        score = min(score, BLOCKING_SCORE_CAP)
    if not failed:
        low = high = 0.0  # nothing to fix
    elif failed <= QUICK_FIX_CHECKS:
        low = high = MIN_ORDER
    else:
        low = max(MIN_ORDER, (pages - scanned) * RATE_TEXT_PAGE + scanned * RATE_SCANNED_PAGE)
        high = low * QUOTE_SPREAD
    return Audit(pages, scanned, score, round(low, 2), round(high, 2), checks)


def _check(id, title, weight, rule, ok, detail, fix, applicable=True) -> Check:
    if not applicable:
        return Check(id, title, weight, rule, "n/a", detail, "")
    return Check(id, title, weight, rule, "pass" if ok else "fail", detail, "" if ok else fix)


def _resources(obj) -> pikepdf.Dictionary:
    target = obj.obj if isinstance(obj, pikepdf.Page) else obj
    return target.get("/Resources", pikepdf.Dictionary())


def _has_text(obj, depth=0) -> bool:
    if pikepdf.parse_content_stream(obj, TEXT_OPERATORS):
        return True
    if depth >= MAX_XOBJECT_DEPTH:
        return False
    xobjects = _resources(obj).get("/XObject", pikepdf.Dictionary())
    return any(x.get("/Subtype") == "/Form" and _has_text(x, depth + 1) for x in xobjects.values())


def _is_scanned(page: pikepdf.Page) -> bool:
    return bool(page.get_images()) and not _has_text(page)


def _tagged(pdf) -> Check:
    mark = pdf.Root.get("/MarkInfo")
    ok = "/StructTreeRoot" in pdf.Root and mark is not None and bool(mark.get("/Marked", False))
    return _check("tagged", "Document is tagged", 25, "WCAG 1.3.1 · PDF/UA-1 §7.1", ok,
                  "Tags tell screen readers what is a heading, paragraph, list or table."
                  if ok else "No tags. Screen readers get one flat stream of text with no headings or tables.",
                  "Add tags to every heading, paragraph, list, table and image, in the order people read them.")


def _scanned_check(scanned: int, pages: int, has_text: bool) -> Check:
    return _check("scanned", "Pages contain real text", 20, "WCAG 1.4.5 · WCAG 1.1.1", scanned == 0,
                  f"{scanned} of {pages} pages are pictures of text with no readable text layer."
                  if scanned else "Every page with text has a readable text layer." if has_text
                  else "No text or scanned images found.",
                  "Turn the scanned pages into real text with OCR, proofread it, then tag it.",
                  applicable=bool(scanned or has_text))


def _figures(pdf) -> list | None:
    tree = pdf.Root.get("/StructTreeRoot")
    if tree is None:
        return None
    rolemap = tree.get("/RoleMap", pikepdf.Dictionary())
    figures, stack, seen = [], [tree.get("/K")], set()
    while stack:
        node = stack.pop()
        if isinstance(node, pikepdf.Array):
            stack.extend(node)
            continue
        if not isinstance(node, pikepdf.Dictionary):
            continue  # marked-content IDs and missing kids
        if node.is_indirect:
            if node.objgen in seen:
                continue
            seen.add(node.objgen)
        tag = node.get("/S")
        if tag is not None and str(rolemap.get(tag, tag)) == "/Figure":
            figures.append(node)
        stack.append(node.get("/K"))
    return figures


def _alt_text(pdf) -> Check:
    args = ("alt_text", "Images have alt text", 12, "WCAG 1.1.1 · PDF/UA-1 §7.3")
    fix = "Write a short description for every meaningful image; mark decorative ones so screen readers skip them."
    images = sum(len(p.get_images()) for p in pdf.pages)
    figures = _figures(pdf)
    if not images and not figures:
        return _check(*args, True, "No images.", fix, applicable=False)
    if figures is None:
        return _check(*args, False, f"{images} images, and none can carry alt text because the PDF has no tags.", fix)
    if not figures:
        return _check(*args, True, f"No tagged figures. {images} images are treated as decoration; "
                      "confirm none of them carry meaning.", fix, applicable=False)
    missing = sum(1 for f in figures if not f.get("/Alt") and not f.get("/ActualText"))
    return _check(*args, missing == 0, f"{missing} of {len(figures)} tagged images have no alt text."
                  if missing else f"All {len(figures)} tagged images have alt text.", fix)


def _title(pdf) -> Check:
    title = str(pdf.docinfo.get("/Title", "")).strip()
    if not title:
        try:
            with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False) as xmp:
                title = str(xmp.get("dc:title") or "").strip()
        except Exception:  # malformed XMP is common in old files; treat as no title
            title = ""
    prefs = pdf.Root.get("/ViewerPreferences")
    shown = prefs is not None and bool(prefs.get("/DisplayDocTitle", False))
    if not title:
        detail = "No document title. Screen readers announce the file name instead."
    elif not shown:
        detail = f'Title "{title}" is set but the viewer is told to show the file name.'
    else:
        detail = f'Title "{title}" is set and shown.'
    return _check("title", "Document title is set and shown", 8, "WCAG 2.4.2 · PDF/UA-1 §7.1",
                  bool(title) and shown, detail,
                  "Set a clear title and make PDF readers show it instead of the file name.")


def _language(pdf) -> Check:
    lang = str(pdf.Root.get("/Lang", "")).strip()
    return _check("language", "Document language is set", 8, "WCAG 3.1.1 · PDF/UA-1 §7.2", bool(lang),
                  f"Language is {lang}." if lang else "No language set, so screen readers may mispronounce the text.",
                  "Set the document language (for example en-US).")


def _fonts(pdf) -> Check:
    seen, not_embedded, unmapped = set(), 0, 0
    for page in pdf.pages:
        for font in _resources(page).get("/Font", pikepdf.Dictionary()).values():
            if font.is_indirect:
                if font.objgen in seen:
                    continue
                seen.add(font.objgen)
            else:
                seen.add(id(font))
            subtype = font.get("/Subtype")
            if subtype == "/Type0":
                descriptor = font.DescendantFonts[0].get("/FontDescriptor")
            else:
                descriptor = font.get("/FontDescriptor")
            if subtype != "/Type3" and (descriptor is None or not any(k in descriptor for k in FONT_FILES)):
                not_embedded += 1
            # ponytail: simple fonts are assumed mappable; symbolic simple fonts slip through until veraPDF runs
            if subtype in ("/Type0", "/Type3") and "/ToUnicode" not in font:
                unmapped += 1
    problems = []
    if not_embedded:
        problems.append(f"{not_embedded} of {len(seen)} fonts are not embedded")
    if unmapped:
        problems.append(f"{unmapped} fonts cannot be turned back into readable text")
    return _check("fonts", "Fonts are embedded and readable", 7, "WCAG 1.3.1 · PDF/UA-1 §7.21", not problems,
                  "; ".join(problems) + "." if problems
                  else f"All {len(seen)} fonts are embedded and mappable." if seen else "No fonts.",
                  "Embed every font and link its characters to real letters, so the text can be read aloud, searched and copied.",
                  applicable=bool(seen))


def _encryption(pdf) -> Check:
    ok = pdf.allow.accessibility
    return _check("encryption", "Security allows screen readers", 5, "PDF/UA-1 §7.16", ok,
                  ("Encryption allows assistive technology to read the content." if ok
                   else "Security settings block screen readers from reading the text.")
                  if pdf.is_encrypted else "The file is not encrypted, so nothing blocks screen readers.",
                  "Re-save with the 'content accessibility' permission turned on, or remove the restrictions.")


def _terminal_fields(pdf) -> list:
    form = pdf.Root.get("/AcroForm")
    stack, fields, seen = list(form.get("/Fields", [])) if form is not None else [], [], set()
    while stack:
        field = stack.pop()
        if field.is_indirect:
            if field.objgen in seen:
                continue
            seen.add(field.objgen)
        kids = [k for k in field.get("/Kids", []) if "/T" in k]
        if kids:
            stack.extend(kids)
        else:
            fields.append(field)
    return fields


def _form_labels(pdf) -> Check:
    fields = _terminal_fields(pdf)
    missing = sum(1 for f in fields if not str(f.get("/TU", "")).strip())
    return _check("form_labels", "Form fields have labels", 5, "WCAG 4.1.2 · PDF/UA-1 §7.18.1", missing == 0,
                  f"{missing} of {len(fields)} form fields have no spoken label." if missing
                  else f"All {len(fields)} form fields have labels." if fields else "No form fields.",
                  "Give every field a spoken label that says what to type, for example 'First name'.",
                  applicable=bool(fields))


def _bookmarks(pdf, pages: int) -> Check:
    outlines = pdf.Root.get("/Outlines")
    ok = outlines is not None and "/First" in outlines
    return _check("bookmarks", "Long document has bookmarks", 5, "WCAG 2.4.5", ok,
                  "Bookmarks let readers jump between sections." if ok
                  else f"{pages} pages and no bookmarks, so readers must scroll page by page."
                  if pages > BOOKMARKS_AFTER_PAGES else f"Only needed for documents over {BOOKMARKS_AFTER_PAGES} pages.",
                  "Add bookmarks that match the headings.", applicable=pages > BOOKMARKS_AFTER_PAGES)


def _tab_order(pdf) -> Check:
    with_annots = [p for p in pdf.pages if len(p.obj.get("/Annots", [])) > 0]
    bad = sum(1 for p in with_annots if p.obj.get("/Tabs") != "/S")
    return _check("tab_order", "Tab order follows the structure", 3, "WCAG 2.4.3 · PDF/UA-1 §7.18.3", bad == 0,
                  f"{bad} of {len(with_annots)} pages with links or fields have no structure-based tab order."
                  if bad else "Tab order follows the document structure." if with_annots
                  else "No links or form fields.",
                  "Set the tab order of every page with links or fields to 'Use document structure'.",
                  applicable=bool(with_annots))


def _pdfua_id(pdf) -> Check:
    meta = pdf.Root.get("/Metadata")
    ok = meta is not None and b"pdfuaid:part" in meta.read_bytes()
    return _check("pdfua_id", "Declares PDF/UA conformance", 2, "PDF/UA-1 §5", ok,
                  "The file declares PDF/UA conformance." if ok
                  else "The file does not declare PDF/UA conformance in its metadata.",
                  "Once everything else is fixed, mark the file as PDF/UA in its document properties.")
