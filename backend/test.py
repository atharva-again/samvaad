import sys
import os
import time
# Defer heavy imports until needed

# Add the project root to sys.path to ensure backend module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_document_path(filename):
    """
    Resolve document path by adding the base documents directory.
    
    """
    # Dynamically find the samvaad directory (parent of backend)
    samvaad_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_path = os.path.join(samvaad_dir, "data", "documents")
    
    # If filename already contains the full path, return as-is
    if filename.startswith(base_path):
        return filename
    
    # If filename is already an absolute path outside our documents directory, return as-is
    if os.path.isabs(filename):
        return filename
    
    # Otherwise, prepend the base path
    return os.path.join(base_path, filename)


def print_help():
    """
    Display help information for available commands.
    """
    print("\nAvailable commands:")
    print("  /query <text> or q <text>    - Query the knowledge base with natural language")
    print("  /voice or v                 - Query the knowledge base with voice (ASR)")
    print("  /ingest <file> or i <file>  - Process and ingest a file into the knowledge base")
    print("  /remove <file> or r <file>  - Remove a file and its embeddings from the database")
    print("  /help or h                  - Show this help message")
    print("  /exit or e                  - Exit the CLI")
    print("\nSupported file formats:")
    print("  Documents: PDF, DOCX, XLSX, PPTX, HTML, XHTML, CSV, TXT, MD")
    print("  Images: PNG, JPEG, TIFF, BMP, WEBP")
    print("  Audio: WAV, MP3")
    print("  Other: WebVTT (subtitles)")
    print("\nExamples:")
    print("  q what is the theory of ballism")
    print("  v")
    print("  i sample.pdf")
    print("  i documents/report.docx")
    print("  i data/spreadsheet.xlsx")
    print("  i images/diagram.png")
    print("  r sample.pdf")
    print("\nNote: File paths are automatically resolved to the data/documents/ directory.")
    print("You can provide just the filename or relative path within the documents folder.")


def load_query_dependencies():
    """Lazy load query-related dependencies."""
    from backend.pipeline.retrieval.query import rag_query_pipeline
    return rag_query_pipeline


def load_ingestion_dependencies():
    """Lazy load ingestion-related dependencies."""
    
    from backend.pipeline.ingest_pipeline import ingest_file_pipeline
    return ingest_file_pipeline


def load_deletion_dependencies():
    """Lazy load deletion-related dependencies."""

    from backend.pipeline.deletion.deletion import delete_file_and_embeddings
    return delete_file_and_embeddings
    


def load_voice_dependencies():
    """Lazy load voice query dependencies."""
    from backend.pipeline.retrieval.query_voice import voice_query_cli
    return voice_query_cli


def handle_query_interactive(query_text, top_k=3, model="gemini-2.5-flash"):
    """
    Handle an interactive query: process a natural language query using the RAG pipeline.
    """
    print("🔄 Loading query dependencies...")
    rag_query_pipeline = load_query_dependencies()

    print(f"🔍 Processing query: '{query_text}'")
    print("=" * 60)

    # Run the complete RAG pipeline
    start_time = time.perf_counter()
    result = rag_query_pipeline(query_text, top_k=top_k, model=model)
    total_time = time.perf_counter() - start_time
    print(f"⏱️  Total query time: {total_time:.4f} seconds")

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
    delete_file_and_embeddings = load_deletion_dependencies()

    # Resolve the document path
    resolved_path = resolve_document_path(file_path)
    print(f"Resolved path: {resolved_path}")

    print(f"Removing file and its embeddings for: {resolved_path}")
    start_time = time.perf_counter()
    orphaned_chunks = delete_file_and_embeddings(resolved_path)
    delete_time = time.perf_counter() - start_time
    print(f"⏱️  Deletion time: {delete_time:.4f} seconds")
    print(f"Deleted file metadata. Orphaned chunk IDs deleted from ChromaDB: {orphaned_chunks}")


def process_file_interactive(file_path):
    """
    Process a file: parse, chunk, embed, and store in the database in interactive mode.
    """
    print("🔄 Loading ingestion dependencies...")
    ingest_file_pipeline = load_ingestion_dependencies()

    # Resolve the document path
    resolved_path = resolve_document_path(file_path)
    print(f"Resolved path: {resolved_path}")

    # Validate file existence
    if not os.path.isfile(resolved_path):
        print(f"File not found: {resolved_path}")
        return

    # Read file contents
    with open(resolved_path, "rb") as f:
        contents = f.read()

    # Determine content type
    ext = os.path.splitext(resolved_path)[1].lower()
    content_type = "application/pdf" if ext == ".pdf" else "text/plain"

    print("Processing file...")
    start_time = time.perf_counter()
    result = ingest_file_pipeline(resolved_path, content_type, contents)
    total_time = time.perf_counter() - start_time
    print(f"⏱️  Total processing time: {total_time:.4f} seconds")

    if result['error']:
        print(f"Error: {result['error']}")
        return

    print(f"Chunked into {result['num_chunks']} chunks.")
    print("First 3 chunks:")
    for i, chunk in enumerate(result['chunk_preview']):
        print(f"Chunk {i+1}:\n{chunk}\n{'-'*40}")

    if result['new_chunks_embedded'] == 0:
        print("File already processed - all chunks exist in database.")
    else:
        print(f"Embedded {result['new_chunks_embedded']} new chunks.")
    print("File processed successfully.")


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

            elif command in ['/voice', 'v']:
                print("🎤 Starting voice query...")
                voice_query_cli = load_voice_dependencies()
                voice_query_cli()

            elif command in ['/ingest', 'i']:
                if len(parts) != 2:
                    print("Usage: /ingest <file_path>")
                    continue
                file_path = parts[1]
                resolved_path = resolve_document_path(file_path)
                print(f"📁 Using document path: {resolved_path}")
                process_file_interactive(file_path)

            elif command in ['/remove', 'r']:
                if len(parts) != 2:
                    print("Usage: /remove <file_path>")
                    continue
                file_path = parts[1]
                resolved_path = resolve_document_path(file_path)
                print(f"📁 Using document path: {resolved_path}")
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


def test_path_resolution():
    """
    Test the path resolution function with various inputs.
    """
    print("🧪 Testing path resolution function...")
    
    test_cases = [
        ("sample.pdf", "E:/Github/samvaad/data/documents/sample.pdf"),
        ("folder/sample.pdf", "E:/Github/samvaad/data/documents/folder/sample.pdf"),
        ("sub/folder/file.docx", "E:/Github/samvaad/data/documents/sub/folder/file.docx"),
        ("E:/Github/samvaad/data/documents/sample.pdf", "E:/Github/samvaad/data/documents/sample.pdf"),
        ("C:/other/path/file.pdf", "C:/other/path/file.pdf"),
    ]
    
    for input_path, expected in test_cases:
        result = resolve_document_path(input_path)
        status = "✅" if result == expected else "❌"
        print(f"{status} {input_path} -> {result}")
        if result != expected:
            print(f"   Expected: {expected}")
    
    print("Path resolution test completed.")


def main():
    """
    Main entry point of the script.
    """
    # Check if test mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--test-paths":
        test_path_resolution()
        return
    
    interactive_cli()


if __name__ == "__main__":
    main()
