from fastapi import APIRouter
from app.schemas.verification import SupplierVerificationRequest, VerificationResponse
from app.services.verification_engine import verify_supplier
from app.services.llm_service import generate_explanation

router = APIRouter(prefix="/api/v1")


@router.get("/suppliers/sample")
def sample_supplier() -> SupplierVerificationRequest:
    return SupplierVerificationRequest(
        supplier_name="ABC Components Private Limited",
        gstin="36ABCDE1234F1Z5",
        website="https://example.com",
        registered_address="Plot 12, Industrial Area, Hyderabad, Telangana",
        bank_account_name="ABC Components Pvt Ltd",
        evidence=[
            {"source": "GST", "field": "gstin", "value": "36ABCDE1234F1Z5"},
            {"source": "Supplier Website", "field": "website", "value": "https://example.com"},
        ],
        documents=[
            {"document_type": "gst_certificate", "extracted_fields": {
                "legal_name": "ABC Components Private Limited",
                "address": "Plot 12, Industrial Area, Hyderabad, Telangana"
            }},
            {"document_type": "bank_proof", "extracted_fields": {
                "account_name": "ABC Components Pvt Ltd"
            }},
        ],
    )


@router.post("/verification/check", response_model=VerificationResponse)
def check_supplier(payload: SupplierVerificationRequest):
    result = verify_supplier(payload)
    result.explanation = generate_explanation(result)
    return result
