
import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from samvaad.api.main import app
from samvaad.db.session import get_db_context
from samvaad.core.auth import verify_supabase_token

# Mock Auth to bypass Supabase
def mock_verify_token(token):
    # Token format: "mock-user-id:email"
    parts = token.split(":")
    if len(parts) == 2:
        return {"sub": parts[0], "email": parts[1], "aud": "authenticated"}
    raise Exception("Invalid mock token")

# Patch the auth verification
import samvaad.core.auth
import samvaad.api.deps
samvaad.core.auth.verify_supabase_token = mock_verify_token
samvaad.api.deps.verify_supabase_token = mock_verify_token

client = TestClient(app)

def test_data_leak_scenario():
    print("\n--- Starting Full Stack Leak Test ---")
    
    import uuid
    uid_a = str(uuid.uuid4())
    uid_b = str(uuid.uuid4())
    
    user_a_token = f"user_a_{uid_a}:a_{uid_a}@test.com"
    user_b_token = f"user_b_{uid_b}:b_{uid_b}@test.com"
    
    headers_a = {"Authorization": f"Bearer {user_a_token}"}
    headers_b = {"Authorization": f"Bearer {user_b_token}"}

    filename = "ballism.txt"
    content_v1 = b"Content Version 1: Original text." # Size 33
    content_v2 = b"Content Version 2: Modified text with EXTRA data." # Size > 33

    # 2. User A Uploads v1
    print("[Step 1] User A uploads v1")
    resp = client.post(
        "/ingest", 
        files={"file": (filename, content_v1, "text/plain")},
        headers=headers_a
    )
    assert resp.status_code == 200
    file_id_a = resp.json()["file_id"]
    print(f"User A File ID: {file_id_a}")

    # 3. User B Uploads v1 (Should link)
    print("\n[Step 2] User B uploads v1")
    resp = client.post(
        "/ingest", 
        files={"file": (filename, content_v1, "text/plain")},
        headers=headers_b
    )
    assert resp.status_code == 200
    file_id_b = resp.json()["file_id"]
    print(f"User B File ID: {file_id_b}")

    # 4. User B Replaces File (Delete + Upload v2)
    print("\n[Step 3] User B replacing file...")
    
    # Delete match
    files_b = client.get("/files", headers=headers_b).json()
    target_file = next(f for f in files_b if f["filename"] == filename)
    
    del_resp = client.delete(f"/files/{target_file['id']}", headers=headers_b)
    assert del_resp.status_code == 200
    
    # Upload v2
    resp = client.post(
        "/ingest", 
        files={"file": (filename, content_v2, "text/plain")},
        headers=headers_b
    )
    assert resp.status_code == 200
    file_id_b_v2 = resp.json()["file_id"]
    print(f"User B New File ID: {file_id_b_v2}")

    # 5. Verify User A
    print("\n[Step 4] Checking User A status...")
    files_a = client.get("/files", headers=headers_a).json()
    user_a_file = next(f for f in files_a if f["filename"] == filename)
    
    print(f"User A sees File ID: {user_a_file['id']}")
    print(f"User A sees Size: {user_a_file['size_bytes']}")
    
    # Check assertions
    if user_a_file['size_bytes'] == len(content_v2):
        print("FAIL: User A sees v2 size!")
        pytest.fail("Data Leak Detected: User A sees modified content size.")
    elif user_a_file['size_bytes'] == len(content_v1):
        print("PASS: User A sees v1 size.")
    else:
        print(f"WARN: User A sees unknown size {user_a_file['size_bytes']}")
        
    # Verify Content Hash Logic via DB directly (optional, but API response `size_bytes` proxies it)
    assert user_a_file['id'] == file_id_a, "User A File ID changed!?"
    assert user_a_file['size_bytes'] == len(content_v1), "User A content size changed!"

    print("--- Test Passed: No Leak ---")

if __name__ == "__main__":
    # Manually run the test function if executed as script
    try:
        test_data_leak_scenario()
    except Exception as e:
        print(f"TEST FAILED: {e}")
        # import traceback
        # traceback.print_exc()
