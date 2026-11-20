import requests, json

BASE = "http://127.0.0.1:8000"
USERNAME = "rasika3"
PASSWORD = "Rasika_23"
TENANT   = "QUICKLOAN-001"
RUNS     = 100

r = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": PASSWORD})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

results = []
for i in range(RUNS):
    r = requests.post(f"{BASE}/analyze", json={"tenant_id": TENANT}, headers=headers)
    d = r.json()
    results.append({
        "risk_score": d.get("risk_score"),
        "risk_tier": d.get("risk_tier"),
        "rules_violated": sorted(v.get("rule_id", "") for v in d.get("violations", [])),
    })
    print(f"run {i+1}/{RUNS}: score={d.get('risk_score')} tier={d.get('risk_tier')}")

baseline = results[0]
identical = sum(1 for r in results if r == baseline)
print(f"\n{identical}/{RUNS} runs identical to the first run.")
if identical != RUNS:
    for i, r in enumerate(results):
        if r != baseline:
            print(f"  run {i+1} differed: {r}")

with open("validation/phase1_determinism_results.json", "w") as f:
    json.dump(results, f, indent=2)
