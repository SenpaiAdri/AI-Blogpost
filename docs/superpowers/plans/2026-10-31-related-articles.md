# Related articles implementation plan

**Goal:** Add three relevant published articles beside the current post on wide screens and below it on smaller screens, preserving the existing UI.

**Approved scope:** The user approved responsive recommendations and explicitly excluded applying the mockup's redesign. Keep typography, colors, article contents, source placement, and AI discussion unchanged. No deployment or hosting migration.

**Approach:** Match shared tag IDs, rank by overlap then newest publication, exclude the current and unpublished posts, and omit the section when nothing matches. Cache a lightweight server-side candidate query for 600 seconds. Bound the pool to the 100 newest matching published posts; no AI or browser database requests. Keep a single recommendation section in document order after the article, moving it to a right column at xl widths.

## Task 1: Data and component
- [x] Add Node built-in tests for ranking, recency, self/unpublished/unrelated exclusions, empty input, and the three-result limit; observe failure first.
- [x] Add a typed ranking helper, cached query, and a server-rendered recommendation component using existing theme tokens and links.

## Task 2: Integration and verification
- [x] Adjust only the article page container/grid; preserve its existing content and article width.
- [x] Run ranking tests, lint, TypeScript, and production build.
- [x] Check desktop/mobile layout and review the final diff for unintended redesign or private data exposure.

**Checks:** `node --experimental-strip-types --test tests/related-posts.test.mjs`, `npm run lint`, `npm run typecheck`, `npm run build` from apps/web.

**Risks to inspect:** empty tags/matches, drafts and current post exclusion, duplicate tags inflating scores, long titles, query failure, and no-match article width. Deployment verification is separate.

**Verified:** 4 ranking tests passed; lint passed with the existing BlogContent image warning; TypeScript passed; production build pre-rendered 933 pages. Live public-key query succeeded. Browser checks at desktop and 390px confirmed three links, responsive placement, and no horizontal overflow. Focused independent review found no actionable bugs. No deployment, migration, or main-checkout changes.
