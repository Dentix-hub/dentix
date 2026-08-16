---
name: dentix-mobile-flutter
description: Implement or review DENTIX Flutter/Dart mobile work, screens, state, API integration, navigation, platform behavior, or mobile-specific UI and performance.
---

# DENTIX Mobile Flutter & Dart Guide

## Architecture Overview
The DENTIX mobile client (`dentix_mobile/`) is built using Flutter/Dart with a clean feature-driven structure:
- **State Management**: Riverpod (`flutter_riverpod`).
- **Routing & Navigation**: `go_router`.
- **Networking & API**: `dio` with centralized interceptors for authentication, tenant headers, and token refresh.
- **Model Serialization**: `freezed` / `json_serializable`.

## Core Mobile Principles

### Architecture & Layering
Follow the existing feature/module structure used by the mobile codebase. The current structure organizes features under `dentix_mobile/lib/features/<feature>/` with layers such as:
- **Presentation**: Screens, pages, and controllers in `presentation/`.
- **Domain**: Entities, use cases, and repository interfaces in `domain/`.
- **Data**: Repositories, data sources, and models in `data/`.
- **No Duplicate Logic**: Never duplicate complex backend financial calculations or clinical validation on the mobile client; delegate to FastAPI backend endpoints.

### Authentication, RBAC & Lifecycle
- Respect active tenant scope and user permissions in route guards and UI rendering.
- Handle token expiration and refresh automatically via Dio interceptors.
- Handle app lifecycle transitions (background/foreground), offline states, and network timeouts gracefully.
- Minimize platform permissions and avoid introducing native plugins without verified cross-platform compatibility.

### Verification Checklist
When the Flutter SDK and project dependencies are available:
- Run Flutter static analysis: `flutter analyze`.
- Run Flutter test suite: `flutter test`.
- Verify widget rebuild performance and memory leaks during state transitions.
