# Release Process

Releases are automated with Release Please:

1. Merge Conventional Commits into `main`.
1. Release Please opens a release PR with version bump and changelog.
1. Merge the release PR to tag and publish a GitHub Release.
1. The `publish.yml` workflow builds and publishes to PyPI.

See also the maintainer notes in README and `CLAUDE.md`.
