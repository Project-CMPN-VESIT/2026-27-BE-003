import psycopg, json
conn = psycopg.connect('dbname=tenant_db user=postgres password=rasika23')
cur = conn.cursor()
cur.execute('SELECT result_json FROM evaluation_results WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 5', ('NEXUSNEOBANK-005',))
rows = cur.fetchall()
for i, r in enumerate(reversed(rows)):
    res = r[0]
    score = res.get('risk_score')
    v = res.get('violations', [])
    highs = [x['rule_id'] for x in v if x.get('severity') == 'HIGH']
    crits = [x['rule_id'] for x in v if x.get('severity') == 'CRITICAL']
    all_rules = [x['rule_id'] for x in v]
    print(f'Run {i} | Score: {score} | Highs: {highs} | Crits: {crits} | All: {all_rules}')
