import os
import sys
import tempfile
import time
from pathlib import Path
from fastapi.testclient import TestClient
import psycopg

PROJECT_ROOT = "C:/Users/Rasika/Documents/compliance_sys"
sys.path.insert(0, PROJECT_ROOT)
os.environ["ENVIRONMENT"] = "development"

from src.api.main import app

client = TestClient(app)
CANARY = "CANARY-TEST-PII-99999"
TENANT = "t_dpdp001"
RURALCRED_PATH = Path(PROJECT_ROOT) / "data/test_tenants/ruralcred"

def run_test():
    print("=== Retention and Deletion Canary Test ===\n")
    
    conn = psycopg.connect('postgresql://postgres:rasika23@localhost:5432/tenant_db')
    conn.execute(f"DELETE FROM users WHERE username = 'canary_admin_2'")
    conn.commit()
    
    res = client.post("/auth/register", json={
        "name": "Canary Admin 2", "email": "canary2@example.com", "username": "canary_admin_2",
        "password": "Password123!", "tenant_id": TENANT, "tenant_name": "Canary Tenant"
    })
    
    # login
    try:
        token = client.post("/auth/login", json={"username": "canary_admin_2", "password": "Password123!"}).json()["access_token"]
    except Exception as e:
        print("Login failed:", e, client.post("/auth/login", json={"username": "canary_admin_2", "password": "Password123!"}).json())
        return
        
    print(f"Uploading ruralcred data with CANARY='{CANARY}'...")
    files_payload = {}
    
    for file_path in RURALCRED_PATH.glob("*.csv"):
        filename = file_path.name
        content = file_path.read_bytes()
        
        # Inject canary into customer_master.csv
        if filename == "customer_master.csv":
             # customer_id,tenant_id,is_minor,data_principal_type,account_status,kyc_status,country,created_at,first_name,last_name,email,phone
             header = content.split(b"\n")[0]
             row = f"{CANARY},{TENANT},False,individual,active,verified,IN,2023-01-01,Canary,Bird,{CANARY}@example.com,1234567890\n".encode()
             content += b"\n" + row
             
        files_payload[filename.replace(".csv", "")] = (filename, content, "text/csv")
        
    res = client.post("/analyze/upload", 
                      data={"tenant_id": TENANT, "tenant_name": "RuralCred (Canary)"},
                      files=files_payload, 
                      headers={"Authorization": f"Bearer {token}"})
    
    if res.status_code != 200:
        print(f"Upload failed! {res.status_code}: {res.text}")
    else:
        print("Upload Successful.")
        
    print("\n--- Validation ---")
    
    # 1. Check if temp files exist with canary
    tempdir = tempfile.gettempdir()
    found_canary_in_temp = False
    for root, dirs, files in os.walk(tempdir):
        if "FinComply" in root or "tmp" in root: # heuristic
            for file in files:
                if file.endswith(".csv"):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            if CANARY in f.read():
                                found_canary_in_temp = True
                    except:
                        pass
    print(f"Canary found in temp directory: {found_canary_in_temp}")

    # 2. Check DB for canary
    cur = conn.cursor()
    # Check customer_master
    cur.execute(f"SELECT * FROM customer_master WHERE tenant_id = '{TENANT}'")
    cm_rows = cur.fetchall()
    found_in_cm = any(CANARY in str(row) for row in cm_rows)
    print(f"Canary found in customer_master: {found_in_cm}")
    
    # Check audit runs summary
    cur.execute(f"SELECT validation_summary FROM audit_runs WHERE tenant_id = '{TENANT}'")
    ar_rows = cur.fetchall()
    found_in_ar = any(CANARY in str(row) for row in ar_rows)
    print(f"Canary found in audit_runs: {found_in_ar}")
    
    # Check evaluation results
    cur.execute(f"SELECT result_json FROM evaluation_results WHERE tenant_id = '{TENANT}'")
    ev_rows = cur.fetchall()
    found_in_ev = any(CANARY in str(row) for row in ev_rows)
    print(f"Canary found in evaluation_results: {found_in_ev}")

if __name__ == "__main__":
    run_test()
