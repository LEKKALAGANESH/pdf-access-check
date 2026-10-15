"use strict";

const MAX_MB = 25;
const MAX_FILES = 20; // matches BATCH_MAX in app.py
const FREE_CHECKS = 30; // matches AUDIT_LIMIT in app.py: files per network per 10 minutes
const STATUS_ORDER = { fail: 0, pass: 1, "n/a": 2 };
const STATUS_LABEL = { fail: "Fails", pass: "Passes", "n/a": "Not needed" };
const STATUS_CLASS = { fail: "is-fail", pass: "is-pass", "n/a": "is-na" };
const REPORT_PATH = /^\/r\/([0-9a-f-]{36})$/i;
const OFFLINE = "Could not reach the server. Check your connection and try again.";
// Whole dollars stay "$25"; anything with cents shows them ("$37.50") so the page matches the quote.
const money = (n) => n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: n % 1 ? 2 : 0 });

const $ = (id) => document.getElementById(id);
const els = {
  form: $("upload-form"), file: $("file"), status: $("status"),
  uploadError: $("upload-error"), uploadErrorText: $("upload-error-text"),
  batch: $("batch"), batchSummary: $("batch-summary"), batchRows: $("batch-rows"),
  batchScroll: $("batch-scroll"), tableHint: $("table-hint"), reportMeta: $("report-meta"),
  report: $("report"), stamp: $("stamp"), score: $("score"), verdict: $("verdict"),
  filename: $("filename"), summary: $("summary"), checks: $("checks"), reportTitle: $("report-title"),
  copyLink: $("copy-link"), printReport: $("print-report"), shareStatus: $("share-status"),
  quote: $("quote"), quoteTitle: $("quote-title"), priceBasis: $("price-basis"),
  leadForm: $("lead-form"), leadError: $("lead-error"), leadSubmit: $("lead-submit"), leadDone: $("lead-done"),
};
let files = []; // the current round: { name, result } or { name, error }, in upload order
let shown = null; // the entry whose report is on screen
let latestUpload = 0; // only the newest round may change the page

const track = (event) => window.plausible?.(event); // a no-op unless analytics is switched on

function show(el, message) {
  el.textContent = message;
  el.hidden = false;
}

function uploadFailed(message) {
  els.uploadErrorText.textContent = message;
  els.uploadError.hidden = false;
  els.uploadError.scrollIntoView({ block: "nearest" }); // the previous report stays below, so keep the error in view
}

function setBusy(message) {
  els.status.textContent = message;
  els.status.classList.toggle("is-busy", Boolean(message));
}

async function readError(res) {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch { /* fall through to the generic message */ }
  return `The server returned an error (${res.status}). Please try again.`;
}

function rejectReason(file) {
  if (!/\.pdf$/i.test(file.name) && file.type !== "application/pdf") return "That file is not a PDF. Choose a file that ends in .pdf.";
  if (file.size > MAX_MB * 1024 * 1024) return `That file is larger than ${MAX_MB} MB. Email it to us for a quote instead.`;
  return "";
}

async function checkFile(file) {
  const reason = rejectReason(file);
  if (reason) return { name: file.name, error: reason };
  const data = new FormData();
  data.append("file", file);
  try {
    const res = await fetch("/api/audit", { method: "POST", body: data });
    if (res.ok) return { name: file.name, result: await res.json() };
    // 429 = the free-check limit; the server's message says which limit and when to try again.
    return { name: file.name, error: await readError(res), limited: res.status === 429 };
  } catch {
    return { name: file.name, error: OFFLINE };
  }
}

