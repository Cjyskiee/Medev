"use strict";
/* MedEvidence frontend. All user/document text is inserted with textContent (never innerHTML). */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const EXAMPLES = ["Type 2 diabetes outcomes in adults", "Malignant brain tumors in adults", "Benign breast tumors in adult women",
  "Pediatric asthma cohort studies", "Treatment of migraine in adults"];
const ASSETS = { logo: ["assets/logo.png", "assets/logo.svg"], hero: ["assets/hero.jpg", "assets/hero.png", "assets/hero.webp"],
  profile: ["assets/profile.jpg", "assets/profile.png"] };
const DEFAULT_PROFILE = { name: "Dr. [Name]", sub: "Physician Â· Researcher" };
let controller = null, busy = false;
const isSignedIn = () => Boolean(window.MedAuth && window.MedAuth.enabled && window.MedAuth.isSignedIn && window.MedAuth.isSignedIn());

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) n.append(k.nodeType ? k : document.createTextNode(String(k)));
  return n;
}
function icon(name) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("class", "ic");
  const u = document.createElementNS("http://www.w3.org/2000/svg", "use"); u.setAttribute("href", "#i-" + name); s.append(u); return s;
}
const fmtTime = iso => { try { return new Date(iso).toLocaleString(); } catch { return iso || ""; } };
const label = v => String(v || "").replace(/_/g, " ");

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const token = window.MedAuth && window.MedAuth.enabled ? await window.MedAuth.getIdToken() : null;
  if (token) headers.Authorization = "Bearer " + token;
  const res = await fetch(path, { ...opts, headers });
  let body = null; try { body = await res.json(); } catch { /* non-JSON error */ }
  return { ok: res.ok, status: res.status, body };
}

/* ---------- Replaceable images ---------- */
function loadFirst(urls) {
  return new Promise(resolve => {
    const next = i => { if (i >= urls.length) return resolve(null);
      const img = new Image(); img.onload = () => resolve(urls[i]); img.onerror = () => next(i + 1); img.src = urls[i] + "?v=" + Date.now(); };
    next(0);
  });
}
async function applyAssets() {
  for (const [key, urls] of Object.entries(ASSETS)) {
    const found = await loadFirst(urls);
    $$(`[data-asset="${key}"]`).forEach(n => {
      if (!found) return;
      if (n.tagName === "IMG") { n.src = found; n.hidden = false; }
      else { n.style.backgroundImage = `url("${found}")`; n.classList.add("has-image"); }
    });
  }
}

/* ---------- Navigation ---------- */
function show(view) {
  $$(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + view));
  $$(".nav button").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  closeMenu(); window.scrollTo(0, 0);
  if (view === "history") loadHistory(); if (view === "documents") loadDocuments(); if (view === "settings") loadSettings();
}
const closeMenu = () => { $("#sidebar").classList.remove("open"); $("#scrim").classList.remove("show"); };
$$(".nav button").forEach(b => b.addEventListener("click", () => show(b.dataset.view)));
$("#menuBtn").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#scrim").classList.add("show"); });
$("#scrim").addEventListener("click", closeMenu);

/* ---------- Profile (editable placeholder, browser-local) ---------- */
function loadProfile() {
  let p = DEFAULT_PROFILE; try { p = { ...p, ...JSON.parse(localStorage.getItem("me_profile") || "{}") }; } catch { /* ignore */ }
  $("#profileName").textContent = p.name || DEFAULT_PROFILE.name; $("#profileSub").textContent = p.sub || DEFAULT_PROFILE.sub;
  $("#setName").value = p.name === DEFAULT_PROFILE.name ? "" : p.name; $("#setSub").value = p.sub === DEFAULT_PROFILE.sub ? "" : p.sub;
}
$("#saveProfile").addEventListener("click", () => {
  const p = { name: $("#setName").value.trim() || DEFAULT_PROFILE.name, sub: $("#setSub").value.trim() || DEFAULT_PROFILE.sub };
  try { localStorage.setItem("me_profile", JSON.stringify(p)); $("#profileSaved").textContent = "Saved."; } catch { $("#profileSaved").textContent = "Could not save in this browser."; }
  loadProfile();
});

