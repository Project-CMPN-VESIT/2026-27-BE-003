import psycopg, json
conn = psycopg.connect('dbname=tenant_db user=postgres password=rasika23')
cur = conn.cursor()
for t in ['PAYFLEX-002', 'QUICKLOAN-001', 'RURALCRED-004', 'WEALTHNEST-003', 'NEXUSNEOBANK-005']:
    cur.execute("SELECT result_json->>'risk_score', result_json->>'risk_tier' FROM evaluation_results WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 1", (t,))
    res = cur.fetchone()
    if res:
        print(t, res[0], res[1])
    else:
        print(t, 'Not found')
