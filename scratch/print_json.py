import json, psycopg
conn = psycopg.connect('dbname=tenant_db user=postgres password=rasika23')
cur = conn.cursor()
cur.execute('SELECT result_json FROM evaluation_results WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 1', ('NEXUSNEOBANK-005',))
res = cur.fetchone()[0]
print(json.dumps(res, indent=2))
