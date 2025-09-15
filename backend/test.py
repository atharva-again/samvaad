import sys
import os
# Defer heavy imports until needed


def print_help():
    """
    Display help information for available commands.
    """
    print("\nAvailable commands:")
    print("  /query <text> or q <text>    - Query the knowledge base with natural language")
    print("  /ingest <file> or i <file>  - Process and ingest a file into the knowledge base")
    print("  /remove <file> or r <file>  - Remove a file and its embeddings from the database")
    print("  /help or h                  - Show this help message")
    print("  /exit or e                  - Exit the CLI")
    print("\nExamples:")
    print("  q what is the theory of ballism")
    print("  i data/documents/sample.pdf")
    print("  r data/documents/sample.pdf")


def load_query_dependencies():
    """Lazy load query-related dependencies."""
    global rag_query_pipeline
    if 'rag_query_pipeline' not in globals():
        from pipeline.query import rag_query_pipeline
    return rag_query_pipeline


def load_ingestion_dependencies():
    """Lazy load ingestion-related dependencies."""
    global parse_file, chunk_text, find_new_chunks, update_chunk_file_db
    global embed_chunks_with_dedup, add_embeddings
    global preprocess_file, generate_file_id, generate_chunk_id
    global add_file
    if 'parse_file' not in globals():
        from pipeline.ingestion import parse_file, chunk_text, find_new_chunks, update_chunk_file_db
        from pipeline.embedding import embed_chunks_with_dedup
        from pipeline.vectorstore import add_embeddings
        from pipeline.preprocessing import preprocess_file
        from utils.hashing import generate_file_id, generate_chunk_id
        from utils.filehash_db import add_file


def load_deletion_dependencies():
    """Lazy load deletion-related dependencies."""
    global delete_file_and_embeddings
    if 'delete_file_and_embeddings' not in globals():
        from pipeline.deletion import delete_file_and_embeddings


def handle_query_interactive(query_text, top_k=3, model="gemini-2.5-flash"):
    """
    Handle an interactive query: process a natural language query using the RAG pipeline.
    """
    print("🔄 Loading query dependencies...")
    rag_query_pipeline = load_query_dependencies()

    print(f"🔍 Processing query: '{query_text}'")
    print("=" * 60)

    # Run the complete RAG pipeline
    result = rag_query_pipeline(query_text, top_k=top_k, model=model)

    # Display results
    print(f"\n📝 QUERY: {result['query']}")
    print(f"\n🤖 ANSWER: {result['answer']}")

    if result['success'] and result['sources']:
        print(f"\n📚 SOURCES ({result['retrieval_count']} chunks retrieved):")
        for i, source in enumerate(result['sources'], 1):
            print(f"\n{i}. {source['filename']} (Similarity: {1 - source['distance']:.3f})")
            print(f"   Preview: {source['content_preview']}")

    if not result['success']:
        print(f"\n⚠️  Query failed or returned limited results.")

    # Optionally show the full RAG prompt for debugging
    if os.getenv("DEBUG_RAG") == "1":
        print(f"\n🔧 DEBUG - Full RAG Prompt:")
        print("-" * 40)
        print(result['rag_prompt'])


def remove_file_interactive(file_path):
    """
    Remove a file and its embeddings from the database and ChromaDB in interactive mode.
    """
    print("🔄 Loading deletion dependencies...")
    load_deletion_dependencies()

    print(f"Removing file and its embeddings for: {file_path}")
    orphaned_chunks = delete_file_and_embeddings(file_path)
    print(f"Deleted file metadata. Orphaned chunk IDs deleted from ChromaDB: {orphaned_chunks}")


def process_file_interactive(file_path):
    """
    Process a file: parse, chunk, embed, and store in the database in interactive mode.
    """
    print("🔄 Loading ingestion dependencies...")
    load_ingestion_dependencies()

    # Validate file existence
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    # Read file contents
    with open(file_path, "rb") as f:
        contents = f.read()
    file_id = generate_file_id(contents)

    # Determine content type
    ext = os.path.splitext(file_path)[1].lower()
    content_type = "application/pdf" if ext == ".pdf" else "text/plain"

    # Preprocessing: check for duplicates
    if preprocess_file(contents, file_path):
        print("This file has already been processed (file_id found in DB). Skipping.")
        return

    # Parse the file
    text, error = parse_file(file_path, content_type, contents)
    if error:
        print(f"Parse error: {error}")
        return

    # Chunk the text
    chunks = chunk_text(text)
    print(f"Chunked into {len(chunks)} chunks.\nFirst 3 chunks:\n")
    for i, chunk in enumerate(chunks[:3]):
        print(f"Chunk {i+1}:\n{chunk}\n{'-'*40}")

    # Find new chunks after deduplication
    new_chunks = find_new_chunks(chunks, file_id)
    print(f"Found {len(new_chunks)} new chunks after deduplication.")

    # Extract chunk texts for embedding
    chunks_to_embed = [chunk for chunk, chunk_id in new_chunks]

    # Embed chunks with deduplication
    print("Embedding (with ChromaDB deduplication)...")
    embeddings, embed_indices = embed_chunks_with_dedup(chunks_to_embed, filename=file_path)

    if not embeddings:
        print("No new chunks to embed. Exiting.")
        return

    print(f"Got {len(embeddings)} new embeddings.\nSample embedding (first 5 dims):\n{embeddings[0][:5]}")

    # Store embeddings in ChromaDB
    print("\nStoring embeddings and chunks in ChromaDB...")
    new_chunks_to_store = [chunks_to_embed[i] for i in embed_indices]
    new_metadatas = [{"filename": file_path, "chunk_id": i, "file_id": file_id} for i in embed_indices]
    add_embeddings(new_chunks_to_store, embeddings, new_metadatas, filename=file_path)

    # Update file metadata
    print("Updating file_metadata DB...")
    add_file(file_id, file_path)
    print("File metadata updated.")

    # Update chunk-file mapping for all chunks
    print("\nUpdating chunk-file mapping DB...")
    update_chunk_file_db(chunks, file_id)  # Note: update_chunk_file_db expects chunks, not IDs
    print("Chunk-file mapping DB updated.")


def interactive_cli():
    """
    Run the interactive CLI loop.
    """
    print("Welcome to Samvaad CLI - Interactive Knowledge Base Assistant")
    print("Type /help or h for available commands.")
    print("=" * 60)

    while True:
        try:
            user_input = input("samvaad> ").strip()
            if not user_input:
                continue

            parts = user_input.split()
            command = parts[0].lower()

            if command in ['/query', 'q']:
                if len(parts) < 2:
                    print("Usage: /query <text>")
                    continue
                query_text = ' '.join(parts[1:])
                handle_query_interactive(query_text)

            elif command in ['/ingest', 'i']:
                if len(parts) != 2:
                    print("Usage: /ingest <file_path>")
                    continue
                file_path = parts[1]
                process_file_interactive(file_path)

            elif command in ['/remove', 'r']:
                if len(parts) != 2:
                    print("Usage: /remove <file_path>")
                    continue
                file_path = parts[1]
                remove_file_interactive(file_path)

            elif command in ['/help', 'h']:
                print_help()

            elif command in ['/exit', 'e']:
                print("Goodbye!")
                break

            else:
                print("Unknown command. Type /help for available commands.")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")


def main():
    """
    Main entry point of the script.
    """
    interactive_cli()


if __name__ == "__main__":
    main()
