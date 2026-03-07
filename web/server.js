// web/server.js (ESM; package.json has "type": "module")
import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const fetchFn = global.fetch;

const API_BASE = (process.env.API_BASE || process.env.OPSCLAW_API || "http://api:8000").replace(/\/+$/, "");
const PORT = parseInt(process.env.PORT || "80", 10);

const app = express();
app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));

app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// ---- minimal cookie parser (no deps) ----
function parseCookieHeader(cookieHeader) {
  const out = {};
  if (!cookieHeader) return out;
  for (const part of cookieHeader.split(";")) {
    const i = part.indexOf("=");
    if (i < 0) continue;
    const k = part.slice(0, i).trim();
    const v = part.slice(i + 1).trim();
    if (!k) continue;
    try { out[k] = decodeURIComponent(v); } catch { out[k] = v; }
  }
  return out;
}
app.use((req, _res, next) => {
  req.cookies = parseCookieHeader(req.headers.cookie || "");
  next();
});

function setCookie(res, name, value, opts = {}) {
  const maxAge = opts.maxAgeMs ? Math.floor(opts.maxAgeMs / 1000) : null;
  const sameSite = opts.sameSite || "Lax";
  const pathOpt = opts.path || "/";
  const httpOnly = !!opts.httpOnly;

  let cookie = `${name}=${encodeURIComponent(value || "")}; Path=${pathOpt}; SameSite=${sameSite}`;
  if (maxAge !== null) cookie += `; Max-Age=${maxAge}`;
  if (httpOnly) cookie += `; HttpOnly`;
  res.append("Set-Cookie", cookie);
}

function authHeaders(req) {
  const token = (req.cookies.opsclaw_token || "").trim();
  const actor = (req.cookies.opsclaw_actor || "").trim();
  const headers = {};
  if (token) headers["x-opsclaw-token"] = token;
  if (actor) headers["x-opsclaw-actor"] = actor;
  return headers;
}

async function apiFetch(req, urlPath, opts = {}) {
  const url = urlPath.startsWith("http") ? urlPath : `${API_BASE}${urlPath}`;
  const headers = Object.assign(
    { "content-type": "application/json" },
    authHeaders(req),
    (opts.headers || {})
  );

  const res = await fetchFn(url, Object.assign({}, opts, { headers }));
  const text = await res.text();

  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  return { ok: res.ok, status: res.status, data, raw: text };
}

// ---------------- Auth save ----------------
app.post("/auth/save", (req, res) => {
  const token = (req.body.token || "").trim();
  const actor = (req.body.actor || "").trim();
  const maxAgeMs = 30 * 24 * 3600 * 1000;

  setCookie(res, "opsclaw_token", token, { maxAgeMs, sameSite: "Lax", path: "/", httpOnly: false });
  setCookie(res, "opsclaw_actor", actor, { maxAgeMs, sameSite: "Lax", path: "/", httpOnly: false });

  const next = (req.body.next || req.query.next || "/").toString();
  return res.redirect(next);
});

// ---------------- Home ----------------
app.get("/", async (req, res) => {
  res.render("index", {
    api: API_BASE,
    token: req.cookies.opsclaw_token || "",
    actor: req.cookies.opsclaw_actor || "",
    created: null,
    loaded: null,
    workflow: null,
    error: null,
  });
});

// ---------------- Projects ----------------
app.post("/projects/create", async (req, res) => {
  const request_text = (req.body.request_text || "basic health check").toString();
  const payload = { project_type: "generic", targets: [], request_text };

  let error = null, created = null;
  try {
    const r = await apiFetch(req, "/projects", { method: "POST", body: JSON.stringify(payload) });
    if (!r.ok) error = `API ${r.status}: ${typeof r.data === "string" ? r.data : JSON.stringify(r.data)}`;
    else created = r.data;
  } catch (e) {
    error = `Create failed: ${e?.message || e}`;
  }

  res.render("index", {
    api: API_BASE,
    token: req.cookies.opsclaw_token || "",
    actor: req.cookies.opsclaw_actor || "",
    created,
    loaded: null,
    workflow: null,
    error,
    last_request_text: request_text,
  });
});

