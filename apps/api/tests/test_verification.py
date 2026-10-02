from app.schemas.verification import DocumentEvidence, SupplierVerificationRequest
from app.services.verification_engine import verify_supplier


def test_consistent_supplier_is_not_attention():
    payload = SupplierVerificationRequest(
        supplier_name="ABC Components Private Limited",
        gstin="36ABCDE1234F1Z5",
        website="https://example.com",
        registered_address="Plot 12, Industrial Area, Hyderabad, Telangana",
        bank_account_name="ABC Components Private Limited",
        evidence=[{"source": "GST", "field": "gstin", "value": "36ABCDE1234F1Z5"}],
        documents=[DocumentEvidence(document_type="gst_certificate", file_name="gst.txt", extracted_fields={
            "legal_name": "ABC Components Private Limited",
            "address": "Plot 12, Industrial Area, Hyderabad, Telangana",
        })],
    )
    result = verify_supplier(payload)
    assert result.overall_status == "verified_with_limits"
    assert result.coverage_percent > 30


def test_mismatch_is_flagged():
    payload = SupplierVerificationRequest(
        supplier_name="Northstar Tools & Fasteners",
        gstin="36ABC1234DE5FZ7",
        bank_account_name="Northstar Holdings",
        documents=[DocumentEvidence(document_type="bank_proof", file_name="bank.txt", extracted_fields={"account_name": "Northstar Holdings"})],
    )
    result = verify_supplier(payload)
    assert any(f.code == "BANK_NAME_MISMATCH" for f in result.flags)


def test_missing_gstin_is_high_severity():
    payload = SupplierVerificationRequest(supplier_name="BluePeak Electricals")
    result = verify_supplier(payload)
    assert any(f.code == "GSTIN_MISSING" and f.severity == "high" for f in result.flags)
