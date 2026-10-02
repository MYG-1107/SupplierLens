import re
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


def verify_supplier(request: SupplierVerificationRequest) -> VerificationResponse:
    flags: list[RiskFlag] = []
    identity = 100
    consistency = 100
    evidence_count = len(request.evidence) + len(request.documents)

    if request.gstin:
        if not GSTIN_RE.match(request.gstin.strip()):
            identity -= 35
            flags.append(RiskFlag(
                code="GSTIN_FORMAT",
                severity="high",
                title="GSTIN format requires review",
                explanation="The supplied GSTIN does not match the expected 15-character GSTIN pattern.",
                evidence=["User-entered GSTIN"],
            ))
    else:
        identity -= 15
        flags.append(RiskFlag(
            code="GSTIN_MISSING",
            severity="medium",
            title="GSTIN was not supplied",
            explanation="A tax-registration identifier was not included in the intake data, so identity coverage is limited.",
            evidence=["Supplier intake form"],
        ))

    # Compare document names against the supplied supplier name.
    document_names: list[str] = []
    for document in request.documents:
        for key, value in document.extracted_fields.items():
            if key.lower() in {"name", "legal_name", "company_name", "trade_name"}:
                document_names.append(value)

    mismatches: list[tuple[str, int]] = []
    for name in document_names:
        score = _similar(request.supplier_name, name)
        if score < 75:
            mismatches.append((name, score))

    if mismatches:
        consistency -= min(40, 15 * len(mismatches))
        flags.append(RiskFlag(
            code="NAME_MISMATCH",
            severity="high" if len(mismatches) > 1 else "medium",
            title="Supplier identity differs across documents",
            explanation="At least one document contains a company name that is materially different from the supplied supplier name.",
            evidence=[f"Document name: {name} (match {score}%)" for name, score in mismatches],
        ))

    address_values = [
        value for d in request.documents
        for key, value in d.extracted_fields.items()
        if key.lower() in {"address", "registered_address", "principal_place_of_business"}
    ]
    if request.registered_address and address_values:
        address_scores = [_similar(request.registered_address, value) for value in address_values]
        if max(address_scores) < 65:
            consistency -= 20
            flags.append(RiskFlag(
                code="ADDRESS_MISMATCH",
                severity="medium",
                title="Address consistency requires review",
                explanation="The registered address supplied during intake is not closely similar to the address found in the submitted evidence.",
                evidence=[f"Document address match: {score}%" for score in address_scores],
            ))

    if request.bank_account_name and request.supplier_name:
        bank_score = _similar(request.bank_account_name, request.supplier_name)
        if bank_score < 70:
            consistency -= 20
            flags.append(RiskFlag(
                code="BANK_NAME_MISMATCH",
                severity="medium",
                title="Bank account name differs from supplier identity",
                explanation="The supplied bank-account name is not closely similar to the supplier name. This can have legitimate explanations, but it should be reviewed before payment.",
                evidence=[f"Bank-account name similarity: {bank_score}%"],
            ))

    if not request.website:
        flags.append(RiskFlag(
            code="WEBSITE_MISSING",
            severity="low",
            title="Website evidence not supplied",
            explanation="No business website was provided, reducing the amount of independently observable business evidence.",
            evidence=["Supplier intake form"],
        ))

    coverage = min(100, 35 + evidence_count * 12)
    identity = max(0, identity)
    consistency = max(0, consistency)

    high_count = sum(1 for f in flags if f.severity == "high")
    medium_count = sum(1 for f in flags if f.severity == "medium")

    if high_count:
        status = "attention"
    elif medium_count:
        status = "review"
    else:
        status = "verified_with_limits"

    next_steps = [
        "Review every medium/high finding against the original evidence.",
        "Confirm bank-account ownership before sending an advance payment.",
        "Add permitted external verification sources to increase coverage.",
    ]
    if not request.documents:
        next_steps.insert(0, "Upload at least one primary supplier document to enable cross-document checks.")

    explanation = (
        f"SupplierLens found {len(flags)} review signal(s). "
        f"Identity consistency is {identity}% and document consistency is {consistency}%. "
        f"Verification coverage is estimated at {coverage}% based only on the evidence supplied to this MVP."
    )

    return VerificationResponse(
        supplier_name=request.supplier_name,
        overall_status=status,
        coverage_percent=coverage,
        identity_match_percent=identity,
        consistency_percent=consistency,
        flags=flags,
        next_steps=next_steps,
        explanation=explanation,
    )
