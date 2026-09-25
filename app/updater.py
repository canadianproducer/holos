"""Оновлення через GitHub Releases: перевірка, завантаження з перевіркою SHA-256 і тихе встановлення."""

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import urllib.request

from common import VERSION

API = "https://api.github.com/repos/{repo}/releases/latest"
SUMS_NAME = "SHA256SUMS.txt"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class UpdateError(Exception):
    """Оновлення не можна безпечно встановити."""


def parse_version(v: str) -> tuple[int, ...]:
    """'v1.2.3' -> (1, 2, 3). Порівнюємо числа, а не рядки (0.10.0 > 0.9.0)."""
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def _is_installer(name: str) -> bool:
    n = name.lower()
    return n.startswith("holos-setup") and n.endswith(".exe")


def parse_release(data: dict, repo: str, current: str = VERSION) -> dict | None:
    """Відповідь GitHub API -> опис оновлення, або None, якщо новішої версії немає.

    sha256 береться з поля digest, яке GitHub рахує сам для кожного файлу релізу.
    Якщо його немає — з файлу SHA256SUMS.txt (sums_url), який докачує check().
    """
    tag = data.get("tag_name") or ""
    if data.get("draft") or data.get("prerelease") or parse_version(tag) <= parse_version(current):
        return None
    assets = data.get("assets") or []
    asset = next((a for a in assets if _is_installer(a.get("name", ""))), None)
    sums = next((a for a in assets if a.get("name") == SUMS_NAME), None)
    url = asset.get("browser_download_url") if asset else None
    if url and not url.startswith(f"https://github.com/{repo}/releases/download/"):
        logging.warning("Оновлення: неочікуване посилання на файл — ігнорую: %s", url)
        url = None
    digest = (asset or {}).get("digest") or ""
    sha256 = digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None
    return {
        "tag": tag,
        "page": data.get("html_url") or f"https://github.com/{repo}/releases/latest",
        "asset": url,
        "name": asset["name"] if asset else None,
        "size": int(asset.get("size") or 0) if asset else 0,
        "sha256": sha256 if sha256 and _HEX64.match(sha256) else None,
        "sums_url": sums.get("browser_download_url") if sums else None,
        "notes": (data.get("body") or "")[:600],
    }


def parse_sums(text: str, name: str) -> str | None:
    """Рядок формату `sha256sum`: '<hex>  <ім'я файлу>'."""
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1].lstrip("*") == name and _HEX64.match(parts[0].lower()):
            return parts[0].lower()
    return None


def _get(url: str, timeout: float, accept: str | None = None):
    if not url.startswith("https://"):
        raise UpdateError(f"Лише HTTPS: {url}")
    headers = {"User-Agent": f"Holos/{VERSION}"}
    if accept:
        headers["Accept"] = accept
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout)


def check(repo: str) -> dict | None:
    """Повертає опис оновлення, якщо на GitHub є новіша версія, інакше None. Ніколи не кидає винятків."""
    if not repo:
        return None
    try:
        with _get(API.format(repo=repo), 8, "application/vnd.github+json") as r:
            info = parse_release(json.loads(r.read().decode("utf-8")), repo)
        if info and info["asset"] and not info["sha256"] and info["sums_url"]:
            with _get(info["sums_url"], 15) as r:
                info["sha256"] = parse_sums(r.read(65536).decode("utf-8", "replace"), info["name"])
        return info
    except Exception as e:
        logging.info("Оновлення: перевірка не вдалася (%s)", e)
    return None


def download(info: dict, progress=lambda pct: None) -> str:
    """Завантажує інсталятор і перевіряє розмір та SHA-256. Без контрольної суми не встановлюємо."""
    if not info.get("sha256"):
        raise UpdateError("у релізі немає контрольної суми — оновіть вручну зі сторінки релізу")
    final = os.path.join(tempfile.gettempdir(), "Holos-Setup-update.exe")
    part = final + ".part"
    size, h, done = info.get("size") or 0, hashlib.sha256(), 0
    try:
        with _get(info["asset"], 60) as r, open(part, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if size:
                    progress(100 * done / size)
        if size and done != size:
            raise UpdateError(f"файл завантажено не повністю ({done} з {size} байт)")
        if h.hexdigest() != info["sha256"]:
            raise UpdateError("контрольна сума не збігається — файл пошкоджено або підмінено")
        os.replace(part, final)
        return final
    finally:
        if os.path.exists(part):
            os.remove(part)


def run_installer(path: str):
    """Тихе встановлення поверх старої версії; інсталятор сам перезапустить програму."""
    subprocess.Popen(
        [path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
        close_fds=True,
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
    )
