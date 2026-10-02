from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class EvidenceItem(BaseModel):
    source: str = Field(min_length=1)
    field: str = Field(min_length=1)
    value: str = Field(min_length=1)


class DocumentEvidence(BaseModel):
    document_type: str
    extracted_fields: dict[str, str] = {}


class SupplierVerificationRequest(BaseModel):
    supplier_name: str = Field(min_length=2)
    gstin: str | None = None
    website: HttpUrl | None = None
    registered_address: str | None = None
    bank_account_name: str | None = None
    evidence: list[EvidenceItem] = []
    documents: list[DocumentEvidence] = []


class RiskFlag(BaseModel):
    code: str
    severity: Literal["info", "low", "medium", "high"]
    title: str
    explanation: str
    evidence: list[str] = []


class VerificationResponse(BaseModel):
    supplier_name: str
    overall_status: Literal["review", "attention", "verified_with_limits"]
    coverage_percent: int
    identity_match_percent: int
    consistency_percent: int
    flags: list[RiskFlag]
    next_steps: list[str]
    explanation: str
