import json, psycopg
conn = psycopg.connect('dbname=tenant_db user=postgres password=rasika23')
cur = conn.cursor()
cur.execute('SELECT result_json FROM evaluation_results WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 5', ('NEXUSNEOBANK-005',))
rows = cur.fetchall()
for i, r in enumerate(reversed(rows)):
    res = r[0]
    score = res.get('risk_score')
    raw = res.get('compliance_score', {}).get('score_percentage')
    contribs = res.get('risk_contributions', {})
    print(f'Run {i} | Score: {score} | Raw/Score%: {raw} | Contribs: {contribs}')
