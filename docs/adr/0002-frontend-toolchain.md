# ADR 0002: Frontend toolchain

- **Status:** accepted
- **Date:** 2026-10-03

## Context

The frontend (`frontend/`) needs a toolchain that the container, CI and local development
share exactly. The project standard (CLAUDE.md) is React + TypeScript (strict), Vite, pnpm,
Zustand, React Flow, Vitest, ESLint, Prettier and Stylelint.

## Decision

- **Node 22** (the pinned `node:22` image of the `frontend` service; local Node 22 too).
- **pnpm 12.8.1**, pinned via `packageManager` in `package.json`. Container and CI get it from
  corepack, so all three use the same version and `pnpm install --frozen-lockfile` works
  everywhere.
- **Vite 8, React 19, Vitest 5** (current releases).
- **TypeScript 6.0**, not 7. The current `typescript-eslint` (8.71) supports TypeScript
  `>=4.8.4 <6.1.0`; type-aware linting is worth more than the newer compiler. Revisit when
  `typescript-eslint` supports 7.
- **Strict compiler settings** beyond `strict`: `noUncheckedIndexedAccess`,
  `noImplicitOverride`, `verbatimModuleSyntax`, unused locals/parameters are errors.
- **ESLint:** `strictTypeChecked` from `typescript-eslint`, React hooks rules, and
  `no-console` as an error: values from the user's Odoo can be sensitive and must never end
  up in logs.
- **No Makefile:** the project has none (CLAUDE.md section 4). Commands are `pnpm` scripts in
  `frontend/`: `dev`, `build`, `typecheck`, `lint`, `fmt`, `test`.
- **Path alias** `@/` → `src/`, defined in `tsconfig.app.json` and `vite.config.ts`.
- **File watching in Docker:** `VITE_USE_POLLING=true` switches Vite to polling, which bind
  mounts on macOS/Windows need for hot reload.

## Consequences

- Upgrading pnpm, Node or TypeScript is a deliberate change of `package.json` (and this ADR).
- CI runs lint, typecheck, test and build for the frontend on every pull request.
