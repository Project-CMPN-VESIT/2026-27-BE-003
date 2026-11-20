import json
with open('data/dpdp_kb/dpdp_rules.json') as f:
    j = json.load(f)
for r in j:
    if r['severity'] == 'CRITICAL':
        print(f"{r['rule_id']} - {r['primary_table']}")
