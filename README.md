# Samvaad: Facilitating Dialogue-Based Learning 

![Python](https://img.shields.io/badge/python-3.11-blue)

### Note
- The software uses **fully open-source models** for all the stages, except final answer generation, for which it uses Gemini. Document parsing, ingestion, querying, automatic speech recognition (ASR), text to speech (TTTS), all are fully on-premise and optimized to be used even on **low-end devices with no GPU.**
- Voice queries are now fully supported with Kokoro TTS for high-quality speech synthesis in English and Hindi is in preview
- Frontend/UI is under development, currently CLI-only

Please see the [issues](https://github.com/atharva-again/samvaad/issues) for ideas or to report bugs.

### Recent Updates
- **Moving to ONNXRuntime:** I am trying to move the project and models from PyTorch to ONNXRuntime to increase performance on low-end devices even more. You can check the status [here](https://github.com/atharva-again/samvaad/issues/20).
- **Interactive CLI:** Improved user interface that can be called using the `samvaad` command
- **Kokoro TTS:** Neural TTS engine with high-quality speech synthesis
- **Voice Queries:** Ask questions or query documents in your preferred language (Hindi, English, etc.)

---

## About The Project

**Samvaad** (Sanskrit for "dialogue") is an open-source software that combines Retrieval-Augmented Generation (RAG) capabilities with end-to-end voice capabilities. Users can add their documents, Samvaad will index and store them, and then users can have a text or voice conversation with those documents that delivers accurate, context-aware answers. Built with a modular backend and a modern frontend (in the works), Samvaad makes it easy to learn new topics, get ahead of confusions, and stay learning - all while feeling like a friend.

---

## Getting Started

### Prerequisites

**Python 3.11**: This project is optimized for Python 3.11. Some dependencies (like sounddevice for voice features) provide wheels primarily for this version. Ensure you're using 3.11:
  ```sh
  python --version  # Should show Python 3.11.x
  ```

**PortAudio (for voice features)**: If you plan to use voice queries or TTS playback, install PortAudio, which is required by the `sounddevice` library:
  - On Ubuntu/Debian: `sudo apt-get install portaudio19-dev`
  - On macOS: `brew install portaudio`
  - On Windows: PortAudio is usually included with `sounddevice`, but install it manually if needed.
  
  Without PortAudio, voice recording and playback will be skipped with a warning.

Follow these steps to set up and run Samvaad locally:

### 1. Clone the Repository

```sh
git clone https://github.com/atharva-again/samvaad.git
cd samvaad
```

### 2. Set Up a Virtual Environment

**Install uv (if not already installed):**
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**

```sh
# Create a Python 3.11.x virtual environment
uv venv --python=3.11
venv\Scripts\activate
```

**macOS/Linux:**

```sh
# Create a Python 3.11.x virtual environment
uv venv --python=3.11
source .venv/bin/activate
```

*Note: uv creates a `.venv` directory by default (with a dot).*


### 3. Install Samvaad

#### ⚡️ Important: Install the Correct PyTorch and ONNX Runtime Versions

Samvaad and its dependencies require PyTorch (`torch`) and ONNX Runtime (`onnxruntime`), but the versions you need depend on whether you want GPU acceleration or not:

- **For GPU support (NVIDIA CUDA):**
  - Install the GPU-enabled versions (replace `cu121` with your CUDA version if needed):
    ```sh
    uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
    uv pip install onnxruntime-gpu
    ```
  - See the [PyTorch Get Started](https://pytorch.org/get-started/locally/) page for other CUDA versions.

- **For CPU-only (no GPU):**
  - Install the CPU-only versions:
    ```sh
    uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
    uv pip install onnxruntime
    ```

**Why?**
If you do not install these packages first, the dependency resolver may download large GPU versions (with CUDA libraries) even if you only want CPU, or vice versa. Installing them explicitly ensures you get the right versions for your hardware. ONNX Runtime is used for fast embedding inference and cross-encoder reranking.

#### Install all other dependencies

```sh
uv pip install -r requirements.txt
```

#### Install Samvaad in editable mode to enable the CLI command

```sh
uv pip install -e .
```

**You must run both steps for the `samvaad` command to work.**


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
samvaad
```

Then use commands like:
- `/ingest document.pdf` or `/i document.pdf` to ingest a file

### 7. Query Your Knowledge Base

Use the interactive CLI for querying:

```sh
samvaad
```

Inside the CLI:
- Type your question directly, for example: `What are the main findings?` - Basic query
- For voice query, type /voice or /v and the voice mode will get activated. You can follow the screen instructions from there.


## Usage Examples

### Interactive CLI

Samvaad now uses an interactive command-line interface for all operations:

```sh
samvaad
```

Available commands (slash-prefixed):
- `/ingest <file>` or `/i <file>` - Process and ingest a file
- Type queries directly (no prefix) - just type your question and press Enter
- `/voice` or `/v` - Start voice query mode (supports multiple languages like Hindi, English, Hinglish)
- `/remove <file>` or `/rm <file>` - Remove a file and its embeddings
- `/help` or `/h` - Show help
- `/quit`, `/exit`, or `/q` - Exit the CLI

---

## Project Structure

```
samvaad/
├── samvaad/          # Python code for the RAG pipeline and API
│   ├── pipeline/     # Core RAG components
│   │   ├── generation/    # LLM integration and TTS engine (Kokoro)
│   │   ├── ingestion/     # Document processing and chunking
│   │   ├── retrieval/     # Query processing and voice recognition
│   │   ├── vectorstore/   # Vector database operations
│   │   └── deletion/      # Document removal utilities
│   ├── utils/        # Utilities (hashing, DB, GPU detection)
│   ├── interfaces/   # CLI and API interfaces
│   │   ├── api.py    # FastAPI server with TTS API
│   │   └── cli.py    # Interactive CLI for testing and usage
├── data/             # Raw documents and audio responses
│   ├── documents/    # Source documents for knowledge base
│   └── audio_responses/  # Saved TTS audio files
├── tests/            # Unit and integration tests
├── requirements.txt  # Dependencies
└── README.md         # Project documentation
```

**Directory Overview:**
- **samvaad/**: Modular RAG pipeline, dual TTS engines, API, and CLI (Python)
- **samvaad/pipeline/generation/**: LLM integration (Gemini) and TTS engine (Kokoro)
- **samvaad/pipeline/retrieval/**: Query processing, voice recognition, and markdown handling
- **data/documents/**: Your source documents (PDFs, Office docs, text, images, etc.)
- **data/audio_responses/**: Automatically saved TTS audio files with engine-specific names
- **tests/**: Comprehensive test suite for reliability

## Features

- **Kokoro TTS:** Neural TTS engine with high-quality speech synthesis
- **Multilingual Voice Support:** Voice queries and responses in Hindi, English, and auto-detection for other languages
- **Retrieval-Augmented Generation (RAG):** Combines LLMs with your own documents for accurate, context-aware answers.
- **Complete Query Pipeline:** Ask natural language questions and get AI-powered answers with source citations.
- **GPU Acceleration:** Automatic GPU detection and usage for faster embeddings, parsing, and inference (when available).
- **Performance Monitoring:** Built-in timing instrumentation for ingestion, retrieval, and deletion steps.
- **OS-Agnostic Paths:** Cross-platform compatibility (Windows, macOS, Linux) with dynamic path resolution.
- **Modular Backend:** Easily extend or swap components in the RAG pipeline.
- **Modern Frontend (Coming Soon):** React + Next.js interface for a seamless chat experience.
- **Interactive CLI:** Full document processing and querying via an interactive command-line interface.
- **Multiple LLM Support:** Works with OpenAI GPT models and Google Gemini, with graceful fallback.
- **Easy Setup:** Simple installation with manual PyTorch selection for CPU or GPU.
- **Private & Secure:** Your data stays on your machine.

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

### About Test Warnings

Some warnings may appear during test runs from external dependencies (e.g., `docling-core`, `google-genai`). These warnings are **not from Samvaad code** but from upstream libraries that have known deprecation issues in Pydantic v2.12+. Here's how to minimize them:

**To reduce or eliminate warnings:**
1. Keep dependencies updated: `uv pip install --upgrade docling google-genai pydantic setuptools`
2. These are deprecation notices that will be fixed in future releases of the upstream libraries
3. The warnings do not affect functionality - all 175+ tests pass successfully

**Current state (as of Oct 2025):**
- `docling-core` 2.49.0: Pending upstream fix for Pydantic validator pattern
- `google-genai` 1.45.0: Pending upstream fix for Pydantic validator pattern  
- `setuptools` 80.9.0: `pkg_resources` deprecation warning (expected to be removed in setuptools 81+)

These warnings will disappear once the upstream libraries update their code to use instance methods instead of classmethods for Pydantic validators (required by Pydantic v2.12+).

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

Please see the [issues](https://github.com/atharva-again/samvaad/issues) page for ideas or to report bugs.

Future Development
The modular design of this project makes it easy to add new features. The backend/ and frontend/ folders are completely separate, so you can build out the user interface and connect it to the backend's API when you're ready.
