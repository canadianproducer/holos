"""Оновлення через GitHub Releases: перевірка, завантаження і тихе встановлення нового Holos-Setup.exe."""
import json
import logging
import os
import re
import subprocess
import tempfile
import urllib.request

from common import VERSION


def _ver(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def check(repo: str):
    """Повертає {"tag", "page", "asset", "size", "notes"} якщо на GitHub є новіша версія, інакше None."""
    if not repo:
        return None
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                     headers={"Accept": "application/vnd.github+json",
                                              "User-Agent": f"Holos/{VERSION}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        if _ver(tag) <= _ver(VERSION):
            return None
        asset = next((a for a in data.get("assets", [])
                      if a["name"].lower().startswith("holos-setup") and a["name"].lower().endswith(".exe")), None)
        return {"tag": tag, "page": data.get("html_url") or f"https://github.com/{repo}/releases/latest",
                "asset": asset["browser_download_url"] if asset else None,
                "size": asset["size"] if asset else 0, "notes": (data.get("body") or "")[:600]}
    except Exception as e:
        logging.info("Оновлення: перевірка не вдалася (%s)", e)
    return None


def download(url, size, progress=lambda pct: None):
    path = os.path.join(tempfile.gettempdir(), "Holos-Setup-update.exe")
    req = urllib.request.Request(url, headers={"User-Agent": f"Holos/{VERSION}"})
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if size:
                progress(100 * done / size)
    return path


def run_installer(path):
    """Тихе встановлення поверх старої версії; інсталятор сам перезапустить програму."""
    subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
                     close_fds=True, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
