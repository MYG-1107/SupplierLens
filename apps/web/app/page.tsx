"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Supplier = {
  id: number;
  supplier_name: string;
  gstin?: string | null;
  website?: string | null;
  registered_address?: string | null;
  bank_account_name?: string | null;
  category?: string | null;
  notes?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  last_verified_at?: string | null;
};

type Flag = {
  code: string;
  severity: "info" | "low" | "medium" | "high";
  title: string;
  explanation: string;
  evidence: string[];
  remediation?: string | null;
};

type Report = {
  id?: number | null;
  supplier_name: string;
  overall_status: string;
  coverage_percent: number;
  identity_match_percent: number;
  consistency_percent: number;
  confidence_percent: number;
  verified_at: string;
  flags: Flag[];
  next_steps: string[];
  explanation: string;
};

type Detail = Supplier & {
  documents: { id: number; document_type: string; file_name: string; extracted_fields: Record<string, string>; extraction_method: string; text_excerpt?: string | null }[];
  latest_report?: Report | null;
  audit_events: { id: number; event_type: string; message: string; created_at: string }[];
};

type Summary = {
  total_suppliers: number;
  verified_suppliers: number;
  needs_review: number;
  attention: number;
  documents: number;
  open_findings: number;
  verification_coverage: number;
};

const emptySummary: Summary = { total_suppliers: 0, verified_suppliers: 0, needs_review: 0, attention: 0, documents: 0, open_findings: 0, verification_coverage: 0 };

function prettyStatus(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (m) => m.toUpperCase());
}

