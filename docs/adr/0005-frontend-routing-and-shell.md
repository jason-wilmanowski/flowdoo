# ADR 0005: Frontend routing and app shell

- **Status:** accepted
- **Date:** 2026-10-03

## Context

The frontend needs URLs for the trace list, a single trace and the overview, so a trace can
be linked and reloaded. Data loading already lives in stores behind a `DataSource`
(ADR 0004); the router must not become a second data layer. The app shell has to show the
connection state, the active data source and the theme on every page.

## Decision

- **React Router 8 in declarative mode** (`BrowserRouter`, `Routes`, `Route`, `Outlet`,
  `NavLink`, `useParams`). No loaders, actions or framework mode: routes only select what
  to show, pages call store actions (`load(id)`) in effects.
  - Considered TanStack Router (type-safe params, but its strength is the loader/data
    layer we do not use, and file-based routing adds a build plugin) and wouter (small, but
    no `aria-current` NavLink and fewer users). React Router is the most widely known option
    and its declarative mode is a thin dependency.
- **Routes:** `/` → `/traces`; `/traces`; `/traces/:traceId`; `/overview` (placeholder until
  M6); anything else renders a not-found page inside the shell. `/_kit` stays outside the
  router and only exists in development builds.
- **Shell as layout route:** `AppShell` renders the top bar and the connection notices once
  and the page in its `<Outlet>`. Pages compose `SplitPanel` (left, main, right) and an
  optional bottom bar themselves, so each page decides which panels it has.
- **Stores in React:** one `AppStores` set per data source, provided by context
  (`useStores()`, `useAppStore(store, selector)`). Switching the data source in the top bar
  creates a new store set; the choice is stored in `localStorage` (`flowdoo.dataSource`)
  and overrides `VITE_DATA_SOURCE` until switched back.
- **Keyboard shortcuts:** one global registry (`ShortcutProvider`). Components register
  shortcuts with `useShortcut`; one `keydown` listener dispatches them, ignores keys typed in
  inputs and keys with Ctrl/Meta/Alt, and feeds the help dialog (`?`). Only the help
  shortcut exists yet; replay keys come with the replay feature.

## Consequences

- Deep links work with the Vite dev server (history fallback). A static deployment needs an
  `index.html` fallback; that is documented when deployment is.
- Pages own their data loading via store actions, which keeps them testable with a fixture
  data source and `MemoryRouter`.
