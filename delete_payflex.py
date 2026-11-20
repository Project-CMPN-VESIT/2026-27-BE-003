import sys
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:rasika23@localhost:5432/tenant_db')
try:
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM tenants WHERE tenant_id = 'PAYFLEX-002'"))
        conn.commit()
    print("PAYFLEX-002 deleted successfully.")
except Exception as e:
    print(f"Error: {e}")
