# Copilot Instructions for Samvaad RAG Project

## Architecture Overview
Samvaad is a Retrieval-Augmented Generation (RAG) chatbot with a modular backend pipeline. Key components:
- **Ingestion**: Parse PDFs/text, chunk text (200 tokens), embed with `BAAI/bge-m3`, store in ChromaDB with deduplication.
- **Query**: Hybrid retrieval (BM25 + embeddings + cross-encoder reranking), generate answers via Gemini/OpenAI.
- **Storage**: ChromaDB for vectors/chunks, SQLite (`utils/filehash_db.py`) for file/chunk metadata and deduplication.
- **API**: FastAPI in `backend/main.py` for ingestion; CLI in `backend/test.py` for interactive use.

Data flow: Documents → `ingestion.py` → `embedding.py` → `vectorstore.py` (ChromaDB); Queries → `query.py` (retrieve from ChromaDB, generate via API).

## Critical Workflows
- **CLI Testing**: Run `python backend/test.py` for interactive commands (`q` for query, `i` for ingest, `r` for remove). Lazy-loads dependencies to avoid slow startup.
- **API Server**: `uvicorn backend.main:app --reload` for FastAPI endpoints (`/health`, `/ingest`).
- **Debugging**: Set `DEBUG_RAG=1` to show full prompts; use `print` for API key checks in `query.py`.
- **Environment**: Load `.env.local` first, then `.env`; require `GEMINI_API_KEY` or `OPENAI_API_KEY`.

## Project Conventions
- **Deduplication**: Use SHA256 hashes (`utils/hashing.py`) for files/chunks; check SQLite before embedding.
- **Models**: Global instances in `query.py` (`_embedding_model`, `_cross_encoder`) to avoid reloading.
- **Error Handling**: Return dicts with `success` bool; raise `ValueError` for missing env vars.
- **Chunking**: Recursive splitter with separators (`\n\n`, `\n`, `.`, etc.) up to 200 tokens.
- **Retrieval**: Fuse BM25 and embeddings via Reciprocal Rank Fusion (k=60), rerank top 10 with cross-encoder.
- **Metadata**: Store `filename`, `file_id` in ChromaDB for filtering; use SQLite for relational queries.

## Integrations & Dependencies
- **ChromaDB**: Persistent client (`chroma_db/`); add embeddings with metadata, query with `where` filters.
- **LLMs**: Gemini (`google-genai`) for generation; fallback to OpenAI if needed.
- **Parsing**: `pymupdf` for PDFs, plain text for .txt.
- **Embeddings**: `sentence-transformers` with prefix `"Represent this sentence for retrieval: "`.
- **Cross-Encoder**: `cross-encoder/ms-marco-MiniLM-L-6-v2` for reranking.

Reference: `backend/pipeline/query.py` for RAG logic, `backend/test.py` for CLI patterns, `utils/filehash_schema.sql` for DB structure.</content>
<parameter name="filePath">e:\Github\samvaad\.github\copilot-instructions.md