import psycopg
conn = psycopg.connect(dbname='tenant_db', user='postgres', password='rasika23', host='localhost')
cur = conn.cursor()
cur.execute("ALTER TABLE audit_runs ALTER COLUMN hash_version SET DEFAULT 'v2'")
cur.execute("UPDATE audit_runs SET hash_version = 'v2' WHERE hash_version = 'legacy' OR hash_version = 'v1'")
conn.commit()
print('Fixed default and updated rows')
conn.close()
