"""Завантаження моделей у теку даних (один раз, при першому запуску)."""
import logging
import shutil
import sys
from pathlib import Path

import common  # noqa: F401
from common import (
    PIPER_DIR,
    PIPER_VOICES,
    READY_FLAG,
    STYLETTS_REPO,
    STYLETTS_VOICES_SPACE,
    VERBALIZER_MODEL,
    VERBALIZER_TOKENIZER,
    VOICES_DIR,
    Config,
)

STEPS = [
    "Розпізнавання мовлення (Whisper, ~1.6 ГБ)",
    "Український голос (StyleTTS2, ~0.7 ГБ)",
    "Набір українських голосів",
    "Наголоси української мови",
    "Російські та англійські голоси (Piper)",
    "Вимова чисел (~0.5 ГБ)",
]


def download_all(progress=lambda i, n, msg: print(f"[{i}/{n}] {msg}", flush=True)):
    from huggingface_hub import hf_hub_download, snapshot_download
    cfg = Config()
    n = len(STEPS)

    progress(1, n, STEPS[0])
    from faster_whisper import download_model
    download_model(cfg["stt_model"])

    progress(2, n, STEPS[1])
    snapshot_download(STYLETTS_REPO)

    progress(3, n, STEPS[2])
    space = snapshot_download(STYLETTS_VOICES_SPACE, repo_type="space", allow_patterns=["voices/*.pt"])
    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    for p in Path(space, "voices").glob("*.pt"):
        shutil.copy(p, VOICES_DIR / p.name)

    progress(4, n, STEPS[3])
    from ukrainian_word_stress import Stressifier
    Stressifier()  # саме скачує дані stanza

    progress(5, n, STEPS[4])
    PIPER_DIR.mkdir(parents=True, exist_ok=True)
    for rel in PIPER_VOICES.values():
        for suffix in ("", ".json"):
            f = hf_hub_download("rhasspy/piper-voices", rel + suffix)
            shutil.copy(f, PIPER_DIR / Path(rel + suffix).name)

    progress(6, n, STEPS[5])
    try:
        snapshot_download(VERBALIZER_MODEL, allow_patterns=["*.bin", "*.json", "*.txt", "*.model"])
        snapshot_download(VERBALIZER_TOKENIZER, allow_patterns=["*.json", "*.txt", "*.model"])
    except Exception as e:
        logging.warning("Вербалізатор пропущено: %s", e)

    READY_FLAG.write_text("ok")
    progress(n, n, "Готово")


if __name__ == "__main__":
    try:
        download_all()
    except Exception as e:
        print("\nПОМИЛКА:", e)
        sys.exit(1)
