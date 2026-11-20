import json
with open('data/dpdp_kb/dpdp_rules.json') as f:
    j = json.load(f)
for r in j:
    if r['primary_table'] == 'system_inventory':
        print(f"{r['rule_id']} - {r['severity']} - {r['rule_name']}")
