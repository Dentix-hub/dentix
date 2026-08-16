---
name: dentix-frontend-react
description: Implement or review DENTIX React/Vite UI work, components, pages, hooks, React Query data flows, Zustand client state, accessibility, responsive UI, or frontend performance.
---

# DENTIX Frontend React & Vite Guide

## Technology & Design System
- **Framework**: React 18 + Vite.
- **Styling**: Tailwind CSS + custom design tokens.
- **Server State**: TanStack React Query (`@tanstack/react-query`) for API data caching, polling, and mutations.
- **Client State**: Zustand stores (`src/stores/`) for local/transient client and UI state.
- **Prohibition**: Do NOT introduce Redux or other global store libraries.

## Architecture Guidelines

### Component Organization & UI Reuse
- Prioritize existing shared components in `frontend/src/shared/ui/` (`Button`, `Modal`, `Input`, `Toast`, `Badge`, `Card`) before creating new primitives.
- Decompose complex pages into focused sub-components under feature folders.
- Ensure bidirectional RTL (Arabic) and LTR (English) support for all UI text, layouts, forms, and dialogs.

### Server State Management (React Query)
- Encapsulate API queries and mutations in custom hooks under `frontend/src/hooks/` or feature API files.
- Configure appropriate `queryKey` structures with tenant and filter parameters.
- Invalidate relevant query caches upon successful mutation (`queryClient.invalidateQueries`).
- Handle loading, error, and empty states cleanly with skeleton loaders and feedback alerts.

### Accessibility (a11y) & UX Standards
- Provide proper `aria-label`, `role`, and form association (`htmlFor` / `id`) on interactive elements.
- Ensure full keyboard navigability for modals, dropdowns, and tab groups.
- Maintain accessible color contrast and clear focus indicators.
- Preserve responsive breakpoints across mobile, tablet, and desktop views.

### Verification Checklist
- Run linter: `npm run lint` (or `cmd /c "npm run lint"`).
- Run unit/component tests: `npm run test` (or `cmd /c "npm test"`).
- Run production build check: `npm run build` (or `cmd /c "npm run build"`).
- Validate rendered UI against responsive viewports and language directions.
