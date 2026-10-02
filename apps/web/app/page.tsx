"use client";

import { useState } from "react";

type Flag = {
  code: string;
  severity: "info" | "low" | "medium" | "high";
  title: string;
  explanation: string;
  evidence: string[];
};

type Result = {
  supplier_name: string;
  overall_status: string;
  coverage_percent: number;
  identity_match_percent: number;
  consistency_percent: number;
  flags: Flag[];
  next_steps: string[];
  explanation: string;
};

const api = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [supplierName, setSupplierName] = useState("ABC Components Private Limited");
  const [gstin, setGstin] = useState("36ABCDE1234F1Z5");
  const [website, setWebsite] = useState("https://example.com");
  const [address, setAddress] = useState("Plot 12, Industrial Area, Hyderabad, Telangana");
  const [bankName, setBankName] = useState("ABC Components Pvt Ltd");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);

  async function verify() {
    setLoading(true);
    setResult(null);
    try {
      const response = await fetch(`${api}/api/v1/verification/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_name: supplierName,
          gstin,
          website,
          registered_address: address,
          bank_account_name: bankName,
          evidence: [
            { source: "GST", field: "gstin", value: gstin },
            { source: "Supplier Website", field: "website", value: website },
          ],
          documents: [
            { document_type: "gst_certificate", extracted_fields: { legal_name: supplierName, address } },
            { document_type: "bank_proof", extracted_fields: { account_name: bankName } },
          ],
        }),
      });
      if (!response.ok) throw new Error("Verification request failed");
      setResult(await response.json());
    } catch (error) {
      setResult({
        supplier_name: supplierName,
        overall_status: "attention",
        coverage_percent: 0,
        identity_match_percent: 0,
        consistency_percent: 0,
        flags: [{ code: "API_UNAVAILABLE", severity: "high", title: "API unavailable", explanation: error instanceof Error ? error.message : "Unable to reach SupplierLens API.", evidence: [] }],
        next_steps: ["Start the FastAPI service on port 8000 and try again."],
        explanation: "The web application could not reach the verification API.",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <div className="container">
        <header className="header">
          <div className="brand">Supplier<span>Lens</span></div>
          <div className="badge">Evidence-first verification · MVP</div>
        </header>

        <section className="hero">
          <div>
            <h1>See the evidence before you commit.</h1>
            <p>
              SupplierLens helps procurement teams reconcile supplier identities, find inconsistencies across evidence, and turn verification work into an explainable review workflow.
            </p>
            <div className="stats">
              <div className="stat"><b>Identity</b><small>Cross-field matching</small></div>
              <div className="stat"><b>Evidence</b><small>Source-linked findings</small></div>
              <div className="stat"><b>AI-ready</b><small>OCR · ML · RAG · LLM</small></div>
            </div>
          </div>
          <div className="panel">
            <strong>Product principle</strong>
            <p className="muted">A model should explain evidence, not replace it.</p>
            <p className="muted">The current MVP uses deterministic checks and is designed so OCR, ML models, permitted data connectors, and an LLM can be added behind clear interfaces.</p>
          </div>
        </section>

        <section className="workspace">
          <div className="panel">
            <h2>Supplier intake</h2>
            <p className="muted">Start with synthetic data. Later connect permitted official/public sources and document extraction.</p>
            <div className="field"><label>Supplier name</label><input value={supplierName} onChange={e => setSupplierName(e.target.value)} /></div>
            <div className="field"><label>GSTIN</label><input value={gstin} onChange={e => setGstin(e.target.value)} /></div>
            <div className="field"><label>Website</label><input value={website} onChange={e => setWebsite(e.target.value)} /></div>
            <div className="field"><label>Registered address</label><textarea value={address} onChange={e => setAddress(e.target.value)} /></div>
            <div className="field"><label>Bank account name</label><input value={bankName} onChange={e => setBankName(e.target.value)} /></div>
            <button className="button" onClick={verify} disabled={loading}>{loading ? "Verifying…" : "Run verification"}</button>
          </div>

          <div className="panel">
            {!result ? (
              <>
                <h2>Verification report</h2>
                <p className="muted">Run a check to see identity, consistency, evidence coverage, review signals, and next steps.</p>
              </>
            ) : (
              <>
                <div className="resultHeader">
                  <div><div className="muted">Supplier</div><h2>{result.supplier_name}</h2></div>
                  <div className={`status ${result.overall_status === "attention" ? "attention" : result.overall_status === "review" ? "review" : "ok"}`}>{result.overall_status.replaceAll("_", " ")}</div>
                </div>
                <div className="meters">
                  <div className="meter"><span>Evidence coverage</span><strong>{result.coverage_percent}%</strong></div>
                  <div className="meter"><span>Identity match</span><strong>{result.identity_match_percent}%</strong></div>
                  <div className="meter"><span>Consistency</span><strong>{result.consistency_percent}%</strong></div>
                </div>
                <p>{result.explanation}</p>
                <h3>Review signals</h3>
                {result.flags.length === 0 ? <p className="muted">No signals were generated from the supplied MVP evidence.</p> : result.flags.map(flag => (
                  <div key={flag.code} className={`flag ${flag.severity === "high" ? "high" : ""}`}>
                    <div className="flagTitle">{flag.title} · {flag.severity}</div>
                    <div className="muted">{flag.explanation}</div>
                    {flag.evidence.length > 0 && <div className="muted" style={{marginTop: 8}}>Evidence: {flag.evidence.join(" · ")}</div>}
                  </div>
                ))}
                <h3>Next steps</h3>
                <ol className="list">{result.next_steps.map(step => <li key={step}>{step}</li>)}</ol>
              </>
            )}
          </div>
        </section>

        <footer className="footer">SupplierLens v0.1 · Decision support prototype · Keep source evidence and model output distinguishable.</footer>
      </div>
    </main>
  );
}
