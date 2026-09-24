"""Запис із мікрофона та розпізнавання мовлення (faster-whisper)."""
import collections
import logging
import re
import threading
import time

import numpy as np
import sounddevice as sd

from common import add_cuda_dll_dirs, pick_stt_device

SR = 16000
BLOCK = 480                # 30 мс
PREROLL_SEC = 0.6          # стільки звуку «до натискання» зберігаємо, коли мікрофон завжди відкритий
TAIL_SEC = 0.3             # дописуємо після відпускання, щоб не обрізати останнє слово

# Whisper на тиші/шумі іноді «вигадує» ці фрази — відкидаємо їх.
HALLUCINATIONS = [
    r"дякую за перегляд", r"дякуємо за перегляд", r"підписуйтесь на канал", r"спасибо за просмотр",
    r"продолжение следует", r"субтитры (сделал|создавал|делал)", r"редактор субтитров",
    r"thanks for watching", r"thank you for watching", r"subscribe to", r"amara\.org",
    r"^\W*$",
]
_HALL = re.compile("|".join(HALLUCINATIONS), re.I)

# Підказка задає стиль: розділові знаки, великі літери.
PROMPTS = {
    "uk": "Привіт. Ось текст українською мовою, з комами, крапками та знаками питання.",
    "ru": "Привет. Вот текст на русском языке, с запятыми, точками и вопросительными знаками.",
    "en": "Hello. Here is some text in English, with commas, periods, and question marks.",
}


class Recorder:
    def __init__(self, cfg):
        self.cfg = cfg
        self.level = 0.0
        self._frames = []
        self._pre = collections.deque(maxlen=int(PREROLL_SEC * SR / BLOCK))
        self._recording = False
        self._stream = None
        self._lock = threading.Lock()
        if cfg["mic_always_on"]:
            self._open()

    def _device(self):
        d = self.cfg["mic_device"]
        if isinstance(d, str) and d.isdigit():
            return int(d)
        return d

    def _open(self):
        if self._stream is None:
            self._stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=BLOCK,
                                          device=self._device(), callback=self._cb)
            self._stream.start()

    def _close(self):
        if self._stream is not None and not self.cfg["mic_always_on"]:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None

    def _cb(self, indata, frames, t, status):
        block = indata[:, 0].copy()
        self.level = float(np.sqrt(np.mean(block ** 2)))
        with self._lock:
            if self._recording:
                self._frames.append(block)
            else:
                self._pre.append(block)

    def start(self):
        with self._lock:
            self._frames = list(self._pre) if self.cfg["mic_always_on"] else []
            self._pre.clear()
            self._recording = True
        self._open()

    def stop(self, tail=True) -> np.ndarray:
        if tail:
            time.sleep(TAIL_SEC)
        with self._lock:
            self._recording = False
            frames, self._frames = self._frames, []
        self._close()
        self.level = 0.0
        return np.concatenate(frames) if frames else np.zeros(0, np.float32)

    @property
    def recording(self):
        return self._recording


class Transcriber:
    def __init__(self, cfg):
        self.cfg = cfg
        self.model = None
        self.device = None

    def load(self):
        add_cuda_dll_dirs()
        from faster_whisper import WhisperModel
        name = self.cfg["stt_model"]
        dev = pick_stt_device(self.cfg["stt_device"])
        t = time.time()
        try:
            self.model = WhisperModel(name, device=dev, compute_type="float16" if dev == "cuda" else "int8")
            # «Прогрів»: перший виклик повільний; на GPU він же перевіряє, що cuBLAS/cuDNN знайшлися.
            list(self.model.transcribe(np.zeros(SR, np.float32), language="uk")[0])
        except Exception as e:
            if dev != "cuda":
                raise
            logging.warning("Whisper на GPU не запустився (%s) — перемикаюсь на процесор", e)
            dev = "cpu"
            self.model = WhisperModel(name, device="cpu", compute_type="int8")
            list(self.model.transcribe(np.zeros(SR, np.float32), language="uk")[0])
        self.device = dev
        logging.info("Whisper %s завантажено на %s за %.1f с", name, dev, time.time() - t)

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size < SR * 0.3:
            return ""
        peak = float(np.max(np.abs(audio)))
        if peak < 0.003:
            logging.info("Тиша — пропускаю")
            return ""
        if peak < 0.3:  # тихий мікрофон — підсилюємо
            audio = audio * (0.5 / peak)
        lang = self.cfg["stt_language"]
        lang = None if lang == "auto" else lang
        # Підказка Whisper: стиль + словник термінів латиницею (GitHub, а не «гітхаб»).
        vocab = ", ".join(self.cfg["vocabulary"] or [])
        prompt = PROMPTS.get(lang, "") if lang else ""
        if vocab:
            prompt = (prompt + " " + vocab + ".").strip()
        t = time.time()
        segments, info = self.model.transcribe(
            audio, language=lang, beam_size=5, vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 700, "speech_pad_ms": 300},
            condition_on_previous_text=False,
            initial_prompt=prompt or None,
            without_timestamps=True,
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        logging.info("Розпізнано (%s, %.1f с аудіо, %.2f с): %s",
                     info.language, audio.size / SR, time.time() - t, text)
        return self.clean(text)

    def clean(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        if not text or (_HALL.search(text) and len(text) < 60):
            return ""
        for src, dst in (self.cfg["replacements"] or {}).items():
            text = re.sub(re.escape(src), dst, text, flags=re.I)
        text = re.sub(r"\s+([,.!?:;])", r"\1", text)
        return text
