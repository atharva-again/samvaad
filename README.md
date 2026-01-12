# Samvaad (संवाद)

> **Dialogue-Based Learning Facilitated by Real-Time AI**

Samvaad is a sophisticated, full-stack Retrieval-Augmented Generation (RAG) platform that transforms static documents into interactive, dialogue-driven learning experiences. By combining state-of-the-art vector retrieval with ultra-low-latency WebRTC voice conversations, Samvaad allows you to talk to your knowledge—literally.

## Key Features

- **Real-Time Voice Mode**: Ultra-low latency voice conversations using WebRTC (Daily) and the Pipecat framework. Interact naturally with your documents using voice.
- **Deep RAG Pipeline**: Advanced document ingestion supporting PDF, Docx, Images (OCR), and more via LlamaParse and Docling.
- **Intelligent Deduplication**: Content-addressable storage (SHA-256) ensures zero-redundancy in document chunks across users.
- **Multi-Model Intelligence**: Optimized for Gemini, Groq, and OpenAI, with high-quality embeddings via Voyage AI.
- **Neural TTS & STT**: Crystal-clear speech synthesis using Kokoro and Deepgram for a human-like conversational experience.
- **Modern Full-Stack Architecture**: A high-performance FastAPI backend paired with a premium Next.js 15+ frontend.

## Tech Stack

### Backend (Python)
- **Framework**: FastAPI (Asynchronous, High Performance)
- **Package Manager**: [uv](https://astral.sh/uv) (Extremely fast Python package installer)
- **Database**: PostgreSQL with `pgvector` (Vector similarity search)
- **Voice Framework**: [Pipecat](https://github.com/pipecat-ai/pipecat) & [Daily](https://www.daily.co/)
- **AI/LLM**: Google Gemini, Voyage AI (Embeddings), Deepgram (STT/TTS)

### Frontend (TypeScript)
- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS with a custom "Void" Dark Theme
- **UI Components**: Shadcn/ui & Framer Motion
- **Auth**: Supabase (OAuth & Email)

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ & pnpm
- Supabase Account
- API Keys: Gemini, Voyage AI, Deepgram, Daily, Supabase

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/atharva-again/samvaad.git
   cd samvaad
   ```

2. **Setup Backend:**
   ```bash
   # Install uv if you haven't
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Sync dependencies and create venv
   uv sync
   ```

3. **Setup Frontend:**
   ```bash
   cd frontend
   pnpm install
   ```

### Configuration

Create a `.env` file in the root directory (for backend) and `frontend/.env.local` (for frontend).

**Backend `.env`:**
```env
# AI & Pipeline
GEMINI_API_KEY=...
VOYAGE_API_KEY=...
DEEPGRAM_API_KEY=...
DAILY_API_KEY=...

# Database
DATABASE_URL=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

## Development

### Run Backend
```bash
# From the root
uvicorn samvaad.api.main:app --reload
```

### Run Frontend
```bash
# From the frontend directory
pnpm dev
```

### Interactive CLI (Internal testing)
```bash
# From the root
samvaad
```

## Project Structure

```text
.
├── samvaad/           # Core Backend Logic
│   ├── api/           # FastAPI Routes & App Initialization
│   ├── core/          # Shared Logic (Auth, Memory, Unified Context)
│   ├── db/            # Database Models & Service Layer (pgvector)
│   ├── pipeline/      # RAG Pipeline (Ingestion, Retrieval, Deletion)
│   ├── prompts/       # AI Personas & System Prompt Engineering
│   └── utils/         # Citation Handling, Text Processing, Hashing
├── frontend/          # Next.js Application
├── tests/             # Pytest Unit & Integration Suites
├── PLANS/             # Living Architecture & Development Roadmap
└── AGENTS.md          # Developer Knowledge Base for AI Assistants
```

## Developer Knowledge Base

This project maintains a hierarchical set of `AGENTS.md` files that act as a "source of truth" for code conventions, architecture, and anti-patterns.

- **Root Context**: [`AGENTS.md`](./AGENTS.md)
- **API Context**: [`samvaad/api/AGENTS.md`](./samvaad/api/AGENTS.md)
- **DB Context**: [`samvaad/db/AGENTS.md`](./samvaad/db/AGENTS.md)
- **Frontend Context**: [`frontend/app/AGENTS.md`](./frontend/app/AGENTS.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
