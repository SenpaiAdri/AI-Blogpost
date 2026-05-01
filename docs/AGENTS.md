# Documentation - Agent Guidelines

## Role
This folder acts as the single source of truth for high-level system architecture, operational guidelines, and local development setup.

## Key Files
- `architecture.md`: Defines the system boundaries, runtime choices, and data flow.
- `local-development.md`: Instructions for setting up the local environment, including Supabase and environment variables.
- `operations.md`: Runbooks and guides for managing the production state.

## Important Constraints & Rules
- **Documentation Drift Governance:** If you execute a task that introduces major changes to the system (e.g., adding a new service, changing how deployment works, altering the database architecture, or adding significant new dependencies), you **MUST** update the relevant `.md` files in this directory to reflect those changes.
- **Architectural Integrity:** Do not suggest or implement changes that violate the boundaries defined in `architecture.md` (e.g., merging the Python worker into the Next.js app) without explicit permission and discussion with the user.
