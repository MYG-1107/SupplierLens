from __future__ import annotations

import re
from datetime import datetime, timezone
from rapidfuzz.fuzz import ratio

from app.schemas.verification import RiskFlag, SupplierVerificationRequest, VerificationResponse

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z0-9]{10}[0-9A-Z][A-Z0-9][0-9A-Z]$", re.I)


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _similar(a: str | None, b: str | None) -> int:
    if not a or not b:
        return 0
    return int(ratio(_norm(a), _norm(b)))


def _status(high: int, medium: int) -> str:
    if high:
        return "attention"
    if medium:
        return "review"
    return "verified_with_limits"


def verify_supplier(request: SupplierVerificationRequest, verification_id: int | None = None) -> VerificationResponse:
    flags: list[RiskFlag] = []
    identity = 100
    consistency = 100

    evidence_count = len(request.evidence)
    document_count = len(request.documents)
    coverage = 30 + evidence_count * 8 + document_count * 14

    gstin = (request.gstin or "").strip()
    if gstin:
        if not GSTIN_RE.match(gstin):
            identity -= 35
            flags.append(RiskFlag(
                code="GSTIN_FORMAT",
                severity="high",
                title="GSTIN format requires review",
                explanation="The supplied GSTIN does not match the expected 15-character pattern. This is a format check, not a government-status confirmation.",
                evidence=[f"Entered GSTIN: {gstin}"],
                remediation="Check the GSTIN against an authoritative GST source before onboarding.",
            ))
        else:
            flags.append(RiskFlag(
                code="GSTIN_FORMAT_OK",
                severity="info",
                title="GSTIN format is plausible",
                explanation="The entered GSTIN passes the structural format check.",
                evidence=["Supplier intake"],
            ))
    else:
        identity -= 20
        flags.append(RiskFlag(
            code="GSTIN_MISSING",
            severity="high",
            title="GSTIN evidence is missing",
            explanation="No GSTIN was provided, so tax-registration identity cannot be assessed in this MVP.",
            evidence=["Supplier intake"],
            remediation="Collect a GSTIN and verify it through an authorized/official source.",
        ))

    document_names: list[tuple[str, str]] = []
    for document in request.documents:
        for key, value in document.extracted_fields.items():
            if key.lower() in {"name", "legal_name", "company_name", "trade_name", "account_name"} and value:
                document_names.append((document.file_name or document.document_type, value))

    mismatches: list[tuple[str, int, str]] = []
    for source, name in document_names:
        score = _similar(request.supplier_name, name)
        if score < 75:
            mismatches.append((source, score, name))

    if mismatches:
        consistency -= min(45, 18 * len(mismatches))
        flags.append(RiskFlag(
            code="NAME_MISMATCH",
            severity="high" if len(mismatches) > 1 else "medium",
            title="Supplier identity differs across evidence",
            explanation="One or more extracted names are materially different from the supplier name entered during intake.",
            evidence=[f"{source}: {name} (match {score}%)" for source, score, name in mismatches],
            remediation="Ask the supplier to reconcile legal/trade/account names and retain the supporting document.",
        ))

    address_values = [
        (d.file_name or d.document_type, value)
        for d in request.documents
        for key, value in d.extracted_fields.items()
        if key.lower() in {"address", "registered_address", "principal_place_of_business"} and value
    ]
    if request.registered_address and address_values:
        scores = [(src, _similar(request.registered_address, value), value) for src, value in address_values]
        best = max(scores, key=lambda x: x[1])
        if best[1] < 65:
            consistency -= 18
            flags.append(RiskFlag(
                code="ADDRESS_MISMATCH",
                severity="medium",
                title="Address consistency requires review",
                explanation="The registered address does not closely match the best available document address.",
                evidence=[f"Best document match: {best[1]}%", f"Document: {best[2]}"],
                remediation="Confirm whether the difference is a branch, warehouse, trading address, or stale registration address.",
            ))

    if request.bank_account_name and request.supplier_name:
        bank_score = _similar(request.bank_account_name, request.supplier_name)
        if bank_score < 70:
            consistency -= 22
            flags.append(RiskFlag(
                code="BANK_NAME_MISMATCH",
                severity="medium",
                title="Bank account name differs from supplier identity",
                explanation="The supplied bank-account name is not closely similar to the supplier name. There may be legitimate explanations, but payment ownership should be reviewed.",
                evidence=[f"Bank-account name similarity: {bank_score}%"],
                remediation="Request bank proof and confirm account ownership with your procurement/payment controls.",
            ))

    if not request.website:
        flags.append(RiskFlag(
            code="WEBSITE_MISSING",
            severity="low",
            title="Website evidence is missing",
            explanation="No business website was supplied, reducing independently observable evidence in this MVP.",
            evidence=["Supplier intake"],
            remediation="Collect a company website or another independently observable business presence.",
        ))
    else:
        flags.append(RiskFlag(
            code="WEBSITE_PROVIDED",
            severity="info",
            title="Website supplied",
            explanation="A website was supplied and can be reviewed as an additional evidence source.",
            evidence=[str(request.website)],
        ))

    if not request.documents:
        flags.append(RiskFlag(
            code="NO_DOCUMENTS",
            severity="high",
            title="No supplier documents uploaded",
            explanation="The current verification run cannot perform document-level cross-checks without uploaded evidence.",
            evidence=["Document workspace"],
            remediation="Upload primary identity, registration, banking, or quotation evidence.",
        ))

    coverage = max(0, min(100, coverage))
    identity = max(0, min(100, identity))
    consistency = max(0, min(100, consistency))

    high_count = sum(1 for f in flags if f.severity == "high")
    medium_count = sum(1 for f in flags if f.severity == "medium")
    overall = _status(high_count, medium_count)
    confidence = max(20, min(95, int((identity * 0.45) + (consistency * 0.35) + (coverage * 0.20))))

    next_steps: list[str] = []
    if any(f.code == "GSTIN_MISSING" for f in flags):
        next_steps.append("Collect and verify the supplier GSTIN through an authorized source.")
    if any(f.code in {"NAME_MISMATCH", "BANK_NAME_MISMATCH"} for f in flags):
        next_steps.append("Resolve name differences before authorizing an advance payment or onboarding the supplier.")
    if any(f.code == "ADDRESS_MISMATCH" for f in flags):
        next_steps.append("Confirm which address is legally registered and which is operational.")
    if not request.documents:
        next_steps.append("Upload at least one primary supplier document to increase evidence coverage.")
    next_steps.append("Keep original source evidence attached to the verification record for auditability.")

    now = datetime.now(timezone.utc).isoformat()
    explanation = (
        f"SupplierLens found {len(flags)} signal(s) from the evidence supplied to this run. "
        f"Identity consistency is {identity}%, evidence consistency is {consistency}%, "
        f"and coverage is {coverage}%. These indicators support human review; they do not certify a supplier."
    )

    return VerificationResponse(
        id=verification_id,
        supplier_name=request.supplier_name,
        overall_status=overall,
        coverage_percent=coverage,
        identity_match_percent=identity,
        consistency_percent=consistency,
        confidence_percent=confidence,
        verified_at=now,
        flags=flags,
        next_steps=next_steps,
        explanation=explanation,
    )
