import psycopg

conn = psycopg.connect(
"dbname=tenant_db user=postgres password=rasika23"
)

conn.autocommit = True

cur = conn.cursor()

cur.execute(
"""
UPDATE users
SET authorized_tenants = authorized_tenants ||
ARRAY[
'QUICKLOAN-001',
'PAYFLEX-002',
'WEALTHNEST-003',
'RURALCRED-004',
'NEXUSNEOBANK-005'
]
WHERE username = %s
""",
('rasika3',)
)

cur.execute("SELECT username, authorized_tenants FROM users")
print(cur.fetchall())

cur.close()
conn.close()
