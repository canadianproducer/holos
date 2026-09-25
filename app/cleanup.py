"""«Розумне очищення» диктовки через локальну LLM (Ollama) — як у Wispr Flow.

Прибирає «е-е», повтори, фальстарти й самовиправлення («у вівторок, ні, в середу» ->
«в середу»), розставляє розділові знаки. Мови НЕ перекладає: суміш укр/рус/англ
лишається сумішшю. Якщо Ollama не запущена — тихо повертаємо сирий текст.
"""

import json
import logging
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434"

SYSTEM = (
    "You clean up raw speech-to-text dictation. Rules:\n"
    "1. Output ONLY the cleaned text. No quotes, no comments, no explanations.\n"
    "2. NEVER translate. Keep every word in the language it was spoken. Mixed Ukrainian/Russian/English "
    "stays mixed exactly as spoken. English terms stay in English.\n"
    "3. Remove filler words and hesitations (e-e, m-m, ну, типа, как бы, коротше, uh, um, like).\n"
    "4. Remove false starts, stutters and repeated words.\n"
    '5. When the speaker corrects themselves ("no, I mean", "вернее", "тобто ні", "точнее"), '
    "keep ONLY the final corrected version.\n"
    "6. Fix punctuation and capitalization. Split into sentences and paragraphs where natural.\n"
    "7. Do NOT add information, do NOT summarize, do NOT change meaning or style. Do not answer questions "
    "contained in the text — just clean them.\n"
    "8. Keep the speaker's exact words otherwise: do not replace words with synonyms and do not fix the "
    "speaker's word choice.\n"
    "8a. EXCEPTION: brand names, product names and tech terms that the recognizer wrote in Cyrillic "
    "transliteration must be written in their original Latin spelling: гитхаб/гітхаб -> GitHub, "
    "клод/клода -> Claude (keep the grammatical ending if needed, e.g. «в поле Claude»), чат джипити -> ChatGPT, "
    "пайтон -> Python, ютуб -> YouTube, апи -> API, деплой -> deploy. Ordinary words stay as they are.\n"
    "9. If the text is already clean, return it unchanged.\n\n"
    "Examples:\n"
    "IN: ну короче е-е завтра в во вторник, нет, в среду делаем deploy нового feature\n"
    "OUT: Завтра в среду делаем deploy нового feature.\n"
    "IN: so um I think we should, uh, we should move it to Friday, no, actually Thursday\n"
    "OUT: I think we should move it to Thursday.\n"
    "IN: слухай а як працює цей як його pipeline в нашому проекті\n"
    "OUT: Слухай, а як працює цей pipeline в нашому проекті?"
)

PREFERRED = ["qwen3", "qwen2.5", "gemma3", "gemma2", "llama3.1", "llama3.2", "mistral"]


