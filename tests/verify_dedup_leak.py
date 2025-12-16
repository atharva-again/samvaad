
import os
import sys
import uuid
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from samvaad.db.service import DBService
from samvaad.pipeline.ingestion.ingestion import ingest_file_pipeline
from samvaad.db.session import get_db_context
from samvaad.db.models import File, GlobalFile

def verify_leak():
    user_a = f"user_a_{uuid.uuid4()}"
    user_b = f"user_b_{uuid.uuid4()}"
    filename = "leak_test_file.txt"
    
    content_v1 = b"This is the original content. It contains secret data for User A."
    content_v2 = b"This is the MODIFIED content. User B changed it. User A should NOT see this."

    print(f"--- Starting Leak Test ---")
    print(f"User A: {user_a}")
    print(f"User B: {user_b}")

    # 0. Create Users
    from samvaad.db.models import User
    with get_db_context() as db:
        u_a = User(id=user_a, email="a@test.com")
        u_b = User(id=user_b, email="b@test.com")
        db.add(u_a)
        db.add(u_b)
        db.commit()

    # 1. User A uploads v1
    print("\n[Step 1] User A uploads v1")
    ingest_file_pipeline(filename, "text/plain", content_v1, user_id=user_a)
    
    # 2. User B uploads v1 (Deduplication)
    print("\n[Step 2] User B uploads v1")
    ingest_file_pipeline(filename, "text/plain", content_v1, user_id=user_b)

    # Verify both point to same hash
    with get_db_context() as db:
        files_a = DBService.get_user_files(user_a)
        files_b = DBService.get_user_files(user_b)
        
        file_a = db.query(File).filter(File.id == files_a[0]['id']).first()
        file_b = db.query(File).filter(File.id == files_b[0]['id']).first()
        
        print(f"User A File Hash: {file_a.content_hash}")
        print(f"User B File Hash: {file_b.content_hash}")
        
        if file_a.content_hash != file_b.content_hash:
            print("ERROR: Deduplication failed. Hashes should be identical.")
            return

    # 3. User B 'Replaces' file.
    # Frontend Logic: Delete old file -> Upload new file
    print("\n[Step 3] User B replaces file (mocks frontend logic)")
    
    # User B deletes their v1 file
    DBService.delete_file(files_b[0]['id'], user_b)
    
    # User B uploads v2
    ingest_file_pipeline(filename, "text/plain", content_v2, user_id=user_b)

    # 4. Check User A's file
    print("\n[Step 4] Checking User A's status")
    with get_db_context() as db:
        # Refresh User A's file list
        files_a_after = DBService.get_user_files(user_a)
        file_a_obj = db.query(File).filter(File.id == files_a_after[0]['id']).first()
        
        # Determine current hash
        hash_a = file_a_obj.content_hash
        
        # Get content size/metadata
        gf = db.query(GlobalFile).filter(GlobalFile.hash == hash_a).first()
        
        print(f"User A File Hash: {hash_a}")
        print(f"GlobalFile Size: {gf.size}")
        
        if gf.size == len(content_v2):
            print("CRITICAL FAILURE: User A's file size matches v2 content!")
            print(f"User A sees: {content_v2} (Based on size match)")
        elif gf.size == len(content_v1):
            print("SUCCESS: User A's file size matches v1 content.")
        else:
            print(f"UNKNOWN STATE: Size {gf.size} matches neither.")

        # Let's verify chunks for User A
        chunks = DBService.search_similar_chunks([0.0]*1024, top_k=5, user_id=user_a)
        # Mock embedding search usually returns something if we pass 0 vector? 
        # Actually search_similar_chunks depends on embeddings.
        # But we can check global_file_chunks directly.
        
        from samvaad.db.models import global_file_chunks, GlobalChunk
        from sqlalchemy import select
        stmt = select(GlobalChunk.content).join(global_file_chunks, GlobalChunk.hash == global_file_chunks.c.chunk_hash).where(global_file_chunks.c.global_file_hash == hash_a)
        chunk_contents = db.execute(stmt).scalars().all()
        
        print(f"User A Chunks: {chunk_contents}")
        
        leak_found = any("MODIFIED" in c for c in chunk_contents)
        if leak_found:
             print("CRITICAL FAILURE: Modified content found in User A's chunks!")
        else:
             print("SUCCESS: No modified content in User A's chunks.")

if __name__ == "__main__":
    verify_leak()
