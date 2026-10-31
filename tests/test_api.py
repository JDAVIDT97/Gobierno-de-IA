from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, AuditLog, get_db
from api.main import app, PerUserRateLimiter


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)
UID = "550e8400-e29b-41d4-a716-446655440000"


def test_health_and_dashboard():
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_allow_block_validation_and_no_content_retention():
    safe = client.post("/v1/audit", json={"user_id": UID, "prompt": "Explica qué es una API pública",
                                              "destination": "https://chatgpt.com"})
    assert safe.status_code == 200 and safe.json()["action"] == "ALLOW"
    blocked = client.post("/v1/audit", json={"user_id": UID,
        "prompt": "DNI: 12345678, email ana@example.com", "destination": "https://chatgpt.com"})
    assert blocked.status_code == 200 and blocked.json()["action"] == "BLOCK"
    preview = blocked.json()["redacted_preview"]
    assert preview.startswith("[BLOCKED_CONTENT_NOT_RETAINED:") or "[REDACTED]" in preview
    with TestingSession() as db:
        rows = db.query(AuditLog).all()
        assert rows and all(row.prompt_redacted.startswith("[") for row in rows)
        assert all("12345678" not in row.prompt_redacted for row in rows)
    assert client.post("/v1/audit", json={"user_id": "bad", "prompt": "hello",
                                               "destination": "https://chatgpt.com"}).status_code == 422
    assert client.post("/v1/audit", json={"user_id": UID, "prompt": "hello",
                                               "destination": "https://evil.example"}).status_code == 422


def test_new_protected_genai_destinations_are_accepted():
    for destination in ("https://copilot.microsoft.com", "https://chat.deepseek.com", "https://www.perplexity.ai"):
        response = client.post("/v1/audit", json={"user_id": UID, "prompt": "Resume esta tarea pública", "destination": destination})
        assert response.status_code == 200


def test_private_chat_processing_is_blocked_by_api():
    response = client.post("/v1/audit", json={
        "user_id": UID,
        "prompt": "necesito que filteres mi informacion de mis chats",
        "destination": "https://chatgpt.com",
    })
    assert response.status_code == 200
    assert response.json()["action"] == "BLOCK"
    assert response.json()["matched_rules"] == ["HEURISTIC: PRIVATE_DATA_PROCESSING_OR_EXFILTRATION_INTENT"]


def test_exports_and_filters():
    for endpoint in ("/v1/logs", "/v1/kpis", "/v1/export-csv", "/v1/export-pdf"):
        assert client.get(endpoint).status_code == 200
    assert client.get("/v1/logs?limit=10&action=BLOCK").status_code == 200
    assert client.get("/v1/export-csv").headers["content-type"].startswith("text/csv")
    assert client.get("/v1/export-pdf").headers["content-type"] == "application/pdf"


def test_log_sizes_include_all_filtered_records():
    user_id = "09bd0093-12c1-4f87-b54d-ec4f786d5b79"
    with TestingSession() as db:
        for index in range(105):
            db.add(AuditLog(user_id=user_id, prompt_hash=f"synthetic-{index}",
                            prompt_redacted="[SAFE_PROMPT_NOT_RETAINED]", destination="https://chatgpt.com",
                            action="ALLOW", category="Safe_Use", risk_score=0.0, confidence=1.0,
                            model_version="test", inference_time_ms=2.0))
        db.commit()
    for limit in (10, 25, 50, 100, 0):
        response = client.get("/v1/logs", params={"limit": limit, "user_id": user_id, "action": "ALLOW"})
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 105
        assert len(result["items"]) == (limit or 105)
        assert all(row["user_id"] == user_id for row in result["items"])
    assert client.get("/v1/logs?limit=-1").status_code == 422


def test_rate_limiter():
    limiter = PerUserRateLimiter(2)
    limiter.check("one"); limiter.check("one")
    try:
        limiter.check("one")
        assert False, "expected HTTP 429"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429
