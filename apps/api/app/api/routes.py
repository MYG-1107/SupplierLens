from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db import add_audit, get_conn, row_to_dict, utc_now
from app.schemas.verification import (
    AuditEvent, CopilotRequest, CopilotResponse, DashboardSummary, DocumentEvidence,
    SupplierCreate, SupplierOut, SupplierVerificationRequest, VerificationResponse,
)
from app.services.document_service import extract_basic_fields, infer_document_type, save_upload
from app.services.llm_service import generate_copilot
from app.services.verification_engine import verify_supplier

router = APIRouter(prefix="/api/v1")


def _supplier_out(row) -> SupplierOut:
    return SupplierOut(**(row_to_dict(row) or {}))


def _load_supplier(supplier_id: int):
    with get_conn() as conn:
        supplier = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
        if not supplier:
            raise HTTPException(404, "Supplier not found")
        docs = conn.execute("SELECT * FROM documents WHERE supplier_id = ? ORDER BY created_at DESC", (supplier_id,)).fetchall()
    return supplier, docs


def _load_latest_report(supplier_id: int) -> VerificationResponse:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, report_json FROM verification_runs WHERE supplier_id = ? ORDER BY id DESC LIMIT 1",
            (supplier_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "No verification report exists for this supplier")
    payload = json.loads(row["report_json"])
    payload["id"] = row["id"]
    return VerificationResponse(**payload)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM suppliers").fetchone()["c"]
        verified = conn.execute("SELECT COUNT(*) c FROM suppliers WHERE status = 'verified_with_limits'").fetchone()["c"]
        review = conn.execute("SELECT COUNT(*) c FROM suppliers WHERE status = 'review'").fetchone()["c"]
        attention = conn.execute("SELECT COUNT(*) c FROM suppliers WHERE status = 'attention'").fetchone()["c"]
        docs = conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
        runs = conn.execute("SELECT report_json FROM verification_runs ORDER BY id DESC LIMIT 100").fetchall()
    open_findings = 0
    coverage_values = []
    for r in runs:
        report = json.loads(r["report_json"])
        open_findings += sum(1 for f in report.get("flags", []) if f.get("severity") in {"high", "medium"})
        coverage_values.append(report.get("coverage_percent", 0))
    coverage = int(sum(coverage_values) / len(coverage_values)) if coverage_values else 0
    return DashboardSummary(
        total_suppliers=total, verified_suppliers=verified, needs_review=review, attention=attention,
        documents=docs, open_findings=open_findings, verification_coverage=coverage,
    )


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM suppliers ORDER BY updated_at DESC").fetchall()
    return [_supplier_out(r) for r in rows]


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierCreate):
    now = utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO suppliers
            (supplier_name, gstin, website, registered_address, bank_account_name, category, notes, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'not_verified', ?, ?)""",
            (payload.supplier_name, payload.gstin, str(payload.website) if payload.website else None,
             payload.registered_address, payload.bank_account_name, payload.category, payload.notes, now, now),
        )
        sid = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM suppliers WHERE id = ?", (sid,)).fetchone()
    add_audit(sid, "supplier.created", f"Supplier '{payload.supplier_name}' created")
    return _supplier_out(row)


@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: int):
    supplier, docs = _load_supplier(supplier_id)
    data = dict(supplier)
    data["documents"] = [{**dict(d), "extracted_fields": json.loads(d["extracted_fields"])} for d in docs]
    with get_conn() as conn:
        report = conn.execute(
            "SELECT id, report_json, created_at FROM verification_runs WHERE supplier_id = ? ORDER BY id DESC LIMIT 1", (supplier_id,)
        ).fetchone()
        events = conn.execute(
            "SELECT id, supplier_id, event_type, message, created_at FROM audit_events WHERE supplier_id = ? ORDER BY id DESC LIMIT 30", (supplier_id,)
        ).fetchall()
    data["latest_report"] = {"id": report["id"], **json.loads(report["report_json"]), "created_at": report["created_at"]} if report else None
    data["audit_events"] = [dict(e) for e in events]
    return data


@router.get("/documents/{document_id}/download")
def download_document(document_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT file_name, stored_path FROM documents WHERE id = ?", (document_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Document not found")
    path = Path(row["stored_path"])
    if not path.exists():
        raise HTTPException(404, "Stored document file is missing")
    return FileResponse(path, filename=row["file_name"])


@router.post("/suppliers/{supplier_id}/documents", response_model=DocumentEvidence, status_code=201)
def upload_document(supplier_id: int, file: UploadFile = File(...)):
    _load_supplier(supplier_id)
    try:
        path, size = save_upload(supplier_id, file.filename or "document", file.content_type, file.file)
        document_type = infer_document_type(file.filename or "document")
        fields, method, excerpt = extract_basic_fields(path, document_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    now = utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO documents
            (supplier_id, document_type, file_name, stored_path, content_type, size_bytes, extracted_fields, extraction_method, text_excerpt, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (supplier_id, document_type, file.filename or path.name, str(path), file.content_type, size, json.dumps(fields), method, excerpt, now),
        )
        doc_id = int(cur.lastrowid)
    add_audit(supplier_id, "document.uploaded", f"Uploaded {file.filename or path.name} ({document_type})")
    return DocumentEvidence(id=doc_id, document_type=document_type, file_name=file.filename or path.name,
                            extracted_fields=fields, extraction_method=method, text_excerpt=excerpt)


@router.post("/suppliers/{supplier_id}/verify", response_model=VerificationResponse)
def verify_existing_supplier(supplier_id: int):
    supplier, docs = _load_supplier(supplier_id)
    evidence = [{"source": "Supplier intake", "field": "supplier_name", "value": supplier["supplier_name"], "status": "user_provided"}]
    if supplier["gstin"]:
        evidence.append({"source": "Supplier intake", "field": "gstin", "value": supplier["gstin"], "status": "user_provided"})
    if supplier["website"]:
        evidence.append({"source": "Supplier intake", "field": "website", "value": supplier["website"], "status": "user_provided"})
    documents = [DocumentEvidence(id=d["id"], document_type=d["document_type"], file_name=d["file_name"],
                                  extracted_fields=json.loads(d["extracted_fields"]), extraction_method=d["extraction_method"],
                                  text_excerpt=d["text_excerpt"]) for d in docs]
    request = SupplierVerificationRequest(supplier_name=supplier["supplier_name"], gstin=supplier["gstin"], website=supplier["website"],
                                           registered_address=supplier["registered_address"], bank_account_name=supplier["bank_account_name"],
                                           category=supplier["category"], notes=supplier["notes"], evidence=evidence, documents=documents)
    report = verify_supplier(request)
    now = report.verified_at
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO verification_runs (supplier_id, report_json, created_at) VALUES (?, ?, ?)",
                           (supplier_id, report.model_dump_json(), now))
        run_id = int(cur.lastrowid)
        conn.execute("UPDATE suppliers SET status = ?, last_verified_at = ?, updated_at = ? WHERE id = ?",
                     (report.overall_status, now, now, supplier_id))
    add_audit(supplier_id, "verification.completed", f"Verification completed with status '{report.overall_status}'")
    report.id = run_id
    return report


@router.get("/suppliers/{supplier_id}/report", response_model=VerificationResponse)
def supplier_report(supplier_id: int):
    return _load_latest_report(supplier_id)


@router.post("/suppliers/{supplier_id}/copilot", response_model=CopilotResponse)
def supplier_copilot(supplier_id: int, payload: CopilotRequest):
    report = _load_latest_report(supplier_id)
    result = generate_copilot(payload.question, report)
    add_audit(supplier_id, "copilot.query", f"Copilot question answered in {result.mode} mode")
    return result


@router.get("/audit", response_model=list[AuditEvent])
def audit_events(limit: int = 50):
    limit = max(1, min(limit, 200))
    with get_conn() as conn:
        rows = conn.execute("SELECT id, supplier_id, event_type, message, created_at FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [AuditEvent(**dict(r)) for r in rows]
