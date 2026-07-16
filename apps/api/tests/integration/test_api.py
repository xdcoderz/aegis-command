from fastapi.testclient import TestClient

from finspark.core import get_settings
from finspark.main import create_app


def session_payload() -> dict[str, object]:
    return {
        "event_id": "f0fc6325-f50b-4ffc-9f40-f77bb5f80ea6",
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


def test_health_and_assessment_flow(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FINSPARK_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("FINSPARK_PQC_REQUIRED", "false")
    get_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        health = client.get(
            "/api/v1/health/live", headers={"X-Correlation-ID": "integration-test"}
        )
        assert health.status_code == 200
        assert health.headers["X-Correlation-ID"] == "integration-test"
        assert health.headers["X-Content-Type-Options"] == "nosniff"

        oversized = client.post(
            "/api/v1/assessments",
            content=b"{}",
            headers={"Content-Length": "1048577", "X-Correlation-ID": "oversized-test"},
        )
        assert oversized.status_code == 413
        assert oversized.headers["X-Correlation-ID"] == "oversized-test"
        assert oversized.headers["Cache-Control"] == "no-store"

        response = client.post("/api/v1/assessments", json=session_payload())
        assert response.status_code == 201
        assert response.headers["X-Idempotent-Replay"] == "false"
        assessment = response.json()
        assert assessment["decision"] == "BLOCK"
        assert assessment["risk_score"] >= 70
        assert assessment["enforcement_status"] == "NOT_CONFIGURED"

        replay = client.post("/api/v1/assessments", json=session_payload())
        assert replay.status_code == 200
        assert replay.headers["X-Idempotent-Replay"] == "true"
        assert replay.json()["assessment_id"] == assessment["assessment_id"]

        listed = client.get("/api/v1/assessments")
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        detail = client.get(f"/api/v1/assessments/{assessment['assessment_id']}")
        assert detail.status_code == 200

        receipt = client.get(f"/api/v1/assessments/{assessment['assessment_id']}/receipt")
        assert receipt.status_code == 200
        assert receipt.json()["valid"] is False
        assert len(receipt.json()["payload_sha256"]) == 64

        review = client.post(
            f"/api/v1/assessments/{assessment['assessment_id']}/reviews",
            json={"disposition": "MALICIOUS", "comment": "Confirmed credential attack"},
        )
        assert review.status_code == 201
        assert review.json()["reviewer"] == "local-development"
        reviews = client.get(f"/api/v1/assessments/{assessment['assessment_id']}/reviews")
        assert reviews.status_code == 200
        assert len(reviews.json()) == 1

        overview = client.get("/api/v1/overview")
        assert overview.status_code == 200
        assert overview.json()["metrics"]["sessions_monitored_24h"] == 1
        assert overview.json()["metrics"]["active_flags"] == 1
        assert overview.json()["top_sessions"][0]["session_id"] == "demo-attack-01"

        sessions = client.get("/api/v1/sessions?sort=risk_desc&min_risk=70")
        assert sessions.status_code == 200
        assert sessions.json()["total"] == 1
        assert sessions.json()["items"][0]["role"] == "database-admin"
        assert sessions.json()["items"][0]["resource"] == "core-banking-master"
        assert client.get("/api/v1/sessions?min_risk=80&max_risk=20").status_code == 422

        investigation = client.get("/api/v1/sessions/demo-attack-01")
        assert investigation.status_code == 200
        investigation_body = investigation.json()
        assert investigation_body["severity"] == "CRITICAL"
        assert len(investigation_body["timeline"]) >= 4
        assert len(investigation_body["baseline"]) == 5
        assert len(investigation_body["risk_factors"]) == 5
        assert investigation_body["raw_logs"][1]["event_type"] == "process.command"

        action = client.post(
            "/api/v1/sessions/demo-attack-01/action",
            json={"action": "BLOCK", "note": "Contain session and preserve evidence"},
        )
        assert action.status_code == 201
        assert action.json()["actor"] == "local-development"
        assert action.json()["enforcement_status"] == "NOT_CONFIGURED"

        policy = client.get("/api/v1/policies")
        assert policy.status_code == 200
        assert policy.json()["step_up_threshold"] == 40
        updated_policy = client.put(
            "/api/v1/policies",
            json={"step_up_threshold": 35, "block_threshold": 80},
        )
        assert updated_policy.status_code == 200
        assert updated_policy.json()["version"] == 2
        assert updated_policy.json()["updated_by"] == "local-development"
        invalid_policy = client.put(
            "/api/v1/policies",
            json={"step_up_threshold": 80, "block_threshold": 70},
        )
        assert invalid_policy.status_code == 422

        audit = client.get("/api/v1/audit?session_id=demo-attack-01")
        assert audit.status_code == 200
        assert audit.json()["total"] == 2
        assert {item["event_type"] for item in audit.json()["items"]} == {
            "RISK_DECISION",
            "ANALYST_RESPONSE",
        }

        metrics = client.get("/api/v1/operations/metrics")
        assert metrics.status_code == 200
        assert "finspark_assessments_total" in metrics.text

    with TestClient(create_app()) as restarted:
        persisted_policy = restarted.get("/api/v1/policies")
        assert persisted_policy.status_code == 200
        assert persisted_policy.json()["version"] == 2
        persisted_audit = restarted.get("/api/v1/audit?session_id=demo-attack-01")
        assert persisted_audit.json()["total"] == 2

    get_settings.cache_clear()


def test_api_key_roles_are_enforced(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FINSPARK_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setenv("FINSPARK_PQC_REQUIRED", "false")
    monkeypatch.setenv("FINSPARK_AUTH_ENABLED", "true")
    monkeypatch.setenv(
        "FINSPARK_API_KEYS",
        '{"observer-key-0001":"observer","analyst-key-0001":"analyst"}',
    )
    get_settings.cache_clear()
    app = create_app()

    with TestClient(app) as client:
        missing = client.get("/api/v1/assessments")
        assert missing.status_code == 401
        assert missing.headers["WWW-Authenticate"] == "ApiKey"

        observer_headers = {"X-API-Key": "observer-key-0001"}
        assert client.get("/api/v1/assessments", headers=observer_headers).status_code == 200
        assert client.get("/api/v1/overview", headers=observer_headers).status_code == 200
        forbidden = client.post(
            "/api/v1/assessments", json=session_payload(), headers=observer_headers
        )
        assert forbidden.status_code == 403

        analyst_headers = {"X-API-Key": "analyst-key-0001"}
        created = client.post(
            "/api/v1/assessments", json=session_payload(), headers=analyst_headers
        )
        assert created.status_code == 201
        assessment_id = created.json()["assessment_id"]
        review = client.post(
            f"/api/v1/assessments/{assessment_id}/reviews",
            headers=analyst_headers,
            json={"disposition": "SUSPICIOUS", "comment": "Escalated for investigation"},
        )
        assert review.status_code == 201
        assert review.json()["reviewer"].endswith("y-0001")
        forbidden_action = client.post(
            "/api/v1/sessions/demo-attack-01/action",
            headers=observer_headers,
            json={"action": "BLOCK", "note": "Observer cannot contain sessions"},
        )
        assert forbidden_action.status_code == 403
        forbidden_policy = client.put(
            "/api/v1/policies",
            headers=analyst_headers,
            json={"step_up_threshold": 35, "block_threshold": 80},
        )
        assert forbidden_policy.status_code == 403

    get_settings.cache_clear()
