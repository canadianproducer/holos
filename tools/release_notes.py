"""Release page text: the version's CHANGELOG.md section plus short install instructions (EN + UK).

python tools/release_notes.py 0.4.0 notes.md
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FOOTER = """
---

**Install:** download `Holos-Setup-{version}.exe` below and run it. If Windows shows "Windows protected your PC",
click **More info → Run anyway**. On first launch the app downloads the speech models once (~3 GB).
An installed Holos offers the update by itself.

**Встановлення:** завантажте `Holos-Setup-{version}.exe` нижче й запустіть. Якщо Windows покаже «Windows захистила
ваш комп'ютер» — натисніть **«Докладніше» → «Однаково запустити»**. Під час першого запуску програма один раз
завантажить мовні моделі (~3 ГБ). Уже встановлений «Голос» запропонує оновлення сам.

Checksums: `SHA256SUMS.txt`. Full history: [CHANGELOG](https://github.com/canadianproducer/holos/blob/main/CHANGELOG.md).
Author: Oleksandr Potapenko (Canadian Producer). The code was written in pair with the AI assistant Claude.
"""


def changelog_section(text: str, version: str) -> str:
    """Body of the "## [version] ..." section up to the next "## [" heading."""
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, re.S | re.M)
    if not m:
        raise SystemExit(f"CHANGELOG.md has no section [{version}]")
    body = re.sub(r"^\[[^\]]+\]: .*$", "", m.group(1), flags=re.M)  # link definitions at the end of the file
    return body.strip()


def main(version: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return changelog_section(text, version) + "\n" + FOOTER.format(version=version)


if __name__ == "__main__":
    notes = main(sys.argv[1].lstrip("v"))
    if len(sys.argv) > 2:  # write UTF-8 regardless of the Windows console code page
        Path(sys.argv[2]).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(notes)
