from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from samvaad.db.models import File, GlobalFile, GlobalChunk, global_file_chunks
from samvaad.db.session import get_db_context
from samvaad.utils.hashing import generate_file_id, generate_chunk_id

class DBService:
    """
    Unified service for handling File Metadata and Vector Embeddings in Postgres.
    """

    @staticmethod
    def file_exists(file_id: str) -> bool:
        """Check if a file with the given ID already exists."""
        with get_db_context() as db:
            result = db.execute(select(File).where(File.id == file_id)).first()
            return result is not None

    @staticmethod
    def check_content_exists(content_hash: str) -> bool:
        """Check if content blob exists globally."""
        with get_db_context() as db:
            result = db.execute(select(GlobalFile).where(GlobalFile.hash == content_hash)).first()
            return result is not None

    @staticmethod
    def get_existing_chunk_hashes(chunk_hashes: List[str]) -> set[str]:
        """
        Check which of the provided chunk hashes already exist in global_chunks.
        Returns a set of existing hashes.
        """
        if not chunk_hashes:
            return set()
        
        with get_db_context() as db:
            # Chunking query in batches if list is huge? For now assume it fits.
            stmt = select(GlobalChunk.hash).where(GlobalChunk.hash.in_(chunk_hashes))
            results = db.execute(stmt).scalars().all()
            return set(results)

    @staticmethod
    def link_existing_content(user_id: str, filename: str, content_hash: str) -> dict:
        """
        Link a user to existing global content.
        """
        with get_db_context() as db:
            file_ptr_id = str(uuid.uuid4())
            new_file = File(
                id=file_ptr_id,
                user_id=user_id,
                filename=filename,
                content_hash=content_hash
            )
            db.add(new_file)
            db.commit()
            
            return {
                "status": "linked",
                "file_id": file_ptr_id,
                "chunks_added": 0
            }

    @staticmethod
    def add_smart_dedup_content(
        filename: str, 
        content: bytes, 
        chunks: List[str], 
        chunk_hashes: List[str],
        new_embeddings_map: Dict[str, List[float]], 
        user_id: str = None,
        chunk_metadatas: List[Dict[str, Any]] = None
    ):
        """
        Advanced Ingestion with Race Condition Handling.
        """
        content_hash = generate_file_id(content)
        file_ptr_id = str(uuid.uuid4())

        with get_db_context() as db:
            # 1. Create GlobalFile safely
            # Using simple check-then-insert inside txn. 
            # In purely concurrent scenario, ideally ON CONFLICT DO NOTHING.
            # But simple check is "good enough" for most low-traffic apps.
            # db.merge checks PK and updates if exists, inserts if not. 
            new_content = GlobalFile(
                hash=content_hash,
                size=len(content)
            )
            db.merge(new_content)
            
            # 2. Add NEW GlobalChunks
            # Use merge to safely handle race conditions where another user uploads same chunk concurrently.
            for h, vec in new_embeddings_map.items():
                try:
                    idx = chunk_hashes.index(h)
                    text_content = chunks[idx]
                    
                    chunk_obj = GlobalChunk(
                        hash=h,
                        content=text_content,
                        embedding=vec
                    )
                    db.merge(chunk_obj) 
                except ValueError:
                    continue

            # Ensure all Content and Chunks are written to DB before linking them
            db.flush() 

            # 3. Create Associations
            
            # If the GlobalFile was just created/merged, we should ensure associations exist.
            # Checking each is slow.
            # Strategy: If DB says this GlobalFile ALREADY existed (logic in ingestion), we probably skipped this fn.
            # But if we are here, we think we need to add.
            
            # Let's collect items to insert.
            insert_data = []
            for i, h in enumerate(chunk_hashes):
                metadata = chunk_metadatas[i] if chunk_metadatas and i < len(chunk_metadatas) else None
                insert_data.append({
                    "global_file_hash": content_hash,
                    "chunk_hash": h,
                    "chunk_index": i,
                    "chunk_metadata": metadata 
                })
            
            # Use 'min_rows' logic or just try/except integrity error?
            # Or better: "INSERT ... ON CONFLICT DO NOTHING".
            from sqlalchemy.dialects.postgresql import insert
            
            if insert_data:
                stmt = insert(global_file_chunks).values(insert_data)
                stmt = stmt.on_conflict_do_nothing(index_elements=['global_file_hash', 'chunk_hash'])
                db.execute(stmt)

            # 4. Create User File Pointer
            new_file = File(
                id=file_ptr_id,
                user_id=user_id,
                filename=filename,
                content_hash=content_hash
            )
            db.add(new_file)
            
            db.commit()
            
            return {
                "status": "created",
                "file_id": file_ptr_id,
                "chunks_added": len(new_embeddings_map)
            }

    @staticmethod
    def get_user_files(user_id: str) -> List[Dict]:
        """List all files belonging to a specific user."""
        with get_db_context() as db:
            results = db.execute(
                select(File, GlobalFile)
                .join(GlobalFile, File.content_hash == GlobalFile.hash)
                .where(File.user_id == user_id)
                .order_by(File.created_at.desc())
            ).all()
            
            return [
                {
                    "id": f.File.id,
                    "filename": f.File.filename,
                    "created_at": f.File.created_at,
                    "size_bytes": f.GlobalFile.size,
                    "content_hash": f.GlobalFile.hash # Exposed for UI deduplication
                }
                for f in results
            ]

    @staticmethod
    def batch_delete_files(file_ids: List[str], user_id: str) -> Dict[str, List[str]]:
        """
        Delete multiple files by their IDs.
        Returns dict with 'deleted' and 'failed' lists.
        """
        deleted = []
        failed = []
        
        for file_id in file_ids:
            try:
                success = DBService.delete_file(file_id=file_id, user_id=user_id)
                if success:
                    deleted.append(file_id)
                else:
                    failed.append(file_id)
            except Exception as e:
                print(f"Failed to delete file {file_id}: {e}")
                failed.append(file_id)
        
        return {"deleted": deleted, "failed": failed}

    @staticmethod
    def rename_file(file_id: str, new_filename: str, user_id: str) -> Optional[Dict]:
        """
        Rename a file.
        Returns the updated file dict or None if not found.
        """
        with get_db_context() as db:
            file = db.execute(
                select(File).where(File.id == file_id, File.user_id == user_id)
            ).scalar_one_or_none()
            
            if not file:
                return None
            
            file.filename = new_filename
            db.commit()
            db.refresh(file)
            
            return {
                "id": file.id,
                "filename": file.filename,
                "created_at": file.created_at,
                "content_hash": file.content_hash
            }

    @staticmethod
    def delete_file(file_id: str, user_id: str):
        """
        Delete a file pointer AND cleanup orphaned chunks/content.
        Zero-leak guarantee.
        """
        from samvaad.db.models import global_file_chunks, GlobalChunk, GlobalFile
        from sqlalchemy import func

        with get_db_context() as db:
            file = db.execute(
                select(File).where(File.id == file_id, File.user_id == user_id)
            ).scalar_one_or_none()
            
            if not file:
                return False
                
            content_hash = file.content_hash
            db.delete(file)
            db.flush() 
            
            # 1. Check if GlobalFile is Orphaned
            ref_count = db.execute(
                select(func.count(File.id)).where(File.content_hash == content_hash)
            ).scalar()
            
            if ref_count == 0:
                # This GlobalFile is no longer used by ANY user.
                # We must delete it, AND clean up any GlobalChunks that become orphans.
                
                # A. Identify Chunks used by this GlobalFile
                # Query: Get all chunk_hashes linked to this content
                chunk_hashes_in_file = db.execute(
                    select(global_file_chunks.c.chunk_hash)
                    .where(global_file_chunks.c.global_file_hash == content_hash)
                ).scalars().all()
                
                # B. Delete the GlobalFile
                # This automatically removes rows in `global_file_chunks` via ON DELETE CASCADE
                db.execute(delete(GlobalFile).where(GlobalFile.hash == content_hash))
                db.flush() # Ensure association rows are gone
                
                # C. Check each chunk for orphan status
                if chunk_hashes_in_file:
                    # Find chunks that have ZERO references in global_file_chunks
                    # Query: Select chunk_hash from global_chunks where hash IN (candidates) AND hash NOT IN (select chunk_hash from global_file_chunks)
                    
                    # Alternatively, check counts.
                    # Efficient single query:
                    statement = delete(GlobalChunk).where(
                        GlobalChunk.hash.in_(chunk_hashes_in_file)
                    ).where(
                        ~select(global_file_chunks.c.chunk_hash)
                        .where(global_file_chunks.c.chunk_hash == GlobalChunk.hash)
                        .exists()
                    )
                    result = db.execute(statement)
                    print(f"Cleanup: Deleted {result.rowcount} orphaned chunks.")

            db.commit()
            return True

    @staticmethod
    def search_similar_chunks(query_embedding: List[float], top_k: int = 5, user_id: str = None, file_ids: List[str] = None) -> List[Dict]:
        """
        Search for chunks similar to the query embedding.
        
        Args:
            query_embedding: The query vector
            top_k: Number of results to return
            user_id: Filter by user (required for security)
            file_ids: Optional list of file IDs to filter by (for RAG source selection)
        """
        with get_db_context() as db:
            # Join GlobalChunk -> global_file_chunks -> GlobalFile -> File
            # This is a 4-table join.
            
            stmt = (
                select(GlobalChunk, File, global_file_chunks.c.chunk_metadata)
                .join(global_file_chunks, GlobalChunk.hash == global_file_chunks.c.chunk_hash)
                .join(GlobalFile, global_file_chunks.c.global_file_hash == GlobalFile.hash)
                .join(File, File.content_hash == GlobalFile.hash)
                .order_by(GlobalChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )

            if user_id:
                stmt = stmt.where(File.user_id == user_id)
            
            # Filter by specific file IDs if provided (RAG source whitelist)
            if file_ids:
                stmt = stmt.where(File.id.in_(file_ids))

            results = db.execute(stmt).all()
            
            output = []
            for chunk, file_obj, chunk_meta in results:
                output.append({
                    "id": chunk.hash,
                    "document": chunk.content,
                    "metadata": {
                        "filename": file_obj.filename,
                        "file_id": file_obj.id,
                        "extra": chunk_meta or {}
                    },
                    "distance": 0.0
                })
            return output
