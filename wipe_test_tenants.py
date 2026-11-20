import psycopg
import os

DB_PASSWORD = os.getenv('DB_PASSWORD', 'rasika23')

def wipe():
    conn = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="tenant_db",
        user="postgres",
        password=DB_PASSWORD
    )
    with conn.cursor() as cur:
        tenants = ["t_clean"] + [f"t_dpdp{i:03d}" for i in range(1, 17)]
        for t in tenants:
            cur.execute("DELETE FROM audit_runs WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM dsar_requests WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM access_logs WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM transaction_events WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM consent_records WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM data_lifecycle WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM security_events WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM system_inventory WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM customer_master WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM policies WHERE tenant_id = %s", (t,))
            cur.execute("DELETE FROM governance_config WHERE tenant_id = %s", (t,))
        conn.commit()
    print("Wiped successfully")
    
if __name__ == "__main__":
    wipe()
