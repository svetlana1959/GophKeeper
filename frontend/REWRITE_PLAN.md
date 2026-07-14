# Frontend Rewrite Plan

A full rewrite of the GophKeeper web frontend on a typed, testable, scalable
stack. This document is the agreed plan; it is the reference for the phased work.

## Locked decisions

| Area               | Decision                                                                        |
| ------------------ | ------------------------------------------------------------------------------- |
| Language           | **TypeScript** (migrate, not rewrite-from-scratch)                              |
| Build              | **Vite** + **React 19**                                                         |
| Routing            | **react-router 7** — nested, lazy, data router                                  |
| Server state       | **TanStack Query** (React Query)                                                |
| API contract       | **openapi-typescript** — types generated from `/openapi.json`                   |
| Runtime validation | **Zod** at every API boundary                                                   |
| Styling            | **Tailwind CSS + shadcn/ui** (Radix under the hood)                             |
| Theming            | **Light + dark from day one** (design has both)                                 |
| Layout target      | **Desktop-first. No mobile now**, but structured so mobile is additive later    |
| Testing            | **Vitest + React Testing Library** (unit/component), **Playwright** (e2e smoke) |
| Formatting/lint    | **Prettier** + existing ESLint, path aliases (`@/`)                             |

### Web scope: metadata & management only — **no browser crypto**

The web app **never handles secret plaintext or age keys**. This keeps it out of
the zero-knowledge crypto path entirely. The web is for:

- Account auth (email + password → bearer session token)
- Device / trust-graph management (list devices, mint invites, revoke)
- Dashboards, statistics, settings
- Read-only secret **metadata** (names/types/counts) — _pending confirmation of
  what is server-visible; see Open Items_

The Figma's **View / New / Edit / Share Secret** actions are **out of scope** —
they require client-side decryption. On the Secrets screen we render the list as
read-only metadata and hide/disable the value actions with a "manage from the
CLI/desktop app" affordance. A `lib/crypto` seam is **not** built now; if the web
ever becomes a full client, it is an additive module, not a refactor.

## Architecture (layers)

```
src/
  app/            router, providers (Query, Theme, Auth), <ProtectedRoute>, error boundary
  api/
    http.ts       transport (fetch/axios) + auth header + 401 -> logout interceptor
    generated.ts  openapi-typescript output (do not edit; regenerated)
    schemas/      zod schemas per resource (validate responses)
    accounts.ts   auth/enroll/devices/stats/sync/... thin typed functions
  features/
    auth/         Login, Registration (+ loading/error/success), useLogin/useRegister
    dashboard/
    devices/
    statistics/
    settings/
    secrets/      metadata list only
    landing/
  components/ui/  shadcn primitives (Button, Input, Card, Dialog, DropdownMenu, Table, Tabs, Toast, ...)
  styles/         tailwind tokens (Figma vars: colors, spacing, radius, Inter type), light/dark themes
  lib/            utils (crypto/ intentionally absent for now)
```

- **Server state lives in React Query hooks** (`features/x/queries.ts`), never in
  the api modules — api stays pure (returns promises), hooks wrap it.
- **Client/UI state** = React Context (theme, auth). Add Zustand only if it grows.
- **Feature-sliced**: each feature owns its components, hooks, queries, routes.

## Auth model

- Account session: `POST /accounts/login` → bearer token.
- `AuthProvider` holds session; a single axios/fetch **interceptor** attaches the
  token and, on 401, clears it and redirects — removing the per-page `getToken()`
  checks in the current code.
- `<ProtectedRoute>` guards app routes; auth pages redirect authed users out.
- Token storage: start with `localStorage` (current behavior) but **document the
  XSS trade-off**; revisit httpOnly-cookie if the backend adds one.

## Responsive posture (desktop-first, mobile-ready)

- Build to the **desktop** Figma frames only. Do **not** build the Mob frames,
  breakpoints, or a mobile drawer yet.
- Keep it additive: componentize nav (`Sidebar`) so a mobile drawer can later wrap
  it; use Tailwind's responsive utilities and semantic tokens so `md:`/`lg:`
  variants are a later addition, not a rewrite.
- Fluid where free (`clamp()` type, `%`/`fr` grids); fixed desktop layout otherwise.

## Phases

- **Phase 0 — Scaffold.** TS config, Tailwind + shadcn init, `openapi-typescript`
  wired to a `gen:api` script, `http.ts` + React Query + zod, providers + router +
  `<ProtectedRoute>`, tokens/themes from Figma, Prettier, CI (typecheck + lint +
  unit + build), one Playwright smoke. Compiles and lints green; no final visuals.
- **Phase 1 — Auth.** Login + Registration (loading/error/success), light + dark,
  wired to `/accounts`. Validates the whole stack on the smallest surface.
- **Phase 2 — App shell + Dashboard.** Sidebar/topbar layout, Dashboard (overview
  cards from `/stats`, trusted devices, pending access requests = pending devices,
  recent activity) — all via React Query.
- **Phase 3 — Devices.** List (`/devices`), detail, **mint invite** (the web's
  most valuable, ZK-safe power), revoke. _Note: the invite payload tracks whichever
  enrollment model is on `dev` at build time; see Open Items re M4._
- **Phase 4 — Statistics + Settings.**
- **Phase 5 — Secrets (metadata).** Read-only list, value actions hidden. Gated on
  the metadata-visibility question below.
- **Phase 6 — Landing pages.**

## Open items to confirm (not blocking Phase 0/1)

1. **Secret metadata visibility.** Are secret names/types server-visible plaintext
   metadata, or part of the encrypted payload? If encrypted, the Secrets screen is
   also out of web scope until a metadata channel exists. (User indicated category
   _counts_ are sent as metadata — confirm whether per-secret names are too.)
2. **Enrollment model / M4 collision.** `dev` currently uses the old invite model
   (server generates the code). M4 (PR #145) switches `/enroll/invite` to a
   client-generated `{code_hash, roster}`. When M4 merges, the web invite flow must
   generate a code + HMAC roster (WebCrypto HMAC — not secret crypto, still in
   scope). Decide merge order so the FE targets one model.
3. **"Username" vs "email".** Login Figma says "Username"; backend authenticates by
   email. Recommend keeping `email` (type=email + validation), relabel only.
4. **Token storage** strategy (localStorage vs future httpOnly cookie).

## Scripts / CI

- `dev`, `build`, `preview`, `lint`, `typecheck`, `test`, `test:e2e`,
  `gen:api` (regenerate types from `/openapi.json`).
- CI on PR: `typecheck` + `lint` + unit + `build`; Playwright smoke on the auth flow.
