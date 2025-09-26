import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), 'filehashes.sqlite3')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Read schema from file
    schema_path = os.path.join(os.path.dirname(__file__), 'filehash_schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    c.executescript(schema_sql)
    conn.commit()
    conn.close()

def file_exists(file_id: str) -> bool:
    """Check if a file hash exists in file_metadata."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM file_metadata WHERE file_id = ?', (file_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def add_file(file_id: str, filename: str):
    """Insert a new file into file_metadata if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute('BEGIN')
        c.execute('INSERT INTO file_metadata (file_id, filename, upload_time) VALUES (?, ?, ?)',
                  (file_id, filename, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        pass  # Already exists
    finally:
        conn.close()

def chunk_exists(chunk_id: str, file_id: str = None) -> bool:
    """
    If file_id is provided, check if (chunk_id, file_id) mapping exists (per-file check).
    If file_id is None, check if chunk_id exists globally in any file (global check).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if file_id is not None:
        c.execute("SELECT 1 FROM chunk_file_map WHERE chunk_id=? AND file_id=?", (chunk_id, file_id))
    else:
        c.execute("SELECT 1 FROM chunk_file_map WHERE chunk_id=?", (chunk_id,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def add_chunk(chunk_id: str, file_id: str):
    """Insert a (chunk_id, file_id) pair into chunk_file_map if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute('BEGIN')
        c.execute('INSERT INTO chunk_file_map (chunk_id, file_id) VALUES (?, ?)', (chunk_id, file_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        pass  # Already exists
    finally:
        conn.close()

def delete_file_and_cleanup(file_id: str) -> list:
    """
    Delete a file and clean up orphaned chunks.
    Returns a list of chunk_ids that are no longer referenced by any file (to be deleted from the vector DB).
    """
    conn = sqlite3.connect(DB_PATH)
    orphaned_chunks = []
    
    try:
        conn.execute('BEGIN')
        
        # Get all chunk_ids for this file
        c = conn.cursor()
        c.execute('SELECT chunk_id FROM chunk_file_map WHERE file_id = ?', (file_id,))
        chunk_ids = [row[0] for row in c.fetchall()]
        
        # For each chunk_id, check if it's referenced by any other file
        for chunk_id in chunk_ids:
            c.execute('''
                SELECT 1 FROM chunk_file_map 
                WHERE chunk_id = ? AND file_id != ?
                LIMIT 1
            ''', (chunk_id, file_id))
            
            # If no other references, add to orphaned list
            if c.fetchone() is None:
                orphaned_chunks.append(chunk_id)
        
        # Remove all (chunk_id, file_id) pairs for this file
        c.execute('DELETE FROM chunk_file_map WHERE file_id = ?', (file_id,))
        
        # Remove the file entry
        c.execute('DELETE FROM file_metadata WHERE file_id = ?', (file_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error during file deletion: {e}")
        orphaned_chunks = []
    finally:
        conn.close()
    
    return orphaned_chunks