/* ---------- Health / status ---------- */
const MODEL_TEXT = { verified: ["ok", "Model: verified"], not_checked: ["warn", "Model: not verified yet"], not_configured: ["bad", "Model: not configured"],
  unreachable: ["bad", "Model: unreachable"], auth_failed: ["bad", "Model: credentials rejected"], rate_limited: ["warn", "Model: rate limited"], error: ["bad", "Model: last call failed"] };
async function refreshHealth(check = false) {
  let h = null;
  try { const r = await api("/api/health" + (check ? "?check_model=true" : "")); h = r.ok ? r.body : null; } catch { h = null; }
  const setDot = (id, cls) => { $(id).className = "dot " + cls; };
  if (!h) { setDot("#dotBackend", "bad"); $("#txtBackend").textContent = "Backend: unreachable"; setDot("#dotModel", "warn"); $("#txtModel").textContent = "Model: unknown"; return null; }
  setDot("#dotBackend", "ok"); $("#txtBackend").textContent = "Backend: connected";
  const [cls, txt] = MODEL_TEXT[h.model.status] || ["warn", "Model: " + h.model.status];
  setDot("#dotModel", cls); $("#txtModel").textContent = txt; return h;
}

/* ---------- Search ---------- */
function buildChips() {
  const box = $("#chips");
  EXAMPLES.forEach(q => box.append(el("button", { class: "chip", type: "button", onclick: () => { $("#queryInput").value = q; syncClear(); runSearch(q); } }, q)));
}
const syncClear = () => { $("#clearBtn").hidden = !$("#queryInput").value; };
$("#queryInput").addEventListener("input", syncClear);
$("#clearBtn").addEventListener("click", () => { if (controller) controller.abort(); $("#queryInput").value = ""; $("#results").replaceChildren(); setBusy(false); syncClear(); $("#queryInput").focus(); });
$("#searchForm").addEventListener("submit", e => { e.preventDefault(); runSearch($("#queryInput").value); });
function setBusy(b) { busy = b; $("#goBtn").disabled = b; }

async function runSearch(query) {
  query = (query || "").trim();
  if (query.length < 3) { renderNotice("error", "Question too short", "Enter a question between 3 and 500 characters."); return; }
  if (busy) { if (controller) controller.abort(); }           // a new search replaces the previous one
  controller = new AbortController(); const mine = controller; setBusy(true);
  $("#results").replaceChildren(el("div", { class: "card loading" }, el("div", { class: "spinner" }), "Retrieving records and validating evidenceâ€¦"));
  try {
    const r = await api("/api/search", { method: "POST", body: JSON.stringify({ query }), signal: mine.signal });
    if (mine.signal.aborted) return;
    if (r.status === 401 || r.status === 403) {
      renderNotice("error", isSignedIn() ? "Please sign in again" : "Sign in to search",
        isSignedIn() ? "Your session has expired. Sign in, then run the search again." : "Search results are limited to signed-in users with a verified email.");
      return;
    }
    if (!r.body || !r.body.status) throw new Error("bad");
    renderResult(r.body);
  } catch (err) {
    if (mine.signal.aborted) return;
    renderNotice("error", "Cannot reach the backend", "The request failed. Check that the MedEvidence server is running, then try again.");
  } finally { if (controller === mine) setBusy(false); refreshHealth(); }
}

function renderNotice(kind, title, text, extra) {
  const box = $("#results");
  const card = el("div", { class: "card notice " + kind }, icon("alert"), el("div", {}, el("h3", {}, title), el("p", {}, text), extra));
  box.replaceChildren(card);
}

