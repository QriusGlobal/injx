# Archive Directory

This directory contains internal development documentation, task files, and workflows that are not part of the public API or user-facing documentation.

## Contents

### `archive/docs/`
Internal development documentation that is not linked in the public documentation site:

- **concurrency.md** - Detailed analysis of concurrency patterns and ContextVar usage
- **internals.md** - Internal implementation details and architecture specifics
- **philosophy.md** - Development philosophy and design principles (see CLAUDE.md for public version)
- **RELEASE_RECOVERY.md** - Procedures for release recovery and rollback
- **WORKFLOW_TESTING.md** - Internal workflow testing procedures

These documents are preserved for developer reference but are not included in the public documentation because they cover internal implementation details rather than user-facing APIs.

### `archive/.task/`
Claude Code task files and automation scripts:

- **commit-*.sh** - Commit automation scripts
- **rebase-*.sh** - Rebase automation scripts
- **semantic-versioning-correction-*.md** - Semantic versioning correction tasks and procedures
- **gemini-architectural-review.md** - Architectural review notes
- **rollback-procedures.md** - Rollback procedures documentation

These files are preserved for reference but are not part of the production codebase.

## Usage

This archive is provided for reference and historical purposes. When working with the project:

1. Refer to public documentation in `/docs` for user-facing APIs and guides
2. Refer to `README.md`, `CONTRIBUTING.md`, and `CLAUDE.md` for contribution guidelines
3. Use this archive only for understanding internal development history and procedures

## Notes

- These files are not tracked in the primary documentation build
- They are preserved to maintain development history and context
- Public documentation (in `/docs`) should be the primary reference for users and contributors
