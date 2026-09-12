# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- The release gate decides from git tags instead of main's version field. A
  version above the newest tag is a release; a version equal to it is a
  maintenance change that ships nothing; anything lower is rejected. Merging a
  CI or docs fix into `main` no longer forces a version bump, and a release
  that fails before tagging can be retried under the same version instead of
  burning it, which is what happened to 0.1.0.
- The PyPI upload uses `skip-existing`, and tagging accepts a tag already
  pointing at the same commit, so every release step is safe to repeat.

## [0.1.1]

First published release. 0.1.0 was merged but never shipped: the release
workflow died on a startup failure before tagging or publishing anything, and
the release gate refuses to reuse a version that already sits on `main`.

### Added

- GitHub Actions pipelines: code validation on `develop`, a release gate on
  pull requests into `main`, security scanning, version tagging, GitHub
  releases and PyPI publishing.
- Ruff, mypy, bandit and coverage configuration in `pyproject.toml`.

### Fixed

- The `dependency-review` job requested `pull-requests: write`, more than the
  release workflow granted it, which GitHub rejects when the workflow starts.
  It now runs with `contents: read` only.
- The release workflow tagged before publishing to PyPI, so a failed upload
  left a tag that made every later attempt at that version skip itself.

## [0.1.0]

### Added

- `map3d_viewer`, `map3d_scene` and `map3d_area_selector` Reflex components.
- Overpass API client with fallback endpoints and GeoJSON feature conversion.
- `BBox` bounding-box value object and Overpass query builders.
- Demo application under `map3d_demo/`.

[Unreleased]: https://github.com/ecrespo/reflex-map3d/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/ecrespo/reflex-map3d/releases/tag/v0.1.1
[0.1.0]: https://github.com/ecrespo/reflex-map3d/releases/tag/v0.1.0