function renderResult(r) {
  const box = $("#results"); box.replaceChildren();
  if (r.status === "no_context") {
    box.append(el("div", { class: "card notice nocontext" }, icon("alert"), el("div", {},
      el("h3", {}, r.message), el("p", {}, [r.detail, r.suggestion].filter(Boolean).join(" ")))));
    if (r.excluded && r.excluded.length) box.append(excludedPanel(r.excluded));
    return;
  }
  if (r.status === "error") {
    box.append(el("div", { class: "card notice error" }, icon("alert"), el("div", {},
      el("h3", {}, r.error_code === "invalid_query" ? "Check your question" : "The answer could not be generated"), el("p", {}, [r.message, r.detail].filter(Boolean).join(" ")))));
    if (r.sources && r.sources.length) { box.append(el("div", { class: "section-title" }, "Retrieved evidence")); r.sources.forEach(s => box.append(evidenceCard(s))); }
    return;
  }
  const ans = el("div", { class: "card answer" }, el("div", { class: "status ok" }, icon("shield"), "Supported by retrieved records"),
    el("p", { class: "summary" }, r.answer));
  if (r.key_findings.length) ans.append(el("ul", { class: "findings" }, r.key_findings.map(f =>
    el("li", {}, f.text, f.source_ids.map(id => el("button", { class: "badge", type: "button", onclick: () => openDoc(id) }, id))))));
  if (r.limitations.length) ans.append(el("p", { class: "limits" }, "Limitations: " + r.limitations.join(" ")));
  ans.append(el("p", { class: "disclaimer" }, "Research summary from synthetic records only. Not a diagnosis or treatment recommendation."));
  box.append(ans, el("div", { class: "section-title" }, `Evidence (${r.sources.length})`));
  r.sources.forEach(s => box.append(evidenceCard(s)));
  if (r.excluded && r.excluded.length) box.append(excludedPanel(r.excluded));
}

function evidenceCard(s) {
  const dl = el("dl", { class: "meta" });
  [["Diagnosis", s.diagnosis], ["Classification", label(s.condition_classification)], ["Patient group", label(s.patient_group)],
   ["Study type", s.study_type], ["Source", s.source_name], ["Location", s.location]].forEach(([k, v]) => dl.append(el("div", {}, el("dt", {}, k), el("dd", {}, v))));
  return el("article", { class: "card" },
    el("div", { class: "evidence-head" }, el("h3", {}, s.title), el("span", { class: "id-chip" }, s.document_id)), dl,
    el("blockquote", { class: "excerpt" }, s.excerpt),
    el("div", { class: "actions" }, el("button", { class: "btn", type: "button", onclick: () => openDoc(s.document_id) }, icon("file"), "View source record"),
      el("details", { class: "why" }, el("summary", {}, "Why it matched", icon("chevron")), el("ul", {}, (s.match_reasons || []).map(x => el("li", {}, x))))));
}

function excludedPanel(list) {
  return el("details", { class: "card why excluded", open: "" }, el("summary", {}, `Excluded records (${list.length}) â€” similar topic, conflicting attributes`, icon("chevron")),
    el("ul", {}, list.map(e => el("li", {}, el("strong", {}, e.document_id + ": "), e.reasons.join("; ")))));
}

/* ---------- Source modal ---------- */
async function openDoc(id) {
  const r = await api("/api/documents/" + encodeURIComponent(id));
  const body = $("#modalBody"); body.replaceChildren();
  if (!r.ok) {
    $("#modalTitle").textContent = "Record unavailable";
    body.append(el("p", {}, r.status === 401 || r.status === 403 ? "Sign in to open this record." : "This record could not be loaded."));
  }
  else {
    const d = r.body; $("#modalTitle").textContent = d.title;
    const dl = el("dl", { class: "meta" });
    [["Document ID", d.document_id], ["Type", label(d.document_type)], ["Diagnosis", d.diagnosis], ["Classification", label(d.condition_classification)],
     ["Patient group", label(d.patient_group)], ["Study type", d.study_type], ["Source", d.source_name], ["Location", d.source_location], ["Created", d.created_at]]
      .forEach(([k, v]) => dl.append(el("div", {}, el("dt", {}, k), el("dd", {}, v))));
    body.append(dl, el("h4", {}, "Summary"), el("p", {}, d.summary), el("h4", {}, "Findings"), el("ul", {}, d.findings.map(f => el("li", {}, f))),
      el("h4", {}, "Keywords"), el("p", {}, d.keywords.join(", ")));
    if (d.synthetic) body.append(el("p", { class: "muted small" }, "Synthetic record. Contains no real patient information."));
  }
  const dlg = $("#docModal"); if (!dlg.open) dlg.showModal();
}
$("#modalClose").addEventListener("click", () => $("#docModal").close());
$("#docModal").addEventListener("click", e => { if (e.target.id === "docModal") e.target.close(); });

