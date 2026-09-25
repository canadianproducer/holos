"""Текст сторінки релізу: розділ версії з CHANGELOG.md + коротка інструкція встановлення.

python tools/release_notes.py 0.4.0 notes.md
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FOOTER = """
---

**Як встановити:** завантажте `Holos-Setup-{version}.exe` нижче й запустіть. Якщо Windows покаже синє вікно
«Windows захистила ваш комп'ютер» — натисніть «Докладніше» → «Однаково запустити».
Під час першого запуску програма один раз завантажить мовні моделі (~3 ГБ).
Уже встановлений «Голос» запропонує оновлення сам.

Контрольні суми — у `SHA256SUMS.txt`. Повний список змін — [CHANGELOG](https://github.com/canadianproducer/holos/blob/main/CHANGELOG.md).

Автор — Oleksandr Potapenko (Canadian Producer). Код написано в парі з AI-асистентом Claude.
"""


def changelog_section(text: str, version: str) -> str:
    """Вміст розділу «## [version] …» до наступного розділу «## [»."""
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.S | re.M)
    if not m:
        raise SystemExit(f"CHANGELOG.md: немає розділу [{version}]")
    body = re.sub(r"^\[[^\]]+\]: .*$", "", m.group(1), flags=re.M)  # посилання внизу файлу
    return body.strip()


def main(version: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return changelog_section(text, version) + "\n" + FOOTER.format(version=version)


if __name__ == "__main__":
    notes = main(sys.argv[1].lstrip("v"))
    if len(sys.argv) > 2:  # у файл — завжди UTF-8, незалежно від кодування консолі Windows
        Path(sys.argv[2]).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(notes)