async function checkFiles(list) {
  const picked = [...list];
  els.file.value = "";
  if (!picked.length) return;
  const ticket = ++latestUpload;
  els.uploadError.hidden = true;
  const batch = picked.slice(0, MAX_FILES);
  const round = [];
  let limitNotice = "";
  for (const [i, file] of batch.entries()) {
    setBusy(batch.length > 1 ? `Checking ${i + 1} of ${batch.length}: ${file.name}…` : `Checking ${file.name}…`);
    const entry = await checkFile(file);
    if (ticket !== latestUpload) return; // a newer upload replaced this one while it was running
    round.push(entry);
    if (entry.limited) {
      // Every later file would hit the same limit, so stop and say which files are still waiting.
      limitNotice = entry.error;
      entry.error = "Not checked: limit reached. See the message above.";
      for (const rest of batch.slice(i + 1)) round.push({ name: rest.name, error: "Not checked yet. See the message above." });
      break;
    }
    if (batch.length > 1) renderBatch(round, batch.length);
  }
  setBusy("");
  const ok = round.filter((e) => e.result);
  if (batch.length === 1) {
    if (!ok.length) return uploadFailed(limitNotice || round[0].error); // the previous report stays
    els.batch.hidden = true;
  } else if (!ok.length) {
    els.report.hidden = els.quote.hidden = true;
    renderBatch(round, batch.length);
    return uploadFailed(limitNotice || "None of these files could be checked. The table shows why.");
  }
  files = round;
  showReport(ok[0], batch.length === 1 && !limitNotice);
  if (batch.length > 1) renderBatch(round, batch.length);
  renderQuote(quoteFor(ok));
  if (limitNotice) uploadFailed(`Checked ${ok.length} of ${batch.length} files. ${limitNotice}`);
  if (picked.length > MAX_FILES) {
    els.status.textContent = `Checked the first ${MAX_FILES} files. Upload the other ${picked.length - MAX_FILES} as a second batch. ` +
      `The free check takes up to ${FREE_CHECKS} files every 10 minutes; if you reach that, the page tells you when to continue.`;
  }
  track("Check done");
}

function verdictFor(score) {
  if (score === 100) return ["Passes these checks", "is-good"];
  if (score >= 85) return ["Nearly there", "is-good"];
  if (score >= 50) return ["Needs work", "is-close"];
  return ["Not accessible", ""];
}

function priceText({ quote_low: low, quote_high: high }) {
  if (!high) return "Passes";
  return low === high ? money(low) : `${money(low)}–${money(high)}`;
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function batchRow(entry) {
  const tr = document.createElement("tr");
  const name = document.createElement("th");
  name.scope = "row";
  if (!entry.result) {
    name.textContent = entry.name;
    const reason = cell(entry.error);
    reason.colSpan = 3;
    reason.className = "is-error";
    tr.append(name, reason);
    return tr;
  }
  const view = document.createElement("button");
  view.type = "button";
  view.className = "link-button";
  view.textContent = entry.name;
  if (entry === shown) view.setAttribute("aria-current", "true");
  view.addEventListener("click", () => {
    showReport(entry, true);
    renderBatch(files, files.length);
  });
  name.append(view);
  tr.append(name, cell(entry.result.pages), cell(`${entry.result.score}/100`), cell(priceText(entry.result)));
  return tr;
}

function renderBatch(entries, total) {
  els.batchRows.replaceChildren(...entries.map(batchRow));
  const checked = entries.filter((e) => e.result).length;
  const failed = entries.length - checked;
  const done = entries.length < total ? `${entries.length} of ${total} files done` : `${checked} of ${total} files checked`;
  els.batchSummary.textContent = `${done}${failed ? `, ${failed} not checked` : ""}. Choose a file to see its report.`;
  els.batch.hidden = false;
  updateTableHint();
}

// The hint only shows when the table is wider than the screen, i.e. there really is more to scroll to.
function updateTableHint() {
  els.tableHint.hidden = els.batch.hidden || els.batchScroll.scrollWidth <= els.batchScroll.clientWidth;
}

function checkItem(check) {
  const li = document.createElement("li");
  li.className = `check ${STATUS_CLASS[check.status]}`;
  const status = document.createElement("span");
  status.className = "check-status";
  status.textContent = STATUS_LABEL[check.status];
  const body = document.createElement("div");
  body.className = "check-body";
  const title = document.createElement("h3");
  title.className = "check-title";
  title.textContent = check.title;
  const detail = document.createElement("p");
  detail.textContent = check.detail;
  body.append(title, detail);
  if (check.fix) {
    const fix = document.createElement("p");
    fix.className = "check-fix";
    const label = document.createElement("strong");
    label.textContent = "How we fix it: ";
    fix.append(label, check.fix);
    body.append(fix);
  }
  const rule = document.createElement("p");
  rule.className = "check-rule";
  rule.textContent = check.rule;
  body.append(rule);
  li.append(status, body);
  return li;
}

function showReport(entry, moveFocus) {
  shown = entry;
  const { result } = entry;
  const [verdict, tone] = verdictFor(result.score);
  els.score.textContent = result.score;
  els.verdict.textContent = verdict;
  els.stamp.className = `stamp ${tone} is-new`;
  els.filename.textContent = entry.name;

  const fails = result.checks.filter((c) => c.status === "fail").length;
  const pages = `${result.pages} ${result.pages === 1 ? "page" : "pages"}`;
  const scanned = result.scanned_pages ? `, ${result.scanned_pages} of them scanned images` : "";
  const problems = fails ? `${fails} ${fails === 1 ? "problem" : "problems"} found.` : "No problems found by this check.";
  els.summary.textContent = `${pages}${scanned}. ${problems}`;

  const sorted = [...result.checks].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]);
  els.checks.replaceChildren(...sorted.map(checkItem));
  els.shareStatus.textContent = "";
  // Shown only on paper, so a printed report says when it was made and where the live one is.
  const checkedOn = result.checked_at
    ? `Checked on ${new Date(result.checked_at).toLocaleDateString("en-US", { dateStyle: "long" })}. ` : "";
  els.reportMeta.textContent = `${checkedOn}Online report: ${location.origin}/r/${result.audit_id}`;
  els.report.hidden = false;
  if (moveFocus) els.reportTitle.focus();
  // The address bar always points at the report on screen, so a reload or a shared link reopens it.
  const path = `/r/${result.audit_id}`;
  if (location.pathname !== path) history.replaceState(null, "", path);
}

