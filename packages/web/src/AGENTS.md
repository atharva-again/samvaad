# WEB APP KNOWLEDGE BASE

## OVERVIEW

Vite-served React SPA using TanStack Router. The Hono API runs separately and its browser origin is configured with `VITE_API_URL`.

## STRUCTURE

```
packages/web/src/
├── routes/               # Home, login, auth error, and dynamic chat views
├── router.tsx            # TanStack Router route tree
├── root-layout.tsx       # Auth/LiveKit providers and app-wide UI
├── main.tsx              # React/Vite bootstrap
└── styles.css            # Tailwind theme and global styles
```

## WHERE TO LOOK

| Task           | Location                                 | Notes                             |
| -------------- | ---------------------------------------- | --------------------------------- |
| Routes         | `router.tsx`, `routes/`                  | TanStack Router                   |
| Root Providers | `root-layout.tsx`                        | `AuthProvider`, `LiveKitProvider` |
| Chat Logic     | `routes/chat.tsx`, `../components/chat/` | Main conversation interface       |
| Auth Client    | `../lib/auth-client.ts`                  | Better Auth client and API origin |
| Global Styles  | `styles.css`                             | Theme colors and selection styles |

## CONVENTIONS

- **Routing**: Add pages to the TanStack Router tree; use typed `Link` and `useNavigate` for internal navigation.
- **Runtime**: The web app is a browser-only SPA. Keep secrets on the API; only expose public `VITE_*` config.
- **Theme**: Strictly follows the "dark" theme using the `bg-void` background and `text-text-primary` colors defined in `styles.css`.
- **Components**: Prefers Shadcn/ui components located in `packages/web/components/ui`.

## ANTI-PATTERNS

- **Direct CSS**: Avoid adding CSS in `globals.css` that can be handled by Tailwind utility classes.
- **Context Overuse**: Don't wrap small components in new contexts; lift state to `layout.tsx` or use existing providers.
- **Dynamic Paths**: Use TanStack Router route params for chat links rather than hardcoded IDs.
