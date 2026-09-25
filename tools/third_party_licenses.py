"""Список сторонніх Python-пакетів у збірці з їхніми ліцензіями (для THIRD_PARTY_LICENSES.md у теці програми).

Запускається інтерпретатором середовища збірки (build.bat):
    python tools/third_party_licenses.py > dist/Holos/THIRD_PARTY_LICENSES.md
"""

import sys
from importlib.metadata import distributions

# Інструменти збірки — у програму не потрапляють
BUILD_ONLY = {
    "pyinstaller",
    "pyinstaller-hooks-contrib",
    "altgraph",
    "pefile",
    "pywin32-ctypes",
    "pip",
    "setuptools",
    "wheel",
}


def license_of(meta) -> str:
    if meta.get("License-Expression"):
        return meta["License-Expression"]
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return ", ".join(classifiers)
    lic = (meta.get("License") or "").strip().splitlines()
    return lic[0][:60] if lic else "див. сторінку проєкту"


def main() -> str:
    rows = {}
    for d in distributions():
        name = d.metadata["Name"]
        if not name or name.lower().replace("_", "-") in BUILD_ONLY:
            continue
        url = d.metadata.get("Home-page") or next(
            (u.split(",", 1)[1].strip() for u in d.metadata.get_all("Project-URL") or [] if "," in u), ""
        )
        rows[name.lower()] = (name, d.version, license_of(d.metadata), url)
    out = [
        "# Сторонні компоненти «Голосу»",
        "",
        "Пакети Python, що входять у цю збірку. Повні тексти ліцензій — на сторінках проєктів.",
        "Моделі й голоси — див. THIRD_PARTY_NOTICES.md у репозиторії.",
        "",
        "| Пакет | Версія | Ліцензія | Сайт |",
        "|---|---|---|---|",
    ]
    out += [f"| {n} | {v} | {lic} | {u} |" for n, v, lic, u in (rows[k] for k in sorted(rows))]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(main(), end="")
