import requests
import os
from pathlib import Path

BASE = "http://127.0.0.1:8000"
USERNAME = "rasika3"
PASSWORD = "Rasika_23"
TENANT = "NEXUSNEOBANK-005"

r = requests.post(f"{BASE}/auth/login", json={"username": USERNAME, "password": PASSWORD})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

tenant_dir = Path(f"data/test_tenants/{TENANT}")
files_to_upload = {}

for file_path in tenant_dir.glob("*.csv"):
    key = file_path.stem # e.g. 'governance_config'
    files_to_upload[key] = (file_path.name, open(file_path, "rb"), "text/csv")

print(f"Uploading files for {TENANT}...")
upload_res = requests.post(
    f"{BASE}/analyze/upload",
    headers=headers,
    data={"tenant_id": TENANT, "tenant_name": TENANT},
    files=files_to_upload
)

if upload_res.status_code == 200:
    print("Upload successful!")
else:
    print(f"Upload failed: {upload_res.status_code} {upload_res.text}")
