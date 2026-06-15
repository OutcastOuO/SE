import os
import sys
from pathlib import Path


if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])

project_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_dir))

os.environ.setdefault("VMS_DATA_DIR", str(project_dir / "tmp_test_data"))

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)
for path in ["/", "/health", "/api/chaos/health", "/metrics"]:
    response = client.get(path)
    preview = response.text[:120].replace("\n", " ")
    print(path, response.status_code, preview)
    response.raise_for_status()

assert client.get("/health").json()["status"] == "ok"
assert "vms_app_uptime_seconds" in client.get("/metrics").text
print("verify-app passed")
