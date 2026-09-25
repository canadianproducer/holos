"""Пакет прискорення NVIDIA для розпізнавання (cuBLAS + cuDNN).

Встановлювач «Голосу» маленький і працює на будь-якому ПК. Якщо на комп'ютері є
відеокарта NVIDIA, при першому запуску докачуємо офіційні бібліотеки NVIDIA
(з PyPI, ті самі, що ставить pip) — і faster-whisper працює на відеокарті.
"""

import ctypes
import hashlib
import logging
import os
import shutil
import urllib.request
import zipfile

from common import MODELS

CUDA_DIR = MODELS / "cuda"
READY = CUDA_DIR / ".ready"

# Офіційні wheel-и NVIDIA з PyPI. URL і SHA-256 зафіксовані в коді: завантажений файл
# перевіряється до розпакування, тож підмінений чи пошкоджений архів не потрапить на диск.
# (пакет, версія, тека з DLL всередині wheel, розмір, sha256, url)
_PYPI = "https://files.pythonhosted.org/packages/"
PACKAGES = [
    (
        "nvidia-cuda-runtime-cu12",
        "12.9.79",
        "nvidia/cuda_runtime/bin/",
        3591604,
        "8e018af8fa02363876860388bd10ccb89eb9ab8fb0aa749aaf58430a9f7c4891",
        _PYPI + "59/df/e7c3a360be4f7b93cee39271b792669baeb3846c58a4df6dfcf187a7ffab/"
        "nvidia_cuda_runtime_cu12-12.9.79-py3-none-win_amd64.whl",
    ),
    (
        "nvidia-cublas-cu12",
        "12.9.2.10",
        "nvidia/cublas/bin/",
        553162896,
        "623f43027d40d44ceadf0043f002bd25cf353e8f13ce90b9a87057019f560661",
        _PYPI + "20/e2/fc9a0e985249d873150276d5afb02e39a66817fedbf1a385724393e505ed/"
        "nvidia_cublas_cu12-12.9.2.10-py3-none-win_amd64.whl",
    ),
    (
        "nvidia-cuda-nvrtc-cu12",
        "12.9.86",
        "nvidia/cuda_nvrtc/bin/",
        76408187,
        "72972ebdcf504d69462d3bcd67e7b81edd25d0fb85a2c46d3ea3517666636349",
        _PYPI + "52/de/823919be3b9d0ccbf1f784035423c5f18f4267fb0123558d58b813c6ec86/"
        "nvidia_cuda_nvrtc_cu12-12.9.86-py3-none-win_amd64.whl",
    ),
    (
        "nvidia-cudnn-cu12",
        "9.26.0.51",
        "nvidia/cudnn/bin/",
        746465599,
        "010abb90f513fc6e2b6e9278d56f594b87922fff80737434ab415da609db8311",
        _PYPI + "c5/ee/baebebf270df5a57830e40879b4016de47ca43961095cf18b7749452150f/"
        "nvidia_cudnn_cu12-9.26.0.51-py3-none-win_amd64.whl",
    ),
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


def _download(url, size, sha256, dest, progress_bytes):
    """Завантажує файл у dest, перевіряючи розмір і SHA-256. Невідповідність -> файл видаляється."""
    h, done = hashlib.sha256(), 0
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                progress_bytes(len(chunk))
        if done != size or h.hexdigest() != sha256:
            raise RuntimeError(f"{os.path.basename(url)}: контрольна сума не збігається — спробуйте ще раз")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise


def install(progress=lambda done_mb, total_mb: None):
    """Завантажує wheel-и NVIDIA, перевіряє SHA-256, витягує лише DLL. Можна перезапускати — докачає, що бракує."""
    CUDA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CUDA_DIR / "_download.whl"
    done = 0

    def advance(n):
        nonlocal done
        done += n
        progress(done / 1e6, APPROX_MB)

    for pkg, ver, inner, size, sha256, url in PACKAGES:
        marker = CUDA_DIR / f".{pkg}-{ver}"
        if marker.exists():
            advance(size)
            continue
        logging.info("CUDA: завантажую %s %s (%.0f МБ)", pkg, ver, size / 1e6)
        _download(url, size, sha256, tmp, advance)
        with zipfile.ZipFile(tmp) as z:
            for name in z.namelist():
                if name.startswith(inner) and name.lower().endswith(".dll"):
                    with z.open(name) as src, open(CUDA_DIR / os.path.basename(name), "wb") as dst:
                        shutil.copyfileobj(src, dst)
        tmp.unlink(missing_ok=True)
        marker.write_text("ok")
    READY.write_text("ok")
    logging.info("CUDA: пакет прискорення встановлено")
