import os
import sys
from pathlib import Path
import pandas as pd
import psycopg

PROJECT_ROOT = Path("C:/Users/Rasika/Documents/compliance_sys")
sys.path.insert(0, str(PROJECT_ROOT))

from src.anonymization.field_mapper import anonymize_dataframe
from src.agent_layer.query_builder import build_query
from src.agent_layer.orchestrator import load_active_rule_metadata

TENANT = "RURALCRED-004"

def validate_integrity():
    print("--- 1. INPUT VALUE (Raw CSV) ---")
    df = pd.read_csv(f"data/test_tenants/{TENANT}/customer_master.csv")
    first_row = df.iloc[0]
    raw_customer_id = first_row.get("customer_id", "MISSING_ID")
    raw_customer_hash = first_row.get("customer_hash", "MISSING_HASH")
    raw_is_minor = first_row["is_minor"]
    raw_kyc_status = first_row["kyc_status"]
    
    print(f"Row 0 -> customer_hash: {raw_customer_hash}, is_minor: {raw_is_minor}, kyc_status: {raw_kyc_status}")

    print("\n--- 2. MAPPED VALUE (Anonymization Layer) ---")
    # Wrap in dataframe for anonymize_dataframe
    df_single = pd.DataFrame([first_row])
    mapped_dicts = anonymize_dataframe(df_single, "customer_master", TENANT)
    mapped_row = mapped_dicts[0]
    
    mapped_hash = mapped_row["customer_hash"]
    mapped_is_minor = mapped_row["is_minor"]
    mapped_kyc_status = mapped_row["kyc_status"]
    print(f"Mapped -> customer_hash: {mapped_hash}, is_minor: {mapped_is_minor}, kyc_status: {mapped_kyc_status}")

    print("\n--- 3. DATABASE VALUE (Persistence Layer) ---")
    conn = psycopg.connect('postgresql://postgres:rasika23@localhost:5432/tenant_db')
    cur = conn.cursor()
    cur.execute(f"SELECT customer_hash, is_minor, kyc_status FROM customer_master WHERE tenant_id = '{TENANT}' AND customer_hash = '{mapped_hash}'")
    db_row = cur.fetchone()
    if db_row:
        db_hash, db_is_minor, db_kyc_status = db_row
        print(f"DB -> customer_hash: {db_hash}, is_minor: {db_is_minor}, kyc_status: {db_kyc_status}")
    else:
        print("DB -> ROW NOT FOUND")
        return

    print("\n--- 4. EVALUATED VALUE (Rule Engine / Orchestrator) ---")
    rule_metadata = load_active_rule_metadata()
    dpdp_005 = rule_metadata.get("DPDP-005")
    
    sql, params = build_query(dpdp_005, TENANT)
    # The query for DPDP-005 fetches from customer_master and consent_records
    cur.execute(sql, params)
    
    columns = [desc[0] for desc in cur.description]
    all_eval_rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    # Find the specific customer
    eval_row = next((r for r in all_eval_rows if r["customer_hash"] == mapped_hash), None)
    if eval_row:
        eval_hash = eval_row["customer_hash"]
        eval_is_minor = eval_row["is_minor"]
        eval_kyc_status = eval_row["kyc_status"]
        print(f"Eval -> customer_hash: {eval_hash}, is_minor: {eval_is_minor}, kyc_status: {eval_kyc_status}")
    else:
        print("Eval -> ROW NOT FOUND IN QUERY")
        return

    print("\n--- INTEGRITY ASSERTIONS ---")
    assert bool(raw_is_minor) == bool(mapped_is_minor) == bool(db_is_minor) == bool(eval_is_minor), "is_minor mutated!"
    assert str(raw_kyc_status) == str(mapped_kyc_status) == str(db_kyc_status) == str(eval_kyc_status), "kyc_status mutated!"
    print("ALL FIELDS MATERIALLY PRESERVED WITHOUT SILENT MUTATION.")

if __name__ == "__main__":
    validate_integrity()
