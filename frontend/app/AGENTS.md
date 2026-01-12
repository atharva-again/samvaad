# FRONTEND APP KNOWLEDGE BASE

## OVERVIEW
Next.js App Router root, managing routing, global state providers, and high-level UI structure.

## STRUCTURE
```
frontend/app/
├── auth/                 # Auth-related route handlers and error pages
│   ├── callback/route.ts # Supabase auth callback handler
│   └── auth-code-error/  # Error page for auth failures
├── chat/[id]/            # Dynamic chat session routes
├── login/                # Authentication entry point
├── globals.css           # Tailwind base, shadcn tokens, and "void" theme
├── layout.tsx            # Root layout with Auth/Pipecat providers
└── page.tsx              # Application landing page
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Root Providers | `layout.tsx` | `AuthProvider`, `PipecatProvider` |
| Chat Logic | `chat/[id]/page.tsx` | Main conversation interface |
| Auth Redirects | `auth/callback/route.ts` | Server-side auth flow |
| Global Styles | `globals.css` | Theme colors and selection styles |

## CONVENTIONS
- **App Router**: Follows Next.js 15+ conventions. Use `page.tsx` for views and `layout.tsx` for shared UI.
- **Client vs Server**: Default to Server Components. Use `'use client'` only at the leaf nodes or specialized provider wrappers.
- **Theme**: Strictly follows the "dark" theme using the `bg-void` background and `text-text-primary` colors defined in `globals.css`.
- **Components**: Prefers Shadcn/ui components located in `frontend/components/ui`.

## ANTI-PATTERNS
- **Direct CSS**: Avoid adding CSS in `globals.css` that can be handled by Tailwind utility classes.
- **Context Overuse**: Don't wrap small components in new contexts; lift state to `layout.tsx` or use existing providers.
- **Static Paths**: Avoid hardcoding `/chat/123` style links; use dynamic routing and proper state management.