function relativeTime(value: string) {
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.round(diff / 60000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function statusClass(value: string) {
  if (value === "attention") return "danger";
  if (value === "review") return "warning";
  if (value === "verified_with_limits") return "success";
  return "neutral";
}

export default function Home() {
  const [summary, setSummary] = useState<Summary>(emptySummary);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [tab, setTab] = useState<"overview" | "suppliers" | "evidence" | "audit">("overview");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [showCopilot, setShowCopilot] = useState(false);
  const [copilotQuestion, setCopilotQuestion] = useState("Why was this supplier flagged?");
  const [copilotAnswer, setCopilotAnswer] = useState("");
  const [copilotMode, setCopilotMode] = useState("");
  const [newSupplier, setNewSupplier] = useState({ supplier_name: "", gstin: "", website: "", registered_address: "", bank_account_name: "", category: "", notes: "" });
  const fileRef = useRef<HTMLInputElement>(null);

  const filteredSuppliers = useMemo(() => {
    const normalized = query.toLowerCase().trim();
    if (!normalized) return suppliers;
    return suppliers.filter((s) => `${s.supplier_name} ${s.gstin ?? ""} ${s.category ?? ""}`.toLowerCase().includes(normalized));
  }, [suppliers, query]);

  async function api(path: string, init?: RequestInit) {
    const response = await fetch(path, { ...init, headers: { ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }), ...(init?.headers ?? {}) } });
    if (!response.ok) {
      const body = await response.text();
      throw new Error(body || `Request failed (${response.status})`);
    }
    return response.json();
  }

  async function loadAll(selectFirst = false) {
    setLoading(true);
    try {
      const [s, list] = await Promise.all([api("/api/v1/dashboard/summary"), api("/api/v1/suppliers")]);
      setSummary(s);
      setSuppliers(list);
      if (selectFirst && list.length) await openSupplier(list[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load SupplierLens.");
    } finally {
      setLoading(false);
    }
  }

  async function openSupplier(id: number) {
    setBusy(`open-${id}`);
    setError("");
    try {
      const data = await api(`/api/v1/suppliers/${id}`);
      setSelectedId(id);
      setDetail(data);
      setShowCopilot(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to open supplier.");
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => { void loadAll(true); }, []);

  async function createSupplier() {
    if (!newSupplier.supplier_name.trim()) return;
    setBusy("create");
    setError("");
    try {
      const payload = { ...newSupplier, gstin: newSupplier.gstin || null, website: newSupplier.website || null, registered_address: newSupplier.registered_address || null, bank_account_name: newSupplier.bank_account_name || null, category: newSupplier.category || null, notes: newSupplier.notes || null };
      const created = await api("/api/v1/suppliers", { method: "POST", body: JSON.stringify(payload) });
      setShowNew(false);
      setNewSupplier({ supplier_name: "", gstin: "", website: "", registered_address: "", bank_account_name: "", category: "", notes: "" });
      await loadAll();
      await openSupplier(created.id);
      setTab("suppliers");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create supplier.");
    } finally {
      setBusy(null);
    }
  }

  async function verifySelected() {
    if (!selectedId) return;
    setBusy("verify"); setError("");
    try {
      const report = await api(`/api/v1/suppliers/${selectedId}/verify`, { method: "POST" });
      await loadAll();
      await openSupplier(selectedId);
      setDetail((current) => current ? { ...current, latest_report: report } : current);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed.");
    } finally { setBusy(null); }
  }

  async function uploadDocument() {
    if (!selectedId || !fileRef.current?.files?.[0]) return;
    setBusy("upload"); setError("");
    try {
      const form = new FormData(); form.append("file", fileRef.current.files[0]);
      await api(`/api/v1/suppliers/${selectedId}/documents`, { method: "POST", body: form });
      fileRef.current.value = "";
      await openSupplier(selectedId);
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Document upload failed.");
    } finally { setBusy(null); }
  }

  async function askCopilot() {
    if (!selectedId) return;
    setBusy("copilot"); setError("");
    try {
      const response = await api(`/api/v1/suppliers/${selectedId}/copilot`, { method: "POST", body: JSON.stringify({ question: copilotQuestion }) });
      setCopilotAnswer(response.answer); setCopilotMode(response.mode);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Copilot request failed.");
    } finally { setBusy(null); }
  }

  function exportReport() {
    if (!detail?.latest_report) return;
    const blob = new Blob([JSON.stringify({ supplier: detail, report: detail.latest_report }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `supplierlens-report-${detail.id}.json`; a.click(); URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="logo">Supplier<span>Lens</span></div>
        <div className="workspace-name">PROCUREMENT INTELLIGENCE</div>
        <nav className="nav">
          {(["overview", "suppliers", "evidence", "audit"] as const).map((item) => (
            <button key={item} className={tab === item ? "nav-item active" : "nav-item"} onClick={() => setTab(item)}>
              <span className="nav-icon">{item === "overview" ? "⌂" : item === "suppliers" ? "◎" : item === "evidence" ? "◈" : "≡"}</span>{item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="source-note"><span className="dot" /> Evidence-first MVP</div>
          <div className="sidebar-muted">v0.2 · human review stays in control</div>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <div className="eyebrow">SUPPLIER VERIFICATION WORKSPACE</div>
            <h1>{tab === "overview" ? "Procurement overview" : tab === "suppliers" ? "Suppliers" : tab === "evidence" ? "Evidence centre" : "Audit trail"}</h1>
          </div>
          <div className="top-actions">
            <div className="system-status"><span className="dot" /> API connected</div>
            <button className="button primary" onClick={() => setShowNew(true)}>+ New supplier</button>
          </div>
        </header>

        {error && <div className="alert danger-alert">{error}</div>}

        {tab === "overview" && (
          <>
            <section className="hero-banner">
              <div>
                <div className="hero-kicker">BEFORE THE PURCHASE ORDER</div>
                <h2>Know what you can prove about a supplier.</h2>
                <p>Capture supplier evidence, reconcile identity fields, surface inconsistencies, and preserve an auditable verification trail.</p>
              </div>
              <div className="hero-steps">
                <div><span>01</span><b>Capture</b><small>Supplier facts + documents</small></div>
                <div><span>02</span><b>Reconcile</b><small>Cross-field checks</small></div>
                <div><span>03</span><b>Review</b><small>Evidence-backed actions</small></div>
              </div>
            </section>
            <section className="metric-grid">
              <Metric label="Suppliers" value={summary.total_suppliers} detail="Tracked in workspace" />
              <Metric label="Verified with limits" value={summary.verified_suppliers} detail="No medium/high finding" />
              <Metric label="Needs review" value={summary.needs_review} detail="Medium findings" />
              <Metric label="Attention" value={summary.attention} detail="High findings" />
              <Metric label="Documents" value={summary.documents} detail="Evidence files" />
              <Metric label="Open findings" value={summary.open_findings} detail="Latest 100 runs" />
            </section>
            <section className="two-col">
              <div className="card">
                <div className="section-head"><div><div className="eyebrow">SUPPLIER QUEUE</div><h3>Recent suppliers</h3></div><button className="link-button" onClick={() => setTab("suppliers")}>View all →</button></div>
                {loading ? <Loading /> : filteredSuppliers.slice(0, 5).map((supplier) => <SupplierRow key={supplier.id} supplier={supplier} onClick={() => openSupplier(supplier.id)} />)}
              </div>
              <div className="card">
                <div className="section-head"><div><div className="eyebrow">OPERATING MODEL</div><h3>Evidence before AI</h3></div></div>
                <div className="principle"><div className="principle-number">01</div><div><b>Deterministic first</b><p>Structural checks run before any model-generated explanation.</p></div></div>
                <div className="principle"><div className="principle-number">02</div><div><b>Traceable findings</b><p>Every review signal points back to the supplied evidence.</p></div></div>
                <div className="principle"><div className="principle-number">03</div><div><b>Human decision</b><p>SupplierLens assists reviewers; it does not certify suppliers.</p></div></div>
                <div className="coverage-box"><div><span>Average verification coverage</span><b>{summary.verification_coverage}%</b></div><div className="progress"><span style={{ width: `${summary.verification_coverage}%` }} /></div></div>
              </div>
            </section>
          </>
        )}

        {tab === "suppliers" && (
          <section className="card">
            <div className="section-head table-head"><div><div className="eyebrow">SUPPLIER DIRECTORY</div><h3>{suppliers.length} supplier records</h3></div><div className="search"><span>⌕</span><input placeholder="Search name, GSTIN or category" value={query} onChange={(e) => setQuery(e.target.value)} /></div></div>
            <div className="table-wrap"><table><thead><tr><th>Supplier</th><th>Category</th><th>Status</th><th>Last verified</th><th>Action</th></tr></thead><tbody>{filteredSuppliers.map((s) => <tr key={s.id}><td><div className="supplier-cell"><span className="avatar">{s.supplier_name.slice(0, 1)}</span><div><b>{s.supplier_name}</b><small>{s.gstin || "GSTIN not supplied"}</small></div></div></td><td>{s.category || "—"}</td><td><span className={`pill ${statusClass(s.status)}`}>{prettyStatus(s.status)}</span></td><td>{s.last_verified_at ? relativeTime(s.last_verified_at) : "Never"}</td><td><button className="small-button" onClick={() => openSupplier(s.id)}>Open</button></td></tr>)}</tbody></table></div>
          </section>
        )}

        {tab === "evidence" && (
          <section className="two-col evidence-page">
            <div className="card">
              <div className="section-head"><div><div className="eyebrow">EVIDENCE CENTRE</div><h3>{detail ? detail.supplier_name : "Select a supplier"}</h3></div></div>
              {!detail ? <p className="muted">Open a supplier to inspect uploaded evidence and extracted fields.</p> : <>
                <div className="upload-zone" onClick={() => fileRef.current?.click()}><div className="upload-icon">↑</div><b>Upload supplier evidence</b><span>PDF, TXT, CSV, JSON, PNG, JPG, WEBP · max 10 MB</span><input ref={fileRef} type="file" hidden onChange={() => void uploadDocument()} /></div>
                <div className="doc-list">{detail.documents.length === 0 ? <div className="empty">No documents uploaded yet.</div> : detail.documents.map((doc) => <div className="doc-card" key={doc.id}><div className="doc-icon">DOC</div><div><div className="doc-head"><b>{doc.file_name}</b><a className="download" href={`/api/v1/documents/${doc.id}/download`}>Download</a></div><small>{doc.document_type} · {doc.extraction_method}</small>{Object.entries(doc.extracted_fields).map(([key, value]) => <div className="field-line" key={key}><span>{key}</span><b>{value}</b></div>)}</div></div>)}</div>
              </>}
            </div>
            <div className="card report-side">{detail?.latest_report ? <ReportPanel report={detail.latest_report} exportReport={exportReport} /> : <div className="empty-state"><div className="empty-icon">◈</div><h3>Evidence-backed report</h3><p>Run verification for the selected supplier to generate findings, actions and the explainable report.</p></div>}</div>
          </section>
        )}

        {tab === "audit" && (
          <section className="card">
            <div className="section-head"><div><div className="eyebrow">AUDIT TRAIL</div><h3>Recent activity</h3></div></div>
            {!detail ? <p className="muted">Select a supplier from the Suppliers tab to inspect its audit trail.</p> : detail.audit_events.map((event) => <div className="audit-row" key={event.id}><div className="audit-time">{relativeTime(event.created_at)}</div><div><b>{event.event_type}</b><p>{event.message}</p></div></div>)}
          </section>
        )}

        {selectedId && detail && tab !== "evidence" && tab !== "audit" && (
          <section className="detail-grid">
            <div className="card detail-card">
              <div className="section-head"><div><div className="eyebrow">SELECTED SUPPLIER</div><h3>{detail.supplier_name}</h3></div><span className={`pill ${statusClass(detail.status)}`}>{prettyStatus(detail.status)}</span></div>
              <div className="details"><DetailItem label="GSTIN" value={detail.gstin || "Not supplied"} /><DetailItem label="Category" value={detail.category || "Not classified"} /><DetailItem label="Website" value={detail.website || "Not supplied"} /><DetailItem label="Bank account name" value={detail.bank_account_name || "Not supplied"} /><DetailItem label="Registered address" value={detail.registered_address || "Not supplied"} /></div>
              <div className="button-row"><button className="button primary" onClick={verifySelected}>{busy === "verify" ? "Verifying…" : "Run verification"}</button><button className="button ghost" onClick={() => { setTab("evidence"); fileRef.current?.click(); }}>Upload evidence</button><button className="button ghost" onClick={() => setShowCopilot(true)}>Ask Copilot</button></div>
            </div>
            <div className="card report-card">{detail.latest_report ? <ReportPanel report={detail.latest_report} exportReport={exportReport} /> : <div className="empty-state"><div className="empty-icon">◎</div><h3>No verification run yet</h3><p>Run the deterministic verification engine against the supplier's current evidence.</p></div>}</div>
          </section>
        )}
      </section>

      {showNew && <Modal title="Add a supplier" onClose={() => setShowNew(false)}><div className="form-grid"><Field label="Supplier name" value={newSupplier.supplier_name} onChange={(v) => setNewSupplier({ ...newSupplier, supplier_name: v })} required /><Field label="GSTIN" value={newSupplier.gstin} onChange={(v) => setNewSupplier({ ...newSupplier, gstin: v })} /><Field label="Website" value={newSupplier.website} onChange={(v) => setNewSupplier({ ...newSupplier, website: v })} /><Field label="Category" value={newSupplier.category} onChange={(v) => setNewSupplier({ ...newSupplier, category: v })} /><Field label="Bank account name" value={newSupplier.bank_account_name} onChange={(v) => setNewSupplier({ ...newSupplier, bank_account_name: v })} /><Field label="Registered address" value={newSupplier.registered_address} onChange={(v) => setNewSupplier({ ...newSupplier, registered_address: v })} wide /><Field label="Notes" value={newSupplier.notes} onChange={(v) => setNewSupplier({ ...newSupplier, notes: v })} wide textarea /></div><div className="modal-actions"><button className="button ghost" onClick={() => setShowNew(false)}>Cancel</button><button className="button primary" onClick={createSupplier}>{busy === "create" ? "Creating…" : "Create supplier"}</button></div></Modal>}
      {showCopilot && detail?.latest_report && <Modal title="SupplierLens Copilot" onClose={() => setShowCopilot(false)}><div className="copilot-intro">Copilot answers from the latest verification report. It does not add new facts.</div><textarea className="copilot-input" value={copilotQuestion} onChange={(e) => setCopilotQuestion(e.target.value)} /><button className="button primary" onClick={askCopilot}>{busy === "copilot" ? "Thinking…" : "Ask"}</button>{copilotAnswer && <div className="copilot-answer"><div className="answer-label">{copilotMode === "llm" ? "LLM-assisted answer" : "Deterministic answer"}</div><p>{copilotAnswer}</p></div>}</Modal>}
    </main>
  );
}

function Metric({ label, value, detail }: { label: string; value: number; detail: string }) { return <div className="metric"><span>{label}</span><b>{value}</b><small>{detail}</small></div>; }
function Loading() { return <div className="loading">Loading workspace…</div>; }
function SupplierRow({ supplier, onClick }: { supplier: Supplier; onClick: () => void }) { return <button className="supplier-row" onClick={onClick}><span className="avatar">{supplier.supplier_name.slice(0, 1)}</span><span className="supplier-main"><b>{supplier.supplier_name}</b><small>{supplier.category || "Unclassified"} · {supplier.gstin || "No GSTIN"}</small></span><span className={`pill ${statusClass(supplier.status)}`}>{prettyStatus(supplier.status)}</span><span className="chevron">→</span></button>; }
function DetailItem({ label, value }: { label: string; value: string }) { return <div className="detail-item"><span>{label}</span><b>{value}</b></div>; }
function Field({ label, value, onChange, required, wide, textarea }: { label: string; value: string; onChange: (v: string) => void; required?: boolean; wide?: boolean; textarea?: boolean }) { return <label className={`form-field ${wide ? "wide" : ""}`}><span>{label}{required ? " *" : ""}</span>{textarea ? <textarea value={value} onChange={(e) => onChange(e.target.value)} /> : <input value={value} onChange={(e) => onChange(e.target.value)} />}</label>; }
function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) { return <div className="modal-backdrop"><div className="modal"><div className="modal-head"><h3>{title}</h3><button className="close" onClick={onClose}>×</button></div>{children}</div></div>; }
function ReportPanel({ report, exportReport }: { report: Report; exportReport: () => void }) { return <><div className="section-head"><div><div className="eyebrow">VERIFICATION REPORT</div><h3>{report.supplier_name}</h3></div><span className={`pill ${statusClass(report.overall_status)}`}>{prettyStatus(report.overall_status)}</span></div><div className="score-grid"><Score label="Evidence coverage" value={report.coverage_percent} /><Score label="Identity match" value={report.identity_match_percent} /><Score label="Consistency" value={report.consistency_percent} /><Score label="Model confidence" value={report.confidence_percent} /></div><div className="report-explanation">{report.explanation}</div><h4>Review signals <span>{report.flags.filter((f) => f.severity === "high" || f.severity === "medium").length}</span></h4><div className="flag-list">{report.flags.filter((f) => f.severity !== "info").map((f) => <div className={`flag-card ${f.severity}`} key={f.code}><div className="flag-top"><b>{f.title}</b><span>{f.severity}</span></div><p>{f.explanation}</p>{f.evidence.map((line) => <div className="evidence-line" key={line}>↳ {line}</div>)}{f.remediation && <div className="remediation"><b>Suggested review:</b> {f.remediation}</div>}</div>)}</div><h4>Next steps</h4><ol className="next-steps">{report.next_steps.map((step) => <li key={step}>{step}</li>)}</ol><button className="button ghost full" onClick={exportReport}>Export report JSON</button></>; }
function Score({ label, value }: { label: string; value: number }) { return <div className="score"><div><span>{label}</span><b>{value}%</b></div><div className="progress"><span style={{ width: `${value}%` }} /></div></div>; }
