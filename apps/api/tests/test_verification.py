from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_supplier_verification_flags_bank_mismatch():
    payload = {
        "supplier_name": "ABC Components Private Limited",
        "gstin": "36ABCDE1234F1Z5",
        "website": "https://example.com",
        "registered_address": "Hyderabad Telangana",
        "bank_account_name": "Someone Else Trading",
        "evidence": [],
        "documents": []
    }
    response = client.post("/api/v1/verification/check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["supplier_name"] == payload["supplier_name"]
    assert any(flag["code"] == "BANK_NAME_MISMATCH" for flag in data["flags"])
