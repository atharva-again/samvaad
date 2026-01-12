# Samvaad Frontend

> **Premium Conversational UI for Dialogue-Based Learning**

This is the Next.js frontend for Samvaad, designed to provide a seamless, premium interface for both text-based RAG chat and real-time WebRTC voice sessions.

## 🎨 UI/UX Philosophy

- **Void Theme**: A custom-crafted dark mode experience using deep blacks (`bg-void`) and high-contrast typography.
- **Glassmorphism**: Subtle use of transparency and blurs for a modern, layered feel.
- **Responsive & Dynamic**: Fully adaptive layout with fluid animations powered by Framer Motion.
- **Shadcn/ui**: Built on top of accessible, modular components with a custom "New York" style.

## 🛠 Tech Stack

- **Framework**: Next.js 15+ (App Router, Server Components)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: Zustand (UI state, chat session management)
- **Real-time Voice**: Daily WebRTC SDK & Pipecat integration
- **Linting/Formatting**: Biome (Fast, modern alternative to ESLint/Prettier)
- **Auth**: Supabase Auth (SSR support)

## 🚀 Getting Started

### Prerequisites
- pnpm (Recommended)
- Running Samvaad Backend (FastAPI)
- Supabase Project

### Installation

```bash
pnpm install
```

### Environment Setup

Create a `.env.local` file:

```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
pnpm dev
```

### Build & Lint

```bash
# Check for lint/format errors
pnpm biome check .

# Fix lint/format errors
pnpm biome check --apply .

# Build for production
pnpm build
```

## 🏗 Structure

- `app/`: Next.js App Router (Routes, Layouts, Pages)
- `components/`:
  - `chat/`: Core chat interface components (InputBar, MessageList, SourcesPanel)
  - `ui/`: Base Shadcn/ui components
  - `navigation/`: Sidebar and header elements
- `contexts/`: React Contexts for Auth and Global State
- `hooks/`: Custom React hooks (Audio devices, Chat logic)
- `lib/`: Shared utilities and store definitions (Zustand)
- `utils/`: API clients and helper functions

## 🧠 Developer Context

For detailed information on frontend-specific conventions, anti-patterns, and file roles, see:
👉 **[`app/AGENTS.md`](./app/AGENTS.md)**

---

Built with ❤️ for better learning.