/* ---------- History ---------- */
async function loadHistory() {
  const list = $("#historyList"); const r = await api("/api/history");
  if (!r.ok) { list.replaceChildren(el("div", { class: "empty" }, "History could not be loaded.")); return; }
  const items = r.body.items;
  if (!items.length) { list.replaceChildren(el("div", { class: "empty" }, "No searches yet. Your searches will appear here.")); return; }
  list.replaceChildren(...items.map(i => el("button", { class: "row-item", type: "button", onclick: () => { show("search"); $("#queryInput").value = i.query; syncClear(); renderResult(i.result); } },
    el("div", {}, el("div", { class: "t" }, i.query), el("div", { class: "s" }, fmtTime(i.timestamp) + (i.source_ids.length ? " Â· " + i.source_ids.join(", ") : ""))),
    el("span", { class: "tag" }, label(i.status)))));
}
$("#clearHistoryBtn").addEventListener("click", async () => { if (confirm("Clear all search history?")) { await api("/api/history", { method: "DELETE" }); loadHistory(); } });

/* ---------- Documents ---------- */
// Shows a sign-in prompt instead of protected document content.
function signInPrompt(target, text) {
  target.replaceChildren(el("div", { class: "empty" },
    el("p", {}, text),
    el("button", { class: "btn", type: "button", onclick: () => window.MedAuth && window.MedAuth.open() }, "Sign in")));
}

