from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: str = Field(min_length=1)
    field: str = Field(min_length=1)
    value: str = Field(min_length=1)
    status: Literal["observed", "verified", "user_provided", "unavailable"] = "observed"
    reference: str | None = None


class DocumentEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int | None = None
    document_type: str = Field(min_length=2)
    file_name: str = ""
    extracted_fields: dict[str, str] = Field(default_factory=dict)
    extraction_method: Literal["metadata", "text", "ocr", "manual", "unavailable"] = "metadata"
    text_excerpt: str | None = None


class SupplierCreate(BaseModel):
    supplier_name: str = Field(min_length=2, max_length=200)
    gstin: str | None = Field(default=None, max_length=32)
    website: HttpUrl | None = None
    registered_address: str | None = Field(default=None, max_length=500)
    bank_account_name: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class SupplierOut(SupplierCreate):
    id: int
    status: str
    created_at: str
    updated_at: str
    last_verified_at: str | None = None


class SupplierVerificationRequest(SupplierCreate):
    evidence: list[EvidenceItem] = Field(default_factory=list)
    documents: list[DocumentEvidence] = Field(default_factory=list)


class RiskFlag(BaseModel):
    code: str
    severity: Literal["info", "low", "medium", "high"]
    title: str
    explanation: str
    evidence: list[str] = Field(default_factory=list)
    remediation: str | None = None


class VerificationResponse(BaseModel):
    id: int | None = None
    supplier_name: str
    overall_status: Literal["review", "attention", "verified_with_limits"]
    coverage_percent: int
    identity_match_percent: int
    consistency_percent: int
    confidence_percent: int
    verified_at: str
    flags: list[RiskFlag]
    next_steps: list[str]
    explanation: str


class CopilotRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class CopilotResponse(BaseModel):
    answer: str
    cited_findings: list[str] = Field(default_factory=list)
    mode: Literal["deterministic", "llm"]


class DashboardSummary(BaseModel):
    total_suppliers: int
    verified_suppliers: int
    needs_review: int
    attention: int
    documents: int
    open_findings: int
    verification_coverage: int


class AuditEvent(BaseModel):
    id: int
    supplier_id: int | None
    event_type: str
    message: str
    created_at: str