app.post("/projects/load", async (req, res) => {
  const project_id = (req.body.project_id || "").toString().trim();

  let error = null, loaded = null;
  try {
    const r = await apiFetch(req, `/projects/${encodeURIComponent(project_id)}`, { method: "GET" });
    if (!r.ok) error = `API ${r.status}: ${typeof r.data === "string" ? r.data : JSON.stringify(r.data)}`;
    else loaded = r.data;
  } catch (e) {
    error = `Load failed: ${e?.message || e}`;
  }

  res.render("index", {
    api: API_BASE,
    token: req.cookies.opsclaw_token || "",
    actor: req.cookies.opsclaw_actor || "",
    created: null,
    loaded,
    workflow: null,
    error,
    last_project_id: project_id,
  });
});

app.post("/projects/run_workflow", async (req, res) => {
  const project_id = (req.body.project_id || "").toString().trim();
  const request_text = (req.body.workflow_request || "basic system snapshot").toString();
  const timeout_s = parseInt((req.body.timeout_s || "60").toString(), 10) || 60;
  const max_retries = parseInt((req.body.max_retries || "2").toString(), 10) || 2;

  let error = null, workflow = null;
  try {
    const payload = { request_text, timeout_s, max_retries };
    const r = await apiFetch(req, `/projects/${encodeURIComponent(project_id)}/run_workflow`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!r.ok) error = `API ${r.status}: ${typeof r.data === "string" ? r.data : JSON.stringify(r.data)}`;
    else workflow = r.data;
  } catch (e) {
    error = `Workflow failed: ${e?.message || e}`;
  }

  res.render("index", {
    api: API_BASE,
    token: req.cookies.opsclaw_token || "",
    actor: req.cookies.opsclaw_actor || "",
    created: null,
    loaded: null,
    workflow,
    error,
    last_workflow_project_id: project_id,
    last_workflow_request: request_text,
    last_timeout_s: timeout_s,
    last_max_retries: max_retries,
  });
});

// ---------------- MasterGate ----------------
async function renderMasterGate(req, res, extra = {}) {
  const include_archived = req.query.include_archived === "true";
  const only_archived = req.query.only_archived === "true";
  const sel = (req.query.sel || "").toString().trim();

  let approvals = [];
  let selected = null;
  let settings = null;
  let error = null;

  try {
    const qs = new URLSearchParams();
    if (include_archived) qs.set("include_archived", "true");
    if (only_archived) qs.set("only_archived", "true");
    const r = await apiFetch(req, `/approvals?${qs.toString()}`, { method: "GET" });
    if (!r.ok) throw new Error(`approvals API ${r.status}: ${r.raw}`);
    approvals = (r.data && r.data.items) ? r.data.items : [];
  } catch (e) {
    error = e?.message || String(e);
  }

  if (sel) {
    try {
      const r3 = await apiFetch(req, `/approvals/${encodeURIComponent(sel)}`, { method: "GET" });
      if (r3.ok) selected = r3.data;
    } catch (_) {}
  }

  try {
    const r2 = await apiFetch(req, "/settings/status", { method: "GET" });
    settings = r2.ok ? r2.data : { error: r2.raw || `HTTP ${r2.status}` };
  } catch (e) {
    settings = { error: e?.message || String(e) };
  }

  return res.render("mastergate", {
    api: API_BASE,
    approvals,
    selected,
    created: extra.created || null,
    settings,
    error: extra.error || error,
    include_archived,
    only_archived,
    token: req.cookies.opsclaw_token || "",
    actor: req.cookies.opsclaw_actor || "",
  });
}

app.get("/mastergate", async (req, res) => renderMasterGate(req, res));
app.get("/mastergate/", async (req, res) => renderMasterGate(req, res));

