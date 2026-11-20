import psycopg
import os

DB_PASSWORD = os.getenv('DB_PASSWORD', 'rasika23')

def alter():
    conn = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="tenant_db",
        user="postgres",
        password=DB_PASSWORD
    )
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE audit_runs ALTER COLUMN hash_version SET DEFAULT 'legacy'")
        conn.commit()
    print("Altered successfully")
    
if __name__ == "__main__":
    alter()
