import psycopg
conn = psycopg.connect(dbname='tenant_db', user='postgres', password='rasika23', host='localhost')
cur = conn.cursor()
cur.execute("SELECT column_default FROM information_schema.columns WHERE table_name='audit_runs' AND column_name='hash_version'")
print(cur.fetchone()[0])
conn.close()