app.post("/mastergate/request", async (req, res) => {
  const payload = {
    title: req.body.title || "Ask Master",
    draft_prompt: req.body.draft_prompt || "",
    context_snippets: req.body.context_snippets || "",
    require_approval: true,
  };
  try {
    const r = await apiFetch(req, "/mastergate/request", { method: "POST", body: JSON.stringify(payload) });
    if (!r.ok) return renderMasterGate(req, res, { error: `API ${r.status}: ${r.raw}` });
    return res.redirect(`/mastergate?sel=${encodeURIComponent(r.data.approval_id)}`);
  } catch (e) {
    return renderMasterGate(req, res, { error: `Request failed: ${e?.message || e}` });
  }
});

app.post("/approvals/:id/decide", async (req, res) => {
  const id = req.params.id;
  const payload = { decision: req.body.decision || "approve", actor: req.body.actor || "admin", reason: req.body.reason || "" };
  const r = await apiFetch(req, `/approvals/${encodeURIComponent(id)}/decide`, { method: "POST", body: JSON.stringify(payload) });
  if (!r.ok) return renderMasterGate(req, res, { error: `API ${r.status}: ${r.raw}` });
  return res.redirect(`/mastergate?sel=${encodeURIComponent(id)}`);
});

app.post("/approvals/:id/archive", async (req, res) => {
  const id = req.params.id;
  const payload = { actor: req.body.actor || "admin", reason: req.body.reason || "" };
  const r = await apiFetch(req, `/approvals/${encodeURIComponent(id)}/archive`, { method: "POST", body: JSON.stringify(payload) });
  if (!r.ok) return renderMasterGate(req, res, { error: `API ${r.status}: ${r.raw}` });
  return res.redirect(`/mastergate?sel=${encodeURIComponent(id)}`);
});

app.post("/approvals/:id/restore", async (req, res) => {
  const id = req.params.id;
  const payload = { actor: req.body.actor || "admin", reason: req.body.reason || "" };
  const r = await apiFetch(req, `/approvals/${encodeURIComponent(id)}/restore`, { method: "POST", body: JSON.stringify(payload) });
  if (!r.ok) return renderMasterGate(req, res, { error: `API ${r.status}: ${r.raw}` });
  return res.redirect(`/mastergate?sel=${encodeURIComponent(id)}`);
});

app.post("/approvals/:id/ask_master", async (req, res) => {
  const id = req.params.id;
  const payload = { provider: req.body.provider || "ollama" };
  const r = await apiFetch(req, `/approvals/${encodeURIComponent(id)}/ask_master`, { method: "POST", body: JSON.stringify(payload) });
  if (!r.ok) return renderMasterGate(req, res, { error: `API ${r.status}: ${r.raw}` });
  return res.redirect(`/mastergate?sel=${encodeURIComponent(id)}`);
});

app.post("/approvals/:id/apply_feedback_and_validate", async (req, res) => {
  const id = req.params.id;
  const payload = {
    actor: req.body.actor || "system",
    max_commands: parseInt(req.body.max_commands || "6", 10) || 6,
    timeout_s: parseInt(req.body.timeout_s || "60", 10) || 60,
    stop_on_fail: !!req.body.stop_on_fail,
  };
  const r = await apiFetch(req, `/approvals/${encodeURIComponent(id)}/apply_feedback_and_validate`, { method: "POST", body: JSON.stringify(payload) });
  if (!r.ok) return renderMasterGate(req, res, { error: `API ${r.status}: ${r.raw}` });
  return res.redirect(`/mastergate?sel=${encodeURIComponent(id)}`);
});

app.post("/approvals/bulk_decide", async (req, res) => {
  try {
    const r = await apiFetch(req, "/approvals/bulk_decide", { method: "POST", body: JSON.stringify(req.body || {}) });
    res.status(r.status).send(typeof r.data === "string" ? r.data : JSON.stringify(r.data));
  } catch (e) {
    res.status(500).send(`bulk_decide failed: ${e?.message || e}`);
  }
});

app.listen(PORT, () => console.log(`web listening on :${PORT}`));