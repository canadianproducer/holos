# Contributing to Holos

Issues and pull requests are welcome, in English or Ukrainian.

## Branches
- `main` always holds working code. Nothing is committed to `main` directly.
- Every change gets its own branch from `main`:
  `fix/…` (bug fix), `feat/…` (feature), `docs/…`, `test/…`, `build/…`, `ci/…`, `chore/…`.
- One branch = one logical change. When done, merge into `main` with `git merge --no-ff`
  (or a pull request on GitHub) and delete the branch.

## Commits
[Conventional Commits](https://www.conventionalcommits.org/): `fix(autostart): …`, `feat(stt): …`, `docs: …`,
`chore(release): …`. The first line says what changed; the body explains why.

## Versioning (SemVer: MAJOR.MINOR.PATCH)
- **PATCH** (0.4.0 → 0.4.1) — bug fixes only.
- **MINOR** (0.4.1 → 0.5.0) — new features, compatible with existing settings and data.
- **MAJOR** (0.x → 1.0.0, 1.x → 2.0.0) — breaking changes (settings, data format).
  While the version is 0.x the project is in early development.

The version lives in one place: `VERSION` in `app/common.py`. The installer, the exe properties and CI read it from there.

## Releasing
1. All changes are merged into `main`, described under `[Unreleased]` in `CHANGELOG.md`, and CI is green.
2. On a `release/X.Y.Z` branch: bump `VERSION` in `app/common.py`, rename `[Unreleased]` to `[X.Y.Z] - date`.
   Commit `chore(release): X.Y.Z` → merge into `main` → annotated tag `vX.Y.Z` (`git tag -a vX.Y.Z -m "Holos X.Y.Z"`).
3. `release.bat` verifies the version, the CHANGELOG section and the tag, then pushes `main` and the tag.
4. GitHub Actions (`release.yml`) does the rest: builds with the same `build.bat` on a clean Windows runner, runs the
   unit tests, smoke-tests the exe, installs/runs/uninstalls the installer silently, writes `SHA256SUMS.txt` and
   publishes the release with notes taken from `CHANGELOG.md`. If any check fails, nothing is published.
5. A published tag is never rewritten. A broken release is fixed by the next PATCH version.

A test build without publishing: GitHub → Actions → Release → Run workflow (the installer appears under Artifacts).

## Dependencies
- `requirements.txt` — direct dependencies with exact versions (git archives pinned by commit).
- `requirements.lock` — the full set of packages a release is built with; `build.bat` installs exactly this.
- To update libraries: a `build/…` branch — change `requirements.txt`, build, test, regenerate `requirements.lock`.

## Checks
Locally: `pip install -r requirements-dev.txt`, then `pytest`, `ruff check .`, `ruff format --check .`
(or run `pre-commit install` once and they run before every commit).

GitHub Actions (`.github/workflows/ci.yml`) on every push to `main` and every pull request: ruff (bugs, style,
security), tests on Linux and Windows, and a `CHANGELOG.md` section for the current `VERSION`.
Before a release, also by hand: `Holos.exe --selftest`, dictation and read-aloud on a real PC.

Every behaviour change comes with a test whenever the logic can be checked without a microphone or models.

## Language
Documentation and commit messages are in English. The app's interface is in Ukrainian; code comments are mostly
Ukrainian for historical reasons — new code may use either language.
