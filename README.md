## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


# Samvaad - Your RAG Chatbot

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

<p align="center">
	<img src="docs/screenshot.png" alt="Samvaad Screenshot" width="600"/>
</p>

**Samvaad** (Sanskrit for "dialogue") is an open-source Retrieval-Augmented Generation (RAG) chatbot that delivers accurate, context-aware answers from your own documents. Built with a modular backend and a modern frontend, Samvaad makes it easy to deploy a powerful, private AI assistant for any knowledge base.


## Project Structure

```
samvaad/
├── backend/    # Python code for the RAG pipeline and API
├── frontend/   # React + Next.js user interface (WIP)
├── data/       # Raw documents for the knowledge base
├── tests/      # Unit and integration tests
└── README.md   # Project documentation
```

**Directory Overview:**
- **backend/**: Modular RAG pipeline and API (Python)
- **frontend/**: Modern UI (React/Next.js)
- **data/**: Your source documents (PDFs, etc.)
- **tests/**: All tests for reliability

pip install -r requirements.txt

## Features

- **Retrieval-Augmented Generation (RAG):** Combines LLMs with your own documents for accurate, context-aware answers.
- **Complete Query Pipeline:** Ask natural language questions and get AI-powered answers with source citations.
- **Modular Backend:** Easily extend or swap components in the RAG pipeline.
- **Modern Frontend (Coming Soon):** React + Next.js interface for a seamless chat experience.
- **Command Line Interface:** Full document processing and querying via CLI.
- **Multiple LLM Support:** Works with OpenAI GPT models, with graceful fallback when no API key is available.
- **Easy Setup:** Simple installation and configuration.
- **Private & Secure:** Your data stays on your machine.

---

## Getting Started

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

**macOS/Linux:**
```sh
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```sh
pip install -r requirements.txt
```

### 4. Add Your Documents

Place your PDF files inside the `data/documents/` folder. These will be used as the chatbot's knowledge base.

### 5. Configure Environment (Optional)

For AI-powered answers, copy the environment template and add your OpenAI API key:

**Windows:**
```sh
copy .env.template .env
```

**macOS/Linux:**
```sh
cp .env.template .env
```

Edit the `.env` file and add your OpenAI API key:
```
OPENAI_API_KEY=your_actual_api_key_here
```

**Note:** The system works without an API key but will only show retrieved context without AI-generated answers.

### 6. Process Your Documents

```sh
python backend/test.py path/to/your/document.pdf
```

### 7. Query Your Knowledge Base

```sh
# Ask questions about your documents
python backend/test.py -q "What is the main topic discussed?"

# Get more detailed results
python backend/test.py -q "Explain the key concepts" -k 10

# Use GPT-4 for better answers (requires API key)
python backend/test.py -q "Compare different approaches" -m gpt-4
```

## Usage Examples

### Document Processing
```sh
# Process a single document
python backend/test.py documents/research_paper.pdf

# Remove a document and its embeddings
python backend/test.py documents/old_file.pdf -r
```

### Querying Your Knowledge Base
```sh
# Basic query
python backend/test.py -q "What are the main findings?"

# Query with more context chunks
python backend/test.py -q "Explain the methodology" -k 8

# Use GPT-4 for sophisticated analysis
python backend/test.py -q "What are the implications?" -m gpt-4

# Debug mode (shows the full prompt sent to LLM)
DEBUG_RAG=1 python backend/test.py -q "Your question here"
```

### Example Output
```
🔍 Processing query: 'What is the theory of Ballism?'
============================================================

📝 QUERY: What is the theory of Ballism?

🤖 ANSWER:
The theory of Ballism, formally known as the Principle of Spherical Convergence, posits that all matter and energy in the universe is subject to a fundamental force that compels it to assume a perfect spherical shape over infinitely long periods. This concept suggests that gravity is merely one manifestation of this underlying force, which acts at molecular and subatomic levels to eliminate sharp angles and fill concavities.

📚 SOURCES (3 chunks retrieved):

1. ballism.txt (Similarity: 0.847)
   Preview: The theory of Ballism, formally known as the Principle of Spherical Convergence, posits that all matter and energy in the known universe...

2. ballism.txt (Similarity: 0.723)
   Preview: Dr. Finch's initial "Finches' Folly" experiment involved placing a precisely cut cube of monocrystalline silicon...
```


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