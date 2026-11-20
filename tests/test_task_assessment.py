"""Task Assessment & Assignment module: templates, evidence and API."""
import json
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import get_db_connection
from src.api.task_assessment_service import (
    GENERAL_SIGNAL_ID,
    build_task_evidence,
    record_task_evidence,
)

DEMO_TENANT = "QUICKLOAN-001"
TASK_SQL_FILES = ("create_task_templates.sql", "create_task_evidence.sql", "seed_task_templates.sql")


@pytest.fixture(scope="module", autouse=True)
def task_schema():
    """Apply the Task Assessment migrations (idempotent), as the backend does at startup."""
    db_dir = Path(__file__).resolve().parents[1] / "db"
    with get_db_connection() as conn, conn.cursor() as cur:
        for name in TASK_SQL_FILES:
            cur.execute((db_dir / name).read_text(encoding="utf-8"))
        conn.commit()


def _violation(rule_id, record_id, signals, outcome="VIOLATION"):
    return {"rule_id": rule_id, "record_id": record_id, "signals_fired": signals, "outcome": outcome}


# ── Templates match the rule knowledge base ─────────────────────────────────

KB_DIR = Path(__file__).resolve().parents[1] / "data" / "dpdp_kb"


def _kb_rules():
    rules = json.loads((KB_DIR / "dpdp_rules.json").read_text(encoding="utf-8"))
    return rules + json.loads((KB_DIR / "policy_rules.json").read_text(encoding="utf-8"))


def _templates():
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT rule_id, signal_id, signal_field, is_active FROM task_templates")
        return {(r["rule_id"], r["signal_id"]): r for r in cur.fetchall()}


def test_every_knowledge_base_signal_has_a_matching_template():
    templates = _templates()
    for rule in _kb_rules():
        for signal in rule["evidence_signals"]:
            template = templates.get((rule["rule_id"], signal["signal_id"]))
            assert template is not None, (rule["rule_id"], signal["signal_id"])
            assert template["signal_field"] == signal["field"], (rule["rule_id"], signal["signal_id"])
        assert templates[(rule["rule_id"], GENERAL_SIGNAL_ID)]["is_active"] is True, rule["rule_id"]


def test_no_active_template_points_to_a_nonexistent_signal():
    real = {(r["rule_id"], s["signal_id"]) for r in _kb_rules() for s in r["evidence_signals"]}
    for (rule_id, signal_id), template in _templates().items():
        if template["is_active"] and signal_id != GENERAL_SIGNAL_ID:
            assert (rule_id, signal_id) in real, (rule_id, signal_id)


def test_context_signals_alone_cannot_reach_the_violation_threshold():
    """A violation always fires at least one actionable (active) signal."""
    templates = _templates()
    for rule in _kb_rules():
        context_weight = sum(
            float(s["weight"]) for s in rule["evidence_signals"]
            if templates[(rule["rule_id"], s["signal_id"])]["is_active"] is False
        )
        assert context_weight < float(rule["violation_threshold"]), rule["rule_id"]


def test_all_active_templates_usable_with_knowledge_base_rules():
    """The test database holds the knowledge-base rules, so no template is skipped."""
    from src.api.task_assessment_service import _active_template_keys

    active = {key for key, t in _templates().items() if t["is_active"]}
    with get_db_connection() as conn, conn.cursor() as cur:
        assert _active_template_keys(cur) == active


# ── Evidence aggregation ─────────────────────────────────────────────────────

def test_build_task_evidence_skips_context_and_counts_distinct_records():
    actionable = {("DPDP-005", "S2"), ("DPDP-005", GENERAL_SIGNAL_ID)}
    evidence = build_task_evidence([
        _violation("DPDP-005", "c1", ["S1", "S2"]),
        _violation("DPDP-005", "c1", ["S1", "S2"]),   # same record twice
        _violation("DPDP-005", "c2", ["S1", "S2"]),
        _violation("DPDP-005", "c3", ["S1", "S2"], outcome="WARNING"),
    ], actionable)
    assert evidence == [{"rule_id": "DPDP-005", "signal_id": "S2", "affected_records_count": 2}]


def test_build_task_evidence_falls_back_to_general_template():
    actionable = {("DPDP-014", "S2"), ("DPDP-014", GENERAL_SIGNAL_ID)}
    evidence = build_task_evidence([_violation("DPDP-014", "e1", ["S1", "S4"])], actionable)
    assert evidence == [{"rule_id": "DPDP-014", "signal_id": GENERAL_SIGNAL_ID, "affected_records_count": 1}]