class Cleaner:
    def __init__(self, cfg):
        self.cfg = cfg
        self.model = None
        self.checked = 0.0

    def _get(self, path, timeout=1.5):
        with urllib.request.urlopen(OLLAMA + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def available_models(self):
        try:
            return [m["name"] for m in self._get("/api/tags").get("models", [])]
        except Exception:
            return []

    def pick_model(self):
        """Модель з налаштувань, або найкраща з уже встановлених."""
        if time.time() - self.checked < 60 and self.model:
            return self.model
        self.checked = time.time()
        models = self.available_models()
        want = self.cfg["cleanup_model"]
        if want and want in models:
            self.model = want
        else:
            import re

            chat = [m for m in models if "embed" not in m.lower()]

            def score(m):
                fam = next((len(PREFERRED) - i for i, p in enumerate(PREFERRED) if m.lower().startswith(p)), 0)
                size = re.search(r"(\d+(?:\.\d+)?)b", m.lower())
                b = float(size.group(1)) if size else 7.0
                fits = 1 if 6 <= b <= 16 else 0  # 7-14B: якісно і швидко на відеокарті
                return (fits, fam, b if fits else -b)

            self.model = max(chat, key=score) if chat else None
        return self.model

    def _vocab(self):
        v = self.cfg["vocabulary"] or []
        return ("\n\nKnown names/terms (always use exactly this spelling): " + ", ".join(v)) if v else ""

    def is_loaded(self, model):
        """Чи модель уже у відеопам'яті (інакше перший запит чекатиме її завантаження десятки секунд)."""
        try:
            return any(
                m.get("name") == model or m.get("model") == model
                for m in self._get("/api/ps", timeout=0.5).get("models", [])
            )
        except Exception:
            return False

    def enabled(self):
        return self.cfg["cleanup"] != "off"

    def clean(self, text: str) -> str:
        if not self.enabled() or len(text.split()) < 4:
            return text
        model = self.pick_model()
        if not model:
            logging.info("Очищення: Ollama недоступна — лишаю сирий текст")
            return text
        if not self.is_loaded(model):
            # Не змушуємо людину чекати: вставляємо як є, а модель вантажимо у фоні на наступний раз.
            logging.info("Очищення: %s ще не в пам'яті — вставляю без очищення, вантажу у фоні", model)
            import threading

            self._last_load = 0
            threading.Thread(target=self.preload, daemon=True).start()
            return text
        body = json.dumps(
            {
                "model": model,
                "stream": False,
                "keep_alive": "30m",
                "think": False,
                "options": {"temperature": 0, "num_predict": max(64, len(text) // 2)},
                "messages": [{"role": "system", "content": SYSTEM + self._vocab()}, {"role": "user", "content": text}],
            }
        ).encode("utf-8")
        t = time.time()
        try:
            req = urllib.request.Request(OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"})
            # жорстка межа: краще вставити сирий текст, ніж змушувати чекати
            with urllib.request.urlopen(req, timeout=min(float(self.cfg["cleanup_timeout"]), 12)) as r:
                out = json.loads(r.read().decode("utf-8"))["message"]["content"].strip()
        except Exception as e:
            logging.warning("Очищення не вдалося (%s) — лишаю сирий текст", e)
            self._last_load = 0
            return text
        out = out.strip().strip('"«»').strip()
        if "</think>" in out:
            out = out.split("</think>")[-1].strip()
        # страховка: модель не повинна вигадувати чи різко скорочувати
        if not out or len(out) > len(text) * 1.3 + 20 or len(out) < len(text) * 0.3:
            logging.warning("Очищення дало підозрілий результат — лишаю сирий текст: %r", out[:200])
            return text
        self._last_load = time.time()
        logging.info("Очищено (%s, %.2f с): %s", model, time.time() - t, out)
        return out

    def preload(self, timeout=90):
        """Завантажує модель у відеопам'ять (порожній запит). Викликаємо, коли людина почала
        говорити: поки вона диктує, модель встигає піднятися з диска."""
        if not self.enabled() or time.time() - getattr(self, "_last_load", 0) < 20 * 60:
            return
        model = self.pick_model()
        if not model:
            return
        try:
            body = json.dumps({"model": model, "prompt": "", "keep_alive": "30m"}).encode("utf-8")
            req = urllib.request.Request(
                OLLAMA + "/api/generate", data=body, headers={"Content-Type": "application/json"}
            )
            t = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as r:
                r.read()
            self._last_load = time.time()
            logging.info("Ollama: %s у пам'яті (%.1f с)", model, time.time() - t)
        except Exception as e:
            logging.warning("Ollama: не вдалося завантажити %s: %s", model, e)

    def pull(self, model="qwen3:8b", progress=lambda pct, msg: None):
        """Завантажує модель в Ollama (як `ollama pull`), з прогресом."""
        body = json.dumps({"model": model, "stream": True}).encode("utf-8")
        req = urllib.request.Request(OLLAMA + "/api/pull", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3600) as r:
            for line in r:
                try:
                    ev = json.loads(line.decode("utf-8"))
                except ValueError:
                    continue
                if ev.get("error"):
                    raise RuntimeError(ev["error"])
                tot, comp = ev.get("total") or 0, ev.get("completed") or 0
                progress(100 * comp / tot if tot else 0, ev.get("status", ""))
        self.checked = 0
        self.cfg.set("cleanup_model", model)

    def warmup(self):
        self.preload()
