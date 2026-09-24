"""Перевірка оновлень через GitHub Releases (без токенів: публічний репозиторій з релізами)."""
import json
import logging
import re
import urllib.request

from common import VERSION


def _ver(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def check(repo: str):
    """Повертає (версія, url) якщо є новіша, інакше None."""
    if not repo:
        return None
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                     headers={"Accept": "application/vnd.github+json",
                                              "User-Agent": f"Holos/{VERSION}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        if _ver(tag) > _ver(VERSION):
            return tag, data.get("html_url") or f"https://github.com/{repo}/releases/latest"
    except Exception as e:
        logging.info("Оновлення: перевірка не вдалася (%s)", e)
    return None