def test_build_task_evidence_never_fabricates_record_counts():
    evidence = build_task_evidence([_violation("DPDP-009", "unknown", ["S1"])])
    assert evidence == [{"rule_id": "DPDP-009", "signal_id": "S1", "affected_records_count": 0}]


def test_record_task_evidence_failure_does_not_raise():
    class FailingConn:
        @contextmanager
        def transaction(self):
            raise RuntimeError("task tables unavailable")
            yield  # pragma: no cover

    assert record_task_evidence(FailingConn(), DEMO_TENANT, "run_x", []) is None


# ── API ──────────────────────────────────────────────────────────────────────

def test_task_endpoints_require_authentication():
    client = TestClient(app)
    assert client.get(f"/tasks/{DEMO_TENANT}").status_code == 401
    assert client.get(f"/tasks/pdf/{DEMO_TENANT}").status_code == 401


def test_task_endpoints_reject_other_tenants(authorized_client):
    client = authorized_client("SOME-OTHER-TENANT")
    assert client.get(f"/tasks/{DEMO_TENANT}").status_code == 403
    assert client.get(f"/tasks/pdf/{DEMO_TENANT}").status_code == 403


@pytest.fixture(scope="module")
def analysed_run():
    """Analyse the demo tenant once and return (client, analysis response)."""
    from src.api.auth import AuthUser, authenticate_user

    user = AuthUser(id=1, username="task-test", name="Task Test", email="t@example.invalid",
                    role="admin", authorized_tenants=[DEMO_TENANT])
    app.dependency_overrides[authenticate_user] = lambda: user
    client = TestClient(app)
    response = client.post("/analyze", json={"tenant_id": DEMO_TENANT})
    assert response.status_code == 200, response.text
    yield client, response.json()
    app.dependency_overrides.pop(authenticate_user, None)


def test_analysis_generates_tasks_for_every_violated_rule(analysed_run):
    client, analysis = analysed_run
    result = client.get(f"/tasks/{DEMO_TENANT}", params={"audit_run_id": analysis["audit_run_id"]})
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "generated"
    assert body["total_tasks"] == len(body["tasks"]) > 0
    violated = {v["rule_id"] for v in analysis["violations"]}
    assert violated <= {task["rule_id"] for task in body["tasks"]}
    order = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}
    priorities = [order[t["priority"]] for t in body["tasks"]]
    assert priorities == sorted(priorities)
    assert all(t["rule_name"] and t["responsible_team"] and t["remediation_steps"] for t in body["tasks"])


def test_task_pdf_downloads(analysed_run):
    client, analysis = analysed_run
    result = client.get(f"/tasks/pdf/{DEMO_TENANT}", params={"audit_run_id": analysis["audit_run_id"]})
    assert result.status_code == 200
    assert result.headers["content-type"] == "application/pdf"
    assert result.content.startswith(b"%PDF")


def test_run_without_task_evidence_is_reported_as_not_generated(analysed_run):
    client, analysis = analysed_run
    run_id = analysis["audit_run_id"]
    with get_db_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT rule_id, signal_id, affected_records_count FROM task_evidence "
                    "WHERE tenant_id = %s AND audit_run_id = %s", (DEMO_TENANT, run_id))
        saved = cur.fetchall()
        cur.execute("DELETE FROM task_evidence WHERE tenant_id = %s AND audit_run_id = %s", (DEMO_TENANT, run_id))
        conn.commit()
    try:
        body = client.get(f"/tasks/{DEMO_TENANT}", params={"audit_run_id": run_id}).json()
        assert body["status"] == "not_generated"
        assert body["tasks"] == []
    finally:
        with get_db_connection() as conn, conn.cursor() as cur:
            for row in saved:
                cur.execute("INSERT INTO task_evidence (tenant_id, audit_run_id, rule_id, signal_id, affected_records_count) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (DEMO_TENANT, run_id, row["rule_id"], row["signal_id"], row["affected_records_count"]))
            conn.commit()


def test_unknown_audit_run_returns_404(analysed_run):
    client, _ = analysed_run
    assert client.get(f"/tasks/{DEMO_TENANT}", params={"audit_run_id": "run_does_not_exist"}).status_code == 404
