"""Пакет прискорення NVIDIA для розпізнавання (cuBLAS + cuDNN).

Встановлювач «Голосу» маленький і працює на будь-якому ПК. Якщо на комп'ютері є
відеокарта NVIDIA, при першому запуску докачуємо офіційні бібліотеки NVIDIA
(з PyPI, ті самі, що ставить pip) — і faster-whisper працює на відеокарті.
"""

import ctypes
import json
import logging
import os
import shutil
import urllib.request
import zipfile

from common import MODELS

CUDA_DIR = MODELS / "cuda"
READY = CUDA_DIR / ".ready"

# (пакет, версія, тека з DLL всередині wheel)
PACKAGES = [
    ("nvidia-cuda-runtime-cu12", "12.9.79", "nvidia/cuda_runtime/bin/"),
    ("nvidia-cublas-cu12", "12.9.2.10", "nvidia/cublas/bin/"),
    ("nvidia-cuda-nvrtc-cu12", "12.9.86", "nvidia/cuda_nvrtc/bin/"),
    ("nvidia-cudnn-cu12", "9.26.0.51", "nvidia/cudnn/bin/"),
]
APPROX_MB = 1380


def has_nvidia() -> bool:
    """Чи є драйвер NVIDIA (nvcuda.dll ставиться разом із драйвером)."""
    if os.name != "nt":
        return False
    try:
        ctypes.WinDLL("nvcuda.dll")
        return True
    except OSError:
        return False


def installed() -> bool:
    return READY.exists()


def add_to_path():
    if installed() and os.name == "nt":
        os.add_dll_directory(str(CUDA_DIR))
        os.environ["PATH"] = str(CUDA_DIR) + os.pathsep + os.environ.get("PATH", "")


def _wheel_url(pkg, ver):
    with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/{ver}/json", timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    for u in data["urls"]:
        if u["filename"].endswith("win_amd64.whl"):
            return u["url"], u["size"]
    raise RuntimeError(f"{pkg} {ver}: немає збірки для Windows")


def install(progress=lambda done_mb, total_mb: None):
    """Завантажує wheel-и NVIDIA, витягує лише DLL. Можна перезапускати — докачає, що бракує."""
    CUDA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CUDA_DIR / "_download.whl"
    done = 0
    for pkg, ver, inner in PACKAGES:
        marker = CUDA_DIR / f".{pkg}-{ver}"
        url, size = _wheel_url(pkg, ver)
        if marker.exists():
            done += size
            progress(done / 1e6, APPROX_MB)
            continue
        logging.info("CUDA: завантажую %s %s (%.0f МБ)", pkg, ver, size / 1e6)
        with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                progress(done / 1e6, APPROX_MB)
        with zipfile.ZipFile(tmp) as z:
            for name in z.namelist():
                if name.startswith(inner) and name.lower().endswith(".dll"):
                    with z.open(name) as src, open(CUDA_DIR / os.path.basename(name), "wb") as dst:
                        shutil.copyfileobj(src, dst)
        tmp.unlink(missing_ok=True)
        marker.write_text("ok")
    READY.write_text("ok")
    logging.info("CUDA: пакет прискорення встановлено")
