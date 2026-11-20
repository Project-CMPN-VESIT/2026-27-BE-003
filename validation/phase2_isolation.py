import requests, json, sys

BASE = "http://127.0.0.1:8000"
USERNAME = "rasika3"
PASSWORD = "Rasika_23"
TENANTS  = ["PAYFLEX-002", "QUICKLOAN-001", "NEXUSNEOBANK-005"]

if len(sys.argv) > 1:
    output_file = sys.argv[1]
else:
    output_file = "validation/phase2_results.json"

r = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": PASSWORD})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

results = {}

for tenant in TENANTS:
    print(f"Running analysis for {tenant}...")
    r = requests.post(f"{BASE}/analyze", json={"tenant_id": tenant}, headers=headers)
    
    if r.status_code != 200:
        print(f"Error for {tenant}: {r.text}")
        continue
        
    d = r.json()
    results[tenant] = {
        "risk_score": d.get("risk_score"),
        "risk_tier": d.get("risk_tier"),
        "rules_violated": sorted(v.get("rule_id", "") for v in d.get("violations", [])),
    }
    print(f"  -> Score: {d.get('risk_score')}, Tier: {d.get('risk_tier')}, Violations: {len(results[tenant]['rules_violated'])}")

with open(output_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to {output_file}")
