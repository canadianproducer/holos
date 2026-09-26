import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "release_notes", Path(__file__).parent.parent / "tools" / "release_notes.py"
)
release_notes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_notes)

CHANGELOG = """# Журнал змін

## [Unreleased]

## [1.1.0] — 2026-01-02

### Додано
- Нове.

## [1.0.0] — 2026-01-01

### Виправлено
- Старе.

[1.1.0]: https://example/compare
"""


def test_extracts_only_requested_section():
    body = release_notes.changelog_section(CHANGELOG, "1.1.0")
    assert body == "### Додано\n- Нове."


def test_missing_version_fails():
    with pytest.raises(SystemExit):
        release_notes.changelog_section(CHANGELOG, "9.9.9")


def test_current_changelog_has_current_version():
    import common

    notes = release_notes.main(common.VERSION)
    assert f"Holos-Setup-{common.VERSION}.exe" in notes


def test_wrapped_list_items_are_joined():
    text = "## [2.0.0] - 2026-02-02\n\n### Fixed\n- A long line\n  continued here.\n- Next.\n"
    assert release_notes.changelog_section(text, "2.0.0") == "### Fixed\n- A long line continued here.\n- Next."
