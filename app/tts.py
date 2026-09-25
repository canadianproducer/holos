"""Озвучення: українська — StyleTTS2 (patriotyk), російська/англійська — Piper."""

import logging
import queue
import re
import threading
import time
from unicodedata import normalize

import numpy as np
import sounddevice as sd

from common import (
    PIPER_DIR,
    PIPER_VOICES,
    STYLETTS_REPO,
    VERBALIZER_MODEL,
    VERBALIZER_TOKENIZER,
    VOICES_DIR,
    pick_device,
)

UK_SR = 24000


def list_uk_voices():
    return sorted(p.stem for p in VOICES_DIR.glob("*.pt"))


def detect_lang(text: str, default_cyr="uk"):
    uk = len(re.findall(r"[іїєґІЇЄҐ]", text))
    ru = len(re.findall(r"[ыэъёЫЭЪЁ]", text))
    cyr = len(re.findall(r"[а-яА-ЯіїєґІЇЄҐёЁ]", text))
    lat = len(re.findall(r"[a-zA-Z]", text))
    if cyr == 0 and lat == 0:
        return None
    if lat > cyr:
        return "en"
    if uk > ru:
        return "uk"
    if ru > uk:
        return "ru"
    return default_cyr


def split_sentences(text: str, max_len=220):
    """Ріже текст на речення; дуже короткі склеює, задовгі ріже по комах
    (StyleTTS2 гірше звучить на довгих шматках)."""
    text = re.sub(r"\s+", " ", text).strip()
    parts = [p for p in re.split(r"(?<=[.!?…])\s+(?=[«\"(\[]?[A-ZА-ЯІЇЄҐЁ0-9])", text) if p]
    merged = []
    for p in parts:
        if merged and len(merged[-1]) < 25 and len(merged[-1]) + len(p) < max_len:
            merged[-1] += " " + p
        else:
            merged.append(p)
    out = []
    for p in merged:
        while len(p) > max_len:
            cut = max(p.rfind(sep, 0, max_len) for sep in (", ", "; ", " — ", ": "))
            if cut < 40:
                cut = p.rfind(" ", 0, max_len)
            if cut < 1:
                break
            out.append(p[: cut + 1].strip())
            p = p[cut + 1 :].strip()
        if p:
            out.append(p)
    return out


class Verbalizer:
    """Цифри -> слова з правильним відмінком (модель skypro1111)."""

    def __init__(self):
        import ctranslate2
        from huggingface_hub import snapshot_download
        from transformers import M2M100Tokenizer

        path = snapshot_download(VERBALIZER_MODEL, allow_patterns=["*.bin", "*.json", "*.txt", "*.model"])
        self.tr = ctranslate2.Translator(path, device="cpu", compute_type="int8")
        self.tok = M2M100Tokenizer.from_pretrained(VERBALIZER_TOKENIZER)
        self.tok.src_lang = "uk"

    def __call__(self, text: str) -> str:
        src = self.tok.convert_ids_to_tokens(self.tok.encode(text))
        res = self.tr.translate_batch(
            [src], target_prefix=[[self.tok.lang_code_to_token["uk"]]], beam_size=1, max_decoding_length=512
        )
        out = self.tok.decode(self.tok.convert_tokens_to_ids(res[0].hypotheses[0][1:]))
        return out or text


class UkEngine:
    def __init__(self, device):
        import torch
        from ipa_uk import ipa
        from styletts2_inference.models import StyleTTS2
        from ukrainian_word_stress import Stressifier, StressSymbol

        self.torch = torch
        self.ipa = ipa
        self.acute = StressSymbol.CombiningAcuteAccent
        self.stressify = Stressifier()
        self.device = device
        self.model = StyleTTS2(hf_path=STYLETTS_REPO, device=device)
        self.voices = {p.stem: torch.load(p, map_location=device) for p in VOICES_DIR.glob("*.pt")}
        if not self.voices:
            raise RuntimeError(
                "Немає українських голосів у models/voices — запустіть «Голос» з параметром --download або перевстановіть"
            )

    def synth(self, text, voice, speed):
        t = text.strip().replace('"', "").replace("«", "").replace("»", "")
        t = t.replace("+", self.acute)  # «Му+дрого» — ручний наголос
        t = normalize("NFKC", t)
        t = re.sub(r"[᠆‐‑‒–—―⁻₋−⸺⸻]", "-", t)
        if t and t[-1] not in ".?!:-…":
            t += "."
        t = re.sub(r" - ", ": ", t)
        ps = self.ipa(self.stressify(t))
        if not ps:
            return None
        style = self.voices[voice] if voice in self.voices else next(iter(self.voices.values()))
        with self.torch.inference_mode():
            wav = self.model(self.model.tokenizer.encode(ps), speed=speed, s_prev=style)
        return wav.float().cpu().numpy()


