import pandas as pd
import psycopg

print('--- RAW CSV COLUMNS ---')
df = pd.read_csv('data/test_tenants/RURALCRED-004/customer_master.csv')
print('customer_master.csv columns:', list(df.columns))

print('\n--- DB COLUMNS ---')
conn = psycopg.connect('postgresql://postgres:rasika23@localhost:5432/tenant_db')
cur = conn.cursor()
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'customer_master'
""")
db_cols = [row[0] for row in cur.fetchall()]
print('customer_master table columns:', db_cols)
