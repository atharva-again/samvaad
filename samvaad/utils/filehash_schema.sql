-- SQLite schema for file and chunk metadata management

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS file_metadata (
    file_id TEXT PRIMARY KEY, -- SHA256 hash of file contents
    filename TEXT NOT NULL,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunk_file_map (
    chunk_id TEXT NOT NULL, -- SHA256 hash of chunk content
    file_id TEXT NOT NULL,  -- references file_metadata(file_id)
    PRIMARY KEY (chunk_id, file_id),
    FOREIGN KEY (file_id) REFERENCES file_metadata(file_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_chunk_id ON chunk_file_map(chunk_id);
CREATE INDEX IF NOT EXISTS idx_file_id ON chunk_file_map(file_id);
