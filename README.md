# Samvaad: Facilitating Dialogue-Based Learning 

![Python](https://img.shields.io/badge/python-3.11-blue)

### Note
- Currently, only CLI version is supported. Frontend/UI is under development.
- Voice queries are now supported in multiple languages (Hindi, English, Hinglish, etc.). Voice chat feature is still under development.

Please see the [issues](https://github.com/HapoSeiz/samvaad/issues) for ideas or to report bugs.

### Recent Updates
- **Voice Queries:** Ask questions or query documents in your preferred language (Hindi, English, etc.)
- **GPU Acceleration:** Automatic GPU detection for faster processing
- **Performance Monitoring:** Timing instrumentation for all pipeline steps
- **OS Compatibility:** Cross-platform path resolution
- **Separate Requirements:** CPU and GPU-specific dependency files
- **Interactive CLI:** Improved user interface for all operations

The modular design makes it easy to add new features. The backend/ and frontend/ folders are separate, so you can build the UI and connect to the backend API.icense-MIT-green)

---

## About The Project

**Samvaad** (Sanskrit for "dialogue") is an open-source software that combines Retrieval-Augmented Generation (RAG) capabilities with end-to-end voice capabilities. Users can add their documents, Samvaad will index and store them, and then users can have a text or voice conversation with those documents that delivers accurate, context-aware answers. Built with a modular backend and a modern frontend (in the works), Samvaad makes it easy to learn new topics, get ahead of confusions, and stay learning - all while feeling like a friend.

---

## Getting Started

### Prerequisites
- **Python 3.11**: This project is optimized for Python 3.11. Some dependencies (like PyAudio for voice features) have pre-built wheels only for this version. Ensure you're using 3.11:
  ```sh
  python --version  # Should show Python 3.11.x
  ```

Follow these steps to set up and run Samvaad locally:

### 1. Clone the Repository

```sh
git clone https://github.com/HapoSeiz/samvaad.git
cd samvaad
```

### 2. Set Up a Virtual Environment

**Windows:**
```sh
python -m venv venv
venv\Scripts\activate
```
*If you have multiple Python versions:* Use `py -3.11 -m venv venv` (Python Launcher) or specify the path (e.g., `C:\Python311\python.exe -m venv venv`).

**macOS/Linux:**
```sh
python3.11 -m venv venv  # Use python3.11 if available, otherwise python3
source venv/bin/activate
```
*If you have multiple Python versions:*
- System-wide: `python3.11 -m venv venv`
- pyenv: `pyenv local 3.11` then `python -m venv venv`
- conda: `conda create -n samvaad python=3.11` then `conda activate samvaad`

### 3. Install Dependencies

**System Dependencies (for voice features):**
PyAudio requires PortAudio. If you encounter issues with voice queries:

**Windows:** No additional installation needed (included in PyAudio wheels).

**macOS:**
```sh
brew install portaudio
```

**Linux (Ubuntu/Debian):**
```sh
sudo apt-get install portaudio19-dev
```

**Linux (Fedora/CentOS):**
```sh
sudo dnf install portaudio-devel  # or yum install portaudio-devel
```

Choose the appropriate requirements file based on your hardware:

**For CPU-only systems:**
```sh
pip install -r requirements-cpu.txt
```

**For GPU-accelerated systems (requires CUDA-compatible GPU):**
```sh
pip install -r requirements-gpu.txt
```

### 4. Add Your Documents

Place your documents inside the `data/documents/` folder. Supported file types include:
- **PDF files** (.pdf)
- **Microsoft Office documents** (.docx, .pptx, .xlsx)
- **Text files** (.txt, .md)
- **Web pages** (.html, .htm)
- **Images** (.png, .jpg, .jpeg, .tiff, .bmp) - with OCR support
- **Other formats** supported by Docling (e.g., .rtf, .epub)

These will be used as the chatbot's knowledge base.

### 5. Configure Environment

Create a `.env` file in the root directory and add your API keys:

```sh
# Copy and edit the following into .env
GEMINI_API_KEY=your_gemini_api_key_here
```
You can get your `Gemini_API_Key` [here](https://aistudio.google.com/api-keys).

**Note:** The system works without API keys but will only show retrieved context without AI-generated answers.

### 6. Process Your Documents

Run the interactive CLI to ingest documents:

```sh
python -m backend.test
```

Then use commands like:
- `i document.pdf` to ingest a file
- `q What is the main topic?` to query

### 7. Query Your Knowledge Base

Use the interactive CLI for querying:

```sh
python -m backend.test
```

Inside the CLI:
- `q What are the main findings?` - Basic query


### Voice Queries

Samvaad supports multilingual voice queries, allowing you to ask questions in Hindi, English, Hinglish, or other languages. The system transcribes your speech and responds in the same language/style.

```sh
# Start interactive mode
python -m backend.test

# Inside CLI:
v
# This starts voice recording mode. Speak your question in any supported language.
# The system will transcribe, process, and respond accordingly.
```

**Supported Languages:** Hindi, Hinglish (code-mixed), English, and auto-detection for other languages.


## Usage Examples

### Interactive CLI

Samvaad now uses an interactive command-line interface for all operations:

```sh
python -m backend.test
```

Available commands:
- `i <file>` or `ingest <file>` - Process and ingest a file
- `q <text>` or `query <text>` - Query the knowledge base
- `v` or `voice` - Start voice query mode (supports multiple languages like Hindi, English, Hinglish)
- `r <file>` or `remove <file>` - Remove a file and its embeddings
- `h` or `help` - Show help
- `e` or `exit` - Exit the CLI

### Document Processing

```sh
# Start interactive mode
python -m backend.test

# Inside CLI:
i documents/research_paper.pdf
# Output includes timing: ⏱️ Parsing time: 0.1234 seconds, etc.

# Remove a document
r documents/old_file.pdf
# Output: ⏱️ Deletion time: 0.0567 seconds
```

### Querying Your Knowledge Base

```sh
# Start interactive mode
python -m backend.test

# Inside CLI:
q "What are the main findings?"
# Output includes total query time and sources

q "Explain the methodology" -k 8
# Retrieve more context chunks

q "What are the implications?" -m gemini-2.5-flash
# Use Gemini model for answers
```

### Performance Monitoring

The CLI now shows timing for each step:

```
⏱️ Parsing time: 0.1234 seconds
⏱️ Chunking time: 0.0567 seconds
⏱️ Embedding time: 1.2345 seconds
⏱️ Storage time: 0.0890 seconds
⏱️ Total query time: 2.3456 seconds
⏱️ Deletion time: 0.0123 seconds
```

### GPU Acceleration

If a CUDA-compatible GPU is detected, operations will automatically use GPU acceleration for:
- Document parsing (Docling)
- Text embeddings (SentenceTransformer)
- Cross-encoder reranking
- LLM inference (if supported)

Check GPU usage with `nvidia-smi` during processing.

### Example Output

```
🔍 Processing query: 'What is the theory of Ballism?'
============================================================
⏱️ Total query time: 2.3456 seconds

📝 QUERY: What is the theory of Ballism?

🤖 ANSWER:
The theory of Ballism, formally known as the Principle of Spherical Convergence, posits that all matter and energy in the universe is subject to a fundamental force that compels it to assume a perfect spherical shape over infinitely long periods...

📚 SOURCES (3 chunks retrieved):

1. ballism.txt (Similarity: 0.847)
   Preview: The theory of Ballism, formally known as the Principle of Spherical Convergence...

2. ballism.txt (Similarity: 0.723)
   Preview: Dr. Finch's initial "Finches' Folly" experiment...
```

---

## Project Structure

```
samvaad/
├── backend/          # Python code for the RAG pipeline and API
│   ├── pipeline/     # Core RAG components (ingestion, embedding, query, etc.)
│   ├── utils/        # Utilities (hashing, DB, GPU detection)
│   ├── main.py       # FastAPI server
│   └── test.py       # Interactive CLI for testing and usage
├── frontend/         # React + Next.js user interface (WIP)
├── data/             # Raw documents for the knowledge base
├── tests/            # Unit and integration tests
├── requirements-cpu.txt  # Dependencies for CPU-only usage
├── requirements-gpu.txt  # Dependencies for GPU acceleration
└── README.md         # Project documentation
```

**Directory Overview:**
- **backend/**: Modular RAG pipeline, API, and CLI (Python)
- **frontend/**: Modern UI (React/Next.js)
- **data/**: Folder where you can keep your source documents (PDFs, PPTs, txt, etc.)
- **tests/**: All tests for reliability

## Features

- **Retrieval-Augmented Generation (RAG):** Combines LLMs with your own documents for accurate, context-aware answers.
- **Complete Query Pipeline:** Ask natural language questions and get AI-powered answers with source citations.
- **GPU Acceleration:** Automatic GPU detection and usage for faster embeddings, parsing, and inference (when available).
- **Performance Monitoring:** Built-in timing instrumentation for ingestion, retrieval, and deletion steps.
- **OS-Agnostic Paths:** Cross-platform compatibility (Windows, macOS, Linux) with dynamic path resolution.
- **Modular Backend:** Easily extend or swap components in the RAG pipeline.
- **Modern Frontend (Coming Soon):** React + Next.js interface for a seamless chat experience.
- **Interactive CLI:** Full document processing and querying via an interactive command-line interface.
- **Multiple LLM Support:** Works with OpenAI GPT models and Google Gemini, with graceful fallback.
- **Easy Setup:** Simple installation with separate CPU/GPU configurations.
- **Private & Secure:** Your data stays on your machine.

---
---

## Testing

Samvaad includes comprehensive unit and integration tests to ensure reliability.

### Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_utils.py       # Utils (hashing, DB, GPU)
│   ├── test_preprocessing.py
│   ├── test_ingestion.py
│   ├── test_embedding.py
│   ├── test_vectorstore.py
│   ├── test_query.py
│   └── test_deletion.py
├── integration/            # Integration tests for full pipeline
│   └── test_full_pipeline.py
└── pytest.ini             # Test configuration
```

### Running Tests

**Run all tests:**
```sh
pytest
```

**Run unit tests only:**
```sh
pytest tests/unit/
```

**Run integration tests only:**
```sh
pytest tests/integration/
```

**Run specific test file:**
```sh
pytest tests/unit/test_utils.py -v
```

### Test Coverage

- **Unit Tests:** Test individual functions and classes in isolation
- **Integration Tests:** Test the complete RAG pipeline end-to-end
- **Mocking:** External dependencies (APIs, databases, ML models) are mocked for reliable testing
- **CI/CD Ready:** Tests are designed to run in automated environments

## Continuous Integration

Automated test runs execute through GitHub Actions. The workflow runs CPU tests on all pushes and pull requests to `main`. GPU tests run only on pushes to `main` to avoid the overhead of installing large PyTorch GPU wheels on every PR. Both configurations exercise the full `pytest` suite. No additional secrets are required for the suite to pass because external services are mocked in the tests. You can monitor the latest builds from the **Actions** tab on GitHub.

---

## Contributing

Contributions are welcome! To get started:

1. Fork this repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes and add tests
4. Commit and push (`git commit -am 'Add new feature'`)
5. Open a pull request

Please see the [issues](https://github.com/HapoSeiz/samvaad/issues) page for ideas or to report bugs.

Future Development
The modular design of this project makes it easy to add new features. The backend/ and frontend/ folders are completely separate, so you can build out the user interface and connect it to the backend's API when you're ready.
