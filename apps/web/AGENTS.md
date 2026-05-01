# Web App - Agent Guidelines

## Role
Next.js 16 web application that displays the generated AI blog posts. Built with React 19, Tailwind CSS v4, and TypeScript.

## Key Constraints & Next.js 16 Rules
- **Synchronous Params:** Next.js v16 uses synchronous `params` in page components. **Do NOT `await params`**; they are accessed synchronously.
- **Server Components:** By default, files are Server Components. They should fetch data directly from Supabase (do not import a separate API client in server files).
- **Client Components:** Must explicitly use the `"use client"` directive at the top of the file if they require client-side interactivity (e.g., hooks, state, events).
- **Suspense & Loaders:** Use React `Suspense` with fallback components for skeleton loaders (not just relying on `loading.tsx`).
- **Infinite Scroll:** Implement using `IntersectionObserver` (refer to patterns in `PostFeed.tsx` if available).

## Styling (Tailwind 4 & CSS)
- **Custom Colors:** The project uses specific custom colors defined via CSS variables in `globals.css` (e.g., `#131316` for dark theme background, `#393A41`, `#6A6B70`, `#9A9BA2`). Favor these over standard Tailwind color palettes where applicable.
- **Borders:** A common pattern for borders is `border-[#393A41] border-dashed`.

## Integration & Environment
- **Read-Only Access:** The web application only READS data from Supabase using the anon key. It does not write to the database (writes are handled by the ingest worker).
- **Rate Limiting:** Managed in `middleware.ts` via `RATE_LIMIT_*` environment variables.

## Developer Commands
- Start dev server: `npm run dev` (starts on port 3000)
- Lint code: `npm run lint`
- Type checking: `npx tsc --noEmit` **(Note: There is no `npm run typecheck` script; this must be run manually)**
