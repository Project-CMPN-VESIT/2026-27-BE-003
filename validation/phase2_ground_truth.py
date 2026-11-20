import os, json
os.environ["FINCOMPLY_TEST_CREDENTIALS"] = json.dumps({
    __import__("hashlib").sha256(b"secure_test_admin_token_2026").hexdigest(): {
        "username": "test_admin",
        "role": "admin",
        "authorized_tenants": ["t_clean"] + [f"t_dpdp{i:03d}" for i in range(1, 17)],
    }
})
os.environ["ENVIRONMENT"] = "test"
os.environ["HASH_VERSION"] = "legacy"

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
ADMIN_TOKEN = "secure_test_admin_token_2026"
HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

FIXTURE_ROOT = Path("tests/fixtures/deterministic_compliance_package")
manifest = json.loads((FIXTURE_ROOT / "expected_results.json").read_text())

SEVERITY_ORDER = ["NOT_APPLICABLE", "PASS", "NOT_ASSESSABLE", "WARNING", "VIOLATION", "FAILED"]
VIOLATION_STATES = {"VIOLATION", "FAILED"}

# tally[rule_id] = {"tp": 0, "fp": 0, "fn": 0}
tally = {}

for tenant_id, expected in manifest.items():
    tenant_dir = FIXTURE_ROOT / tenant_id
    files = {}
    for fname in sorted(os.listdir(tenant_dir)):
        if fname.endswith(".csv"):
            field = fname.replace(".csv", "")
            files[field] = (fname, open(tenant_dir / fname, "rb").read(), "text/csv")

    up = client.post("/analyze/upload", data={"tenant_id": tenant_id, "tenant_name": tenant_id.upper()},
                      files=files, headers=HEADERS)
    assert up.status_code == 200, f"upload failed for {tenant_id}: {up.text}"

    res = client.post("/analyze", json={"tenant_id": tenant_id}, headers=HEADERS)
    assert res.status_code == 200, f"analyze failed for {tenant_id}: {res.text}"
    findings = res.json().get("findings") or []

    # Roll per-record findings up into one outcome per rule (max severity wins)
    actual_by_rule = {f"DPDP-{i:03d}": "NOT_APPLICABLE" for i in range(1, 17)}
    for f in findings:
        rid = f.get("rule_id")
        if not rid or rid.startswith("POLICY-"):
            continue
        outcome = f.get("outcome")
        if outcome in SEVERITY_ORDER and SEVERITY_ORDER.index(outcome) > SEVERITY_ORDER.index(actual_by_rule.get(rid, "NOT_APPLICABLE")):
            actual_by_rule[rid] = outcome

    expected_by_rule = expected["outcome_count_by_rule"]
    for rid, exp_state in expected_by_rule.items():
        got_state = actual_by_rule.get(rid, "NOT_APPLICABLE")
        exp_violation = exp_state in VIOLATION_STATES
        got_violation = got_state in VIOLATION_STATES
        t = tally.setdefault(rid, {"tp": 0, "fp": 0, "fn": 0})
        if exp_violation and got_violation:
            t["tp"] += 1
        elif got_violation and not exp_violation:
            t["fp"] += 1
        elif exp_violation and not got_violation:
            t["fn"] += 1

    print(f"{tenant_id}: done")

print(f"\n{'Rule':10} {'TP':>3} {'FP':>3} {'FN':>3} {'Precision':>10} {'Recall':>8} {'F1':>6}")
rows = []
for rid in sorted(tally):
    t = tally[rid]
    tp, fp, fn = t["tp"], t["fp"], t["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    rows.append({"rule_id": rid, "TP": tp, "FP": fp, "FN": fn, "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)})
    print(f"{rid:10} {tp:3} {fp:3} {fn:3} {precision:10.3f} {recall:8.3f} {f1:6.3f}")

with open("validation/phase2_ground_truth_results.json", "w") as f:
    json.dump(rows, f, indent=2)
