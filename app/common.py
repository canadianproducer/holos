"""Шляхи, налаштування, журнал. Імпортується ПЕРШИМ — задає теки для моделей."""
import json
import logging
import os
import sys
import threading
from pathlib import Path

VERSION = "0.3.1"
FROZEN = getattr(sys, "frozen", False)
# У віконному exe немає консолі: stdout/stderr = None, і бібліотеки (tqdm тощо) падають при друку.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
# Тека програми: поруч із Holos.exe (зібрана версія) або корінь проєкту (запуск з коду).
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent.parent
# Ресурси (іконка): у зібраному exe — всередині _internal.
RES_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)) / "assets"
# Тека даних (моделі, налаштування, журнали):
#  - портативний режим: файл portable.txt поруч із exe -> все поруч з програмою (флешка, копіювання теки);
#  - інакше %LOCALAPPDATA%\Holos (Program Files недоступна для запису).
_portable = APP_DIR / "portable.txt"
if _portable.exists():
    # portable.txt порожній -> дані поруч із exe; або містить шлях до теки даних
    _p = _portable.read_text(encoding="utf-8-sig").strip()
    ROOT = Path(_p) if _p else APP_DIR
elif not FROZEN:
    ROOT = APP_DIR
else:
    ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Holos"
ROOT.mkdir(parents=True, exist_ok=True)
MODELS = ROOT / "models"
LOGS = ROOT / "logs"
CONFIG_PATH = ROOT / "config.json"
HISTORY_PATH = ROOT / "logs" / "history.txt"
READY_FLAG = MODELS / ".ready"
VOICES_DIR = MODELS / "voices"
PIPER_DIR = MODELS / "piper"

MODELS.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