function quoteText(result) {
  const { quote_low: low, quote_high: high, pages, scanned_pages: scanned } = result;
  if (!high) {
    return ["This file passes our free check", "Request a review",
      "Want proof before you publish? We can review it by hand with PAC and veraPDF and send you the reports. Leave your details and we'll email a price."];
  }
  const price = document.createElement("span");
  price.className = "price";
  price.textContent = priceText(result);
  if (low === high) {
    return [["Get this file fixed for ", price], "Request the fix",
      "Only document settings need fixing (title, language, tab order, security or the PDF/UA flag), so this is a flat-rate job. You get a confirmed price before any work starts."];
  }
  const textPages = pages - scanned;
  const parts = [];
  if (textPages) parts.push(`${textPages} text ${textPages === 1 ? "page" : "pages"} at $1.50`);
  if (scanned) parts.push(`${scanned} scanned ${scanned === 1 ? "page" : "pages"} at $3.00`);
  return [["Get this file fixed for ", price], "Request the fix",
    `Based on ${parts.join(" and ")}, minimum order $25. The higher end covers complex tables and forms. You get a confirmed price before any work starts.`];
}

function quoteFor(entries) {
  if (entries.length === 1) return quoteText(entries[0].result);
  const low = entries.reduce((sum, e) => sum + e.result.quote_low, 0);
  const high = entries.reduce((sum, e) => sum + e.result.quote_high, 0);
  const passing = entries.filter((e) => !e.result.quote_high).length;
  if (!high) {
    return [`These ${entries.length} files pass our free check`, "Request a review",
      "Want proof before you publish? We can review them by hand with PAC and veraPDF and send you the reports. Leave your details and we'll email a price."];
  }
  const price = document.createElement("span");
  price.className = "price";
  price.textContent = low === high ? money(low) : `${money(low)}–${money(high)}`;
  const free = passing ? ` ${passing} ${passing === 1 ? "file passes" : "files pass"} and ${passing === 1 ? "costs" : "cost"} nothing.` : "";
  const needFix = entries.length - passing;
  return [[`Get ${needFix === 1 ? "1 file" : `${needFix} files`} fixed for `, price], "Request the fix",
    `The total of each file's price, each with a $25 minimum.${free} You get a confirmed price before any work starts, and large batches usually come out lower.`];
}