// Reads the title and author headers from a .txt or Markdown record and returns the body.
function parseTextRecord(fileName, raw) {
  const lines = raw.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").split("\n");
  let title = "", author = "";
  const body = [];
  lines.forEach((line, index) => {
    const trimmed = line.trim();
    const meta = trimmed.match(/^(title|author|by)\s*:\s*(.+)$/i);
    const heading = trimmed.match(/^#{1,6}\s+(.+)$/);
    if (index < 8 && !title && heading) { title = heading[1].trim(); return; }
    if (index < 8 && !title && meta && /^title$/i.test(meta[1])) { title = meta[2].trim(); return; }
    if (index < 8 && !author && meta && /^(author|by)$/i.test(meta[1])) { author = meta[2].trim(); return; }
    body.push(line);
  });
  if (!title) title = fileName.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim();
  return { title, author, text: body.join("\n").trim() };
}

async function loadDocuments() {
  const list = $("#docList");
  if (!isSignedIn()) { signInPrompt(list, "Sign in to view the document collection."); return; }
  const r = await api("/api/documents");
  if (r.status === 401 || r.status === 403) { signInPrompt(list, "Sign in to view the document collection."); return; }
  if (!r.ok) { list.replaceChildren(el("div", { class: "empty" }, "Documents could not be loaded.")); return; }
  if (!r.body.documents.length) { list.replaceChildren(el("div", { class: "empty" }, "The document collection is empty. Upload a .txt, .md or .json record to add one.")); return; }
  list.replaceChildren(...r.body.documents.map(d => el("button", { class: "row-item", type: "button", onclick: () => openDoc(d.document_id) },
    el("div", {}, el("div", { class: "t" }, d.title), el("div", { class: "s" }, `${d.document_id} Â· ${d.diagnosis} Â· ${label(d.patient_group)} Â· ${d.study_type}`)),
    el("span", { class: "tag " + d.condition_classification }, label(d.condition_classification)))));
}
$("#uploadBtn").addEventListener("click", () => {
  if (!isSignedIn()) { signInPrompt($("#docList"), "Sign in to upload records."); return; }
  $("#uploadInput").click();
});
$("#uploadInput").addEventListener("change", async e => {
  const file = e.target.files[0]; e.target.value = ""; const msg = $("#uploadMsg"); msg.replaceChildren(); if (!file) return;
  const fail = (title, items) => msg.append(el("div", { class: "card notice error" }, icon("alert"), el("div", {}, el("h3", {}, title), items && el("ul", {}, items.map(x => el("li", {}, x))))));
  if (!/\.(txt|md|markdown|json|jsonl)$/i.test(file.name)) return fail("Unsupported file type", ["Use a .txt, .md, .json or .jsonl file."]);
  if (file.size > 1_000_000) return fail("File is larger than 1 MB.");
  const text = await file.text();
  let records;
  if (/\.(json|jsonl)$/i.test(file.name)) {
    try {
      records = /\.jsonl$/i.test(file.name) ? text.split(/\r?\n/).filter(l => l.trim()).map(l => JSON.parse(l)) : JSON.parse(text);
    } catch { return fail("The file is not valid JSON."); }
    if (!Array.isArray(records)) records = [records];
  } else {
    const record = parseTextRecord(file.name, text);
    if (record.text.length < 40) return fail("Not enough text", ["Put the record body below the title, at least a short paragraph."]);
    records = [record];
  }
  const r = await api("/api/documents", { method: "POST", body: JSON.stringify({ documents: records }) });
  if (r.ok) { msg.append(el("div", { class: "card" }, `Added ${r.body.count} document(s): ${r.body.added.join(", ")}`)); loadDocuments(); }
  else if (r.status === 401 || r.status === 403) signInPrompt($("#docList"), "Sign in to upload records.");
  else fail("Upload rejected", (r.body && r.body.errors) || ["The server rejected the file."]);
});

/* ---------- Settings ---------- */
async function loadSettings() {
  const h = await refreshHealth(); const sb = $("#statusBox"), cb = $("#collectionBox");
  const kv = (box, rows) => box.replaceChildren(...rows.flatMap(([k, v]) => [el("span", {}, k), el("span", {}, v)]));
  if (!h) { kv(sb, [["Backend", "Unreachable"], ["Model API", "Unknown (backend not reachable)"]]); cb.replaceChildren(); return; }
  kv(sb, [["Application", "MedEvidence v" + h.version], ["Backend", "Connected"], ["Model ID", h.model.model_id || "Not set"],
    ["Model API", (MODEL_TEXT[h.model.status] || [0, h.model.status])[1].replace("Model: ", "") + (h.model.detail ? " â€” " + h.model.detail : "")]]);
  kv(cb, [["Total records", h.documents.total], ["Built-in synthetic", h.documents.seed], ["Uploaded", h.documents.uploaded],
    ["Relevance threshold", h.retrieval.min_relevance], ["Load warnings", h.documents.warnings.length || "None"]]);
}
$("#testModel").addEventListener("click", async () => { const b = $("#testModel"); b.disabled = true; b.textContent = "Testingâ€¦"; await loadSettingsCheck(); b.disabled = false; b.textContent = "Test model connection"; });
async function loadSettingsCheck() { await refreshHealth(true); await loadSettings(); }

/* ---------- Init ---------- */
// Reloads protected views when the signed-in account changes.
window.addEventListener("medev:auth", () => {
  if ($("#docModal").open) $("#docModal").close();
  if ($("#view-documents").classList.contains("active")) loadDocuments();
});
buildChips(); loadProfile(); applyAssets(); refreshHealth(); setInterval(() => refreshHealth(), 30000);