class PiperEngine:
    def __init__(self):
        self.cache = {}

    def voice(self, lang, gender):
        key = (lang, gender)
        if key not in self.cache:
            from piper import PiperVoice

            rel = PIPER_VOICES[key]
            self.cache[key] = PiperVoice.load(str(PIPER_DIR / rel.split("/")[-1]))
        return self.cache[key]

    def synth(self, text, lang, gender, speed):
        from piper import SynthesisConfig

        v = self.voice(lang, gender)
        cfg = SynthesisConfig(length_scale=1.0 / max(speed, 0.5))
        chunks = [c.audio_float_array for c in v.synthesize(text, syn_config=cfg)]
        if not chunks:
            return None, v.config.sample_rate
        return np.concatenate(chunks).astype(np.float32), v.config.sample_rate


class Speaker:
    """Синтезує речення в одному потоці й одразу програє в іншому — звук починається за 1-2 с."""

    def __init__(self, cfg, on_state):
        self.cfg = cfg
        self.on_state = on_state
        self.uk = None
        self.piper = PiperEngine()
        self.verbalizer = None
        self._verb_failed = False
        self._stop = threading.Event()
        self._busy = threading.Event()
        self._load_lock = threading.Lock()

    @property
    def speaking(self):
        return self._busy.is_set()

    def load_uk(self):
        with self._load_lock:
            if self.uk is None:
                t = time.time()
                dev = pick_device(self.cfg["tts_device"])
                self.uk = UkEngine(dev)
                # прогрів
                self.uk.synth("Привіт.", self.cfg["uk_voice"], 1.0)
                logging.info("StyleTTS2 завантажено на %s за %.1f с", dev, time.time() - t)

    def _verbalize(self, text):
        if not self.cfg["verbalize_numbers"] or self._verb_failed or not re.search(r"\d", text):
            return text
        try:
            if self.verbalizer is None:
                self.verbalizer = Verbalizer()
            return self.verbalizer(text)
        except Exception as e:
            logging.warning("Вербалізатор недоступний: %s", e)
            self._verb_failed = True
            return text

    def stop(self):
        self._stop.set()
        try:
            sd.stop()
        except Exception:
            pass

    def speak(self, text: str):
        if self.speaking:
            self.stop()
            return
        self._stop.clear()
        self._busy.set()
        threading.Thread(target=self._run, args=(text,), name="speak", daemon=True).start()

    def _run(self, text):
        q = queue.Queue(maxsize=4)
        player = threading.Thread(target=self._play, args=(q,), name="player", daemon=True)
        player.start()
        try:
            self.on_state("speaking")
            speed = float(self.cfg["speed"])
            for para in [p for p in re.split(r"\n\s*\n|\r?\n", text) if p.strip()]:
                lang = detect_lang(para, self.cfg["default_cyrillic"])
                if lang is None:
                    continue
                for sent in split_sentences(para):
                    if self._stop.is_set():
                        return
                    audio, sr = self._synth(sent, lang, speed)
                    if audio is not None and audio.size:
                        q.put((audio, sr))
        except Exception:
            logging.exception("Помилка озвучення")
            self.on_state("error", "Помилка озвучення — див. logs/holos.log")
        finally:
            q.put(None)
            player.join()
            self._busy.clear()
            self.on_state("idle")

    def _synth(self, sent, lang, speed):
        t = time.time()
        if lang == "uk":
            if self.uk is None:
                self.on_state("loading", "Завантажую голос…")
                self.load_uk()
                self.on_state("speaking")
            a = self.uk.synth(self._verbalize(sent), self.cfg["uk_voice"], speed)
            sr = UK_SR
        else:
            gender = self.cfg["ru_voice" if lang == "ru" else "en_voice"]
            a, sr = self.piper.synth(sent, lang, gender, speed)
        if a is not None:
            peak = float(np.max(np.abs(a))) or 1.0
            a = (a / peak * 0.9).astype(np.float32)
            a = np.concatenate([a, np.zeros(int(sr * 0.12), np.float32)])  # пауза між реченнями
        logging.debug("synth %s %.2fs: %s", lang, time.time() - t, sent[:60])
        return a, sr

    def _play(self, q):
        while True:
            item = q.get()
            if item is None or self._stop.is_set():
                if item is not None:
                    continue  # дочитуємо чергу, щоб синтезатор не завис на put()
                return
            audio, sr = item
            sd.play(audio, sr)
            sd.wait()
