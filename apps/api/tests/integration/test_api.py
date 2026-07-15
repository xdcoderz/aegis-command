from fastapi.testclient import TestClient

from finspark.core import get_settings
from finspark.main import create_app


def test_health_and_assessment_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FINSPARK_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("FINSPARK_PQC_REQUIRED", "false")
    get_settings.cache_clear()
    app = create_app()

    payload = {
        "session_id": "demo-attack-01",
        "user_id": "admin-00",
        "role": "database-admin",
        "occurred_at": "2026-03-01T02:15:00Z",
        "source_ip": "198.51.100.77",
        "device_id": "unmanaged-laptop",
        "resource": "core-banking-master",
        "resource_sensitivity": 1.0,
        "commands": ["mimikatz credential dump", "disable audit"],
        "session_duration_minutes": 2,
        "privilege_level": 5,
        "privilege_escalated": True,
        "failed_auth_attempts": 4,
        "bytes_transferred": 50000000,
    }

    with TestClient(app) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        response = client.post("/api/v1/assessments", json=payload)
        assert response.status_code == 201
        assessment = response.json()
        assert assessment["decision"] == "BLOCK"
        assert assessment["risk_score"] >= 70
        detail = client.get(f"/api/v1/assessments/{assessment['assessment_id']}")
        assert detail.status_code == 200

    get_settings.cache_clear()

