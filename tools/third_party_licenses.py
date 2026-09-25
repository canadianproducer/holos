"""Lists the third-party Python packages in a build with their licenses (THIRD_PARTY_LICENSES.md in the app folder).

Run with the build environment's interpreter (build.bat):
    python tools/third_party_licenses.py > dist/Holos/THIRD_PARTY_LICENSES.md
"""

import sys
from importlib.metadata import distributions

# Build tools — not shipped with the app
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
    return lic[0][:60] if lic else "see project page"


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
        "# Holos third-party components",
        "",
        "Python packages included in this build. Full license texts are on the project pages.",
        "Models and voices: see THIRD_PARTY_NOTICES.md.",
        "",
        "| Package | Version | License | Homepage |",
        "|---|---|---|---|",
    ]
    out += [f"| {n} | {v} | {lic} | {u} |" for n, v, lic, u in (rows[k] for k in sorted(rows))]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(main(), end="")
