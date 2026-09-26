# Changelog

All notable changes to Holos are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Release script: the tag is pushed separately from the branch, so GitHub reliably starts the release build.

## [0.4.0] - 2026-09-25

### Added
- Settings `save_history` (keep dictation history) and `log_text` (write dictated text to the log — for debugging only).
- `Holos.exe --smoke` checks a packaged build without models.
- Holos.exe carries version and description in its file properties; component licenses are installed with the app.

### Changed
- Releases are built and tested by GitHub Actions on a clean Windows runner: unit tests, a run of the built app,
  a silent install/run/uninstall cycle. Each release includes `SHA256SUMS.txt`.
- Reproducible builds: exact versions of all dependencies (`requirements.lock`), uv and Python; the version number
  lives in one place.
- Documentation is in English, with a Ukrainian README (`README.uk.md`).

### Fixed
- The "Holos.vbs … The system cannot find the file specified" error no longer appears after Windows restarts.
  Autostart is now a registry entry; the old Startup-folder file is removed automatically.
- **Security:** an update is installed only after its size and SHA-256 checksum are verified; without a checksum
  the app only links to the release page. The NVIDIA acceleration pack is verified against SHA-256 values pinned in code.
- **Privacy:** dictated text is no longer written to the error log (users attach it to public issues).
  Older logs that contain it are deleted once on the first start of 0.4.0. The log and the history are size-limited.
- A corrupt `config.json` is no longer overwritten with defaults — a copy is kept as `config.json.broken`;
  settings are saved atomically and values of the wrong type are ignored.
- The build reported success even when the installer step failed.
- Updates no longer re-enable autostart after it was turned off in the tray menu; uninstalling removes the
  autostart registry entry.

### Developer
- Branching and release process (CONTRIBUTING.md), architecture (docs/ARCHITECTURE.md), SECURITY.md,
  THIRD_PARTY_NOTICES.md, issue and pull request templates.
- 50+ unit tests (pytest), ruff (style, bugs, security), pre-commit, CI on Linux and Windows, Dependabot.

## [0.3.0] - 2026-09-24

### Added
- `Holos-Setup.exe` installer that needs no administrator rights.
- Automatic updates from GitHub Releases.
- NVIDIA acceleration pack downloaded on first launch.
- Smart cleanup via Ollama no longer delays dictation.

## [0.2.0] - 2026-09-24

### Added
- First working release: dictation (Right Ctrl) and read-aloud (Ctrl+Shift+Space).

[Unreleased]: https://github.com/canadianproducer/holos/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/canadianproducer/holos/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/canadianproducer/holos/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/canadianproducer/holos/releases/tag/v0.2.0