function renderQuote([title, action, basis]) {
  els.quoteTitle.replaceChildren(...[title].flat());
  els.priceBasis.textContent = basis;
  els.leadSubmit.dataset.label = action;
  els.leadSubmit.textContent = action;
  els.leadForm.hidden = false;
  els.leadDone.hidden = true;
  els.leadError.hidden = true;
  els.quote.hidden = false;
}

function validateLead(form) {
  const problems = [];
  for (const id of ["name", "email", "organization"]) {
    const input = form.elements[id];
    const ok = id === "email" ? /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.value.trim()) : input.value.trim() !== "";
    input.setAttribute("aria-invalid", String(!ok));
    if (!ok) problems.push(form.querySelector(`label[for="${id}"]`).textContent.toLowerCase());
  }
  return problems;
}

async function submitLead(event) {
  event.preventDefault();
  const form = els.leadForm;
  els.leadError.hidden = true;
  const problems = validateLead(form);
  if (problems.length) {
    show(els.leadError, `Please check: ${problems.join(", ")}.`);
    form.querySelector('[aria-invalid="true"]').focus();
    return;
  }
  const ids = files.filter((e) => e.result).map((e) => e.result.audit_id);
  const payload = { ...Object.fromEntries(new FormData(form)), audit_id: ids[0], more_audit_ids: ids.slice(1) };
  els.leadSubmit.disabled = true;
  els.leadSubmit.textContent = "Sending…";
  try {
    const res = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      show(els.leadError, await readError(res));
      return;
    }
    form.hidden = true;
    els.leadDone.hidden = false;
    els.leadDone.focus();
    track("Lead sent");
  } catch {
    show(els.leadError, OFFLINE);
  } finally {
    els.leadSubmit.disabled = false;
    els.leadSubmit.textContent = els.leadSubmit.dataset.label;
  }
}

async function copyReportLink() {
  const url = `${location.origin}/r/${shown.result.audit_id}`;
  try {
    await navigator.clipboard.writeText(url);
    els.shareStatus.textContent = "Link copied. Anyone with it can open this report.";
  } catch {
    els.shareStatus.textContent = `Copy this link: ${url}`;
  }
}

async function openSharedReport(id) {
  const ticket = ++latestUpload;
  setBusy("Opening the report…");
  try {
    const res = await fetch(`/api/audit/${id}`);
    const outcome = res.ok ? await res.json() : await readError(res);
    if (ticket !== latestUpload) return;
    if (!res.ok) {
      history.replaceState(null, "", "/");
      return uploadFailed(outcome);
    }
    files = [{ name: outcome.filename, result: outcome }];
    showReport(files[0], false);
    renderQuote(quoteFor(files));
  } catch {
    if (ticket === latestUpload) uploadFailed(OFFLINE);
  } finally {
    if (ticket === latestUpload) setBusy("");
  }
}

els.file.addEventListener("change", () => checkFiles(els.file.files));
els.form.addEventListener("submit", (e) => e.preventDefault());
els.form.addEventListener("dragover", (e) => {
  e.preventDefault();
  els.form.classList.add("is-over");
});
els.form.addEventListener("dragleave", () => els.form.classList.remove("is-over"));
els.form.addEventListener("drop", (e) => {
  e.preventDefault();
  els.form.classList.remove("is-over");
  checkFiles(e.dataTransfer.files);
});
els.leadForm.addEventListener("submit", submitLead);
els.copyLink.addEventListener("click", copyReportLink);
els.printReport.addEventListener("click", () => window.print());
window.addEventListener("resize", updateTableHint);

const sharedId = location.pathname.match(REPORT_PATH)?.[1];
if (sharedId) openSharedReport(sharedId);
