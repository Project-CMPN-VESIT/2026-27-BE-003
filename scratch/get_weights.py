import json, psycopg

with open('data/dpdp_kb/dpdp_rules.json') as f:
    j = json.load(f)

weights = {}
for r in j:
    weights[r['rule_id']] = r['risk_weight']
    if r['rule_id'] in ['DPDP-001', 'DPDP-004', 'DPDP-011', 'DPDP-009', 'DPDP-008', 'DPDP-002', 'DPDP-006']:
        print(f"{r['rule_id']} weight: {r['risk_weight']}")

conn = psycopg.connect('dbname=tenant_db user=postgres password=rasika23')
cur = conn.cursor()
cur.execute("SELECT result_json FROM evaluation_results WHERE tenant_id = 'NEXUSNEOBANK-005' ORDER BY created_at DESC LIMIT 5")
rows = cur.fetchall()
for i, r in enumerate(reversed(rows)):
    res = r[0]
    print(f"Run {i} max_possible: {res.get('max_possible')}, raw_score: {res.get('raw_score')}, score: {res.get('risk_score')}")