# Усі моделі живуть у теці програми -> тека переноситься на інший ПК разом з ними.
os.environ.setdefault("HF_HOME", str(MODELS / "hf"))
os.environ.setdefault("STANZA_RESOURCES_DIR", str(MODELS / "stanza"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
if READY_FLAG.exists() and "--online" not in sys.argv:
    # Після встановлення працюємо повністю офлайн.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

DEFAULTS = {
    # --- Гарячі клавіші ---
    # Диктування: утримуйте й говоріть (відпустили -> вставка).
    # Коротке натискання = режим «увімкнув/вимкнув».
    "dictate_hotkey": "right ctrl",
    # Читання виділеного тексту. Повторне натискання або Esc — стоп.
    "read_hotkey": "ctrl+shift+space",

    # --- Розпізнавання (faster-whisper) ---
    "stt_model": "large-v3-turbo",
    "stt_device": "auto",            # auto | cuda | cpu
    "stt_language": "auto",          # auto | uk | ru | en
    "mic_always_on": False,          # True = мікрофон відкритий завжди (жодне слово не обріжеться)
    "mic_device": None,              # None = системний за замовчуванням, або назва/номер пристрою
    "replacements": {},
    # Слова, які треба писати латиницею / як є (бренди, терміни, імена). Допомагає і Whisper, і очищенню.
    "vocabulary": ["Claude", "ChatGPT", "GitHub", "Python", "API", "Windows", "YouTube", "Instagram",
                   "Threads", "Ollama", "Whisper", "ElevenLabs", "Higgsfield", "Canadian Producer",
                   "UkraineInfo"],              # {"кома": ","} — власні заміни після розпізнавання
    "restore_clipboard": True,
    # «Розумне очищення» через локальну Ollama: auto (якщо Ollama запущена) | off
    "cleanup": "auto",
    "cleanup_model": "",             # порожньо = обрати автоматично з встановлених
    "cleanup_timeout": 12,

    # --- Читання ---
    "tts_device": "auto",            # auto | cuda | cpu
    "uk_voice": "Марина Панас",
    "ru_voice": "female",            # female | male
    "en_voice": "female",
    "default_cyrillic": "uk",        # якою мовою читати кирилицю без явних ознак (uk/ru)
    "speed": 1.0,
    "verbalize_numbers": True,       # «1890 року» -> «тисяча вісімсот дев'яностого року»

    # --- Оновлення: репозиторій GitHub з релізами ("owner/repo"), порожньо = не перевіряти ---
    "update_repo": "canadianproducer/holos",

    # --- Інтерфейс ---
    "sounds": True,
    "overlay_position": "bottom",    # bottom | top
}

PIPER_VOICES = {
    ("ru", "female"): "ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx",
    ("ru", "male"): "ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx",
    ("en", "female"): "en/en_US/amy/medium/en_US-amy-medium.onnx",
    ("en", "male"): "en/en_US/ryan/medium/en_US-ryan-medium.onnx",
}

STYLETTS_REPO = "patriotyk/styletts2_ukrainian_multispeaker"
STYLETTS_VOICES_SPACE = "patriotyk/styletts2-ukrainian"
VERBALIZER_MODEL = "skypro1111/m2m100-ukr-verbalization-ct2"
VERBALIZER_TOKENIZER = "skypro1111/m2m100-ukr-verbalization"


class Config:
    def __init__(self):
        self._lock = threading.Lock()
        self.data = dict(DEFAULTS)
        if CONFIG_PATH.exists():
            try:
                self.data.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
            except Exception as e:  # зіпсований файл не повинен ламати запуск
                logging.error("config.json не читається (%s) — використовую стандартні", e)
        self.save()

    def __getitem__(self, k):
        return self.data.get(k, DEFAULTS.get(k))

    def set(self, k, v):
        with self._lock:
            self.data[k] = v
            self.save()

    def save(self):
        CONFIG_PATH.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")


def setup_logging():
    fmt = "%(asctime)s %(levelname)s %(threadName)s: %(message)s"
    handlers = [logging.FileHandler(LOGS / "holos.log", encoding="utf-8")]
    if sys.stdout is not None and not FROZEN:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers, force=True)
    for noisy in ("stanza", "urllib3", "httpx", "huggingface_hub", "faster_whisper", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    def hook(exc_type, exc, tb):
        logging.critical("Необроблена помилка", exc_info=(exc_type, exc, tb))
    sys.excepthook = hook
    threading.excepthook = lambda a: logging.critical(
        "Помилка в потоці %s", a.thread.name if a.thread else "?",
        exc_info=(a.exc_type, a.exc_value, a.exc_traceback))


def add_cuda_dll_dirs():
    """ctranslate2 (faster-whisper) на Windows шукає cuBLAS/cuDNN. Вони вже є в torch\\lib."""
    if os.name != "nt":
        return
    try:
        import cuda_pack
        cuda_pack.add_to_path()          # пакет прискорення, докачаний при першому запуску
    except Exception as e:
        logging.warning("cuda_pack: %s", e)
    try:
        import torch  # noqa: F401
        lib = Path(torch.__file__).parent / "lib"
        if lib.exists():
            os.add_dll_directory(str(lib))
            os.environ["PATH"] = str(lib) + os.pathsep + os.environ.get("PATH", "")
    except Exception as e:
        logging.warning("torch\\lib не додано: %s", e)


def cuda_libs_available() -> bool:
    """cuBLAS і cuDNN є або в пакеті прискорення, або в CUDA-збірці torch."""
    dirs = [MODELS / "cuda"]
    try:
        import importlib.util
        spec = importlib.util.find_spec("torch")
        if spec and spec.origin:
            dirs.append(Path(spec.origin).parent / "lib")
    except Exception:
        pass
    return any((d / "cudnn64_9.dll").exists() and (d / "cublas64_12.dll").exists() for d in dirs)


def pick_stt_device(pref: str) -> str:
    """Для faster-whisper питаємо саму ctranslate2 (не залежить від того, CPU чи CUDA-збірка torch)."""
    if pref in ("cuda", "cpu"):
        return pref
    if not cuda_libs_available():
        return "cpu"   # без cuDNN ctranslate2 може аварійно закрити програму — не ризикуємо
    try:
        import ctranslate2
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


def pick_device(pref: str) -> str:
    if pref in ("cuda", "cpu"):
        return pref
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
