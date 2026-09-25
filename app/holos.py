"""Голос — диктування і читання вслух для Windows. Точка входу."""

import io
import logging
import math
import os
import queue
import struct
import sys
import threading
import time
import tkinter as tk
import wave

import common  # noqa: F401  (до будь-яких ML-бібліотек: задає теки моделей і змінні HF_*)
import winutil
from common import (
    CONFIG_PATH,
    HISTORY_PATH,
    LOGS,
    READY_FLAG,
    RES_DIR,
    ROOT,
    VERSION,
    Config,
    append_history,
    setup_logging,
)

setup_logging()
log = logging.getLogger("holos")

# (заголовок, підказка під ним). {key} замінюється на клавішу диктування.
STATE_TEXT = {
    "listening": ("Слухаю…", "відпустіть {key} — вставлю текст"),
    "listening_toggle": ("Слухаю…", "{key} — готово  ·  Esc — скасувати"),
    "processing": ("Розпізнаю…", ""),
    "speaking": ("Читаю…", "Esc — зупинити"),
    "loading": ("Завантаження…", ""),
    "error": ("", ""),
}
KEY_NAMES = {
    "right ctrl": "правий Ctrl",
    "right alt": "правий Alt",
    "ctrl": "Ctrl",
    "shift": "Shift",
    "alt": "Alt",
    "space": "Пробіл",
    "win": "Win",
}
COLORS = {
    "key": "#1e1e23",
    "bg": "#26262d",
    "border": "#3a3a44",
    "fg": "#f2f2f2",
    "hint": "#9a9aa6",
    "rec": "#ff4d4f",
    "busy": "#f5b301",
    "play": "#3fb68b",
    "err": "#ff7a45",
}


def key_label(combo: str) -> str:
    return "+".join(
        KEY_NAMES.get(k.strip().lower(), k.strip().upper() if len(k.strip()) == 1 else k.strip())
        for k in combo.split("+")
    )


def _tone(freqs, dur=0.07, vol=0.25, sr=22050):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = b""
        for f in freqs:
            n = int(sr * dur)
            for i in range(n):
                env = min(1, i / 200, (n - i) / 200)
                frames += struct.pack("<h", int(32767 * vol * env * math.sin(2 * math.pi * f * i / sr)))
        w.writeframes(frames)
    return buf.getvalue()


def _tone_file(name, data):
    p = LOGS.parent / f".{name}.wav"
    try:
        p.write_bytes(data)
    except Exception:
        pass
    return str(p)


# winsound не вміє грати асинхронно з пам'яті -> тримаємо короткі wav-файли в теці даних
SND_START = _tone_file("start", _tone([660, 880]))
SND_STOP = _tone_file("stop", _tone([880, 660]))
SND_ERR = _tone_file("err", _tone([300, 220], 0.12))


def play_sound(path, cfg):
    """Звук-підказка. Ніколи не кидає помилок: звук не має права ламати диктування."""
    if not cfg["sounds"] or os.name != "nt":
        return
    try:
        import winsound

        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception as e:
        log.debug("звук: %s", e)


class Overlay:
    """Округла плашка внизу екрана. Не забирає фокус і пропускає кліки.
    Кути робимо через «прозорий колір» вікна: усе, що має колір COLORS['key'], не малюється."""

    W, H, R = 440, 58, 22
    WAVE_W = 96  # праворуч — окрема зона під хвилю, текст її не перетинає

    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=COLORS["key"])
        if os.name == "nt":
            self.win.attributes("-transparentcolor", COLORS["key"])
        self.cv = tk.Canvas(self.win, width=self.W, height=self.H, bg=COLORS["key"], highlightthickness=0)
        self.cv.pack()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        y = 24 if cfg["overlay_position"] == "top" else sh - self.H - 64
        self.win.geometry(f"{self.W}x{self.H}+{(sw - self.W) // 2}+{y}")
        self.win.update_idletasks()
        self.hwnd = int(self.win.wm_frame(), 16) if os.name == "nt" else None
        winutil.make_overlay(self.hwnd)
        self.win.attributes("-alpha", 0.96)
        self.visible = True
        self.hide()
        self.levels = [0.0] * 16

    def show(self):
        if not self.visible:
            if self.hwnd:
                winutil.show_no_activate(self.hwnd, True)
            else:
                self.win.deiconify()
            self.visible = True

    def hide(self):
        if self.visible:
            if self.hwnd:
                winutil.show_no_activate(self.hwnd, False)
            else:
                self.win.withdraw()
            self.visible = False

    def _pill(self, x0, y0, x1, y1, r, **kw):
        pts = [
            x0 + r,
            y0,
            x1 - r,
            y0,
            x1,
            y0,
            x1,
            y0 + r,
            x1,
            y1 - r,
            x1,
            y1,
            x1 - r,
            y1,
            x0 + r,
            y1,
            x0,
            y1,
            x0,
            y1 - r,
            x0,
            y0 + r,
            x0,
            y0,
        ]
        return self.cv.create_polygon(pts, smooth=True, splinesteps=24, **kw)

    def draw(self, state, title, hint, level):
        cv, W, H = self.cv, self.W, self.H
        cv.delete("all")
        self._pill(1, 1, W - 2, H - 2, self.R, fill=COLORS["bg"], outline=COLORS["border"], width=1)
        color = {
            "listening": COLORS["rec"],
            "listening_toggle": COLORS["rec"],
            "processing": COLORS["busy"],
            "loading": COLORS["busy"],
            "speaking": COLORS["play"],
            "error": COLORS["err"],
        }.get(state, COLORS["fg"])
        pulse = 0.5 + 0.5 * math.sin(time.time() * 6)
        r = 6 + (2 * pulse if state in ("processing", "loading", "listening", "listening_toggle") else 0)
        cx, cy = 26, H // 2
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")
        listening = state.startswith("listening")
        text_w = W - 50 - (self.WAVE_W + 16 if listening else 16)
        if hint:
            cv.create_text(
                46, cy - 9, text=title, fill=COLORS["fg"], anchor="w", width=text_w, font=("Segoe UI Semibold", 11)
            )
            cv.create_text(46, cy + 11, text=hint, fill=COLORS["hint"], anchor="w", width=text_w, font=("Segoe UI", 9))
        else:
            cv.create_text(
                46, cy, text=title, fill=COLORS["fg"], anchor="w", width=text_w, font=("Segoe UI Semibold", 11)
            )
        if listening:
            self.levels = self.levels[1:] + [min(1.0, level * 12)]
            x0 = W - self.WAVE_W - 18
            for i, v in enumerate(self.levels):
                x = x0 + i * 6
                h = 4 + v * (H - 26)
                cv.create_line(x, cy - h / 2, x, cy + h / 2, fill=COLORS["rec"], width=3, capstyle="round")


class App:
    def __init__(self):
        self.cfg = Config()
        self.events = queue.Queue()  # (state, text) для інтерфейсу
        self.state, self.state_text, self.state_hint = "loading", "Завантаження…", ""
        self.error_until = 0
        self.last_text = ""
        self.target_hwnd = None
        self.toggle_mode = False
        self.rec_started = 0.0
        self.ready = threading.Event()
        self.stt_lock = threading.Lock()

        self.root = tk.Tk()
        self.root.withdraw()
        self.overlay = Overlay(self.root, self.cfg)

        from stt import Recorder, Transcriber
        from tts import Speaker

        self.recorder = Recorder(self.cfg)
        self.transcriber = Transcriber(self.cfg)
        self.speaker = Speaker(self.cfg, self.set_state)
        from cleanup import Cleaner

        self.cleaner = Cleaner(self.cfg)

        from hotkeys import HotkeyManager

        self.hk = HotkeyManager()
        self.hk.esc_callback = self.on_esc
        self.hk.add(self.cfg["dictate_hotkey"], self.on_dictate_down, self.on_dictate_up)
        self.hk.add(self.cfg["read_hotkey"], None, self.on_read)

        self.tray = None
        self.update = None
        self.ask_update = False
        self.repair_autostart()
        threading.Thread(target=self.check_update, name="update", daemon=True).start()
        threading.Thread(target=self.load_models, name="loader", daemon=True).start()
        threading.Thread(target=self.run_tray, name="tray", daemon=True).start()
        self.root.after(40, self.tick)

    # ---------- стан та інтерфейс ----------
    def set_state(self, state, text=None):
        self.events.put((state, text))

    def tick(self):
        if self.ask_update:
            self.ask_update = False
            self.prompt_update()
        try:
            while True:
                state, text = self.events.get_nowait()
                if state == "error":
                    self.error_until = time.time() + 3
                    play_sound(SND_ERR, self.cfg)
                if state == "idle" and time.time() < self.error_until:
                    continue
                title, hint = STATE_TEXT.get(state, ("", ""))
                self.state = state
                self.state_text = text or title
                self.state_hint = (
                    hint.format(key=key_label(self.cfg["dictate_hotkey"]))
                    if not text or state.startswith("listening")
                    else ""
                )
        except queue.Empty:
            pass
        if self.state == "error" and time.time() > self.error_until:
            self.state = "idle"
        if self.state == "idle":
            self.overlay.hide()
        else:
            self.overlay.show()
            self.overlay.draw(self.state, self.state_text, self.state_hint, self.recorder.level)
        self.root.after(40, self.tick)

    # ---------- завантаження ----------
    def load_models(self):
        try:
            self.set_state("loading", "Завантажую розпізнавання…")
            self.transcriber.load()
            self.ready.set()
            self.set_state("idle")
            self.update_tray_title()
            log.info("Готово до диктування")
            try:
                # модель Ollama не вантажимо одразу (бережемо відеопам'ять) — лише коли почали диктувати
                log.info("Очищення: %s", self.cleaner.pick_model() or "Ollama не знайдено — вимкнено")
            except Exception:
                log.exception("Очищення")
            # Голос читання вантажимо у фоні, щоб перше читання було швидким.
            self.speaker.load_uk()
        except Exception as e:
            log.exception("Помилка завантаження моделей")
            self.set_state("error", f"Помилка завантаження: {e}"[:60])

    # ---------- диктування ----------
    def on_dictate_down(self):
        if self.speaker.speaking:
            self.speaker.stop()
        if not self.ready.is_set():
            self.set_state("error", "Ще завантажуюсь, зачекайте…")
            return
        if self.recorder.recording:
            if self.toggle_mode:  # друге натискання в режимі «увімкнув/вимкнув»
                self.toggle_mode = False
                self.finish_recording()
            return
        self.target_hwnd = winutil.foreground_window()
        try:
            self.recorder.start()
        except Exception as e:
            log.exception("Мікрофон")
            self.set_state("error", f"Мікрофон недоступний: {e}"[:60])
            return
        self.rec_started = time.time()
        threading.Thread(target=self.cleaner.preload, daemon=True).start()
        play_sound(SND_START, self.cfg)
        self.set_state("listening")

    def on_dictate_up(self, other_pressed):
        if not self.recorder.recording or self.toggle_mode:
            return
        held = time.time() - self.rec_started
        if other_pressed and held < 1.0:
            # це було звичайне сполучення клавіш (напр. правий Ctrl+C), а не диктування
            self.recorder.stop(tail=False)
            self.set_state("idle")
            return
        if held < 0.35:
            self.toggle_mode = True
            self.set_state("listening_toggle")
            return
        self.finish_recording()

    def finish_recording(self):
        audio = self.recorder.stop()
        play_sound(SND_STOP, self.cfg)
        self.set_state("processing")
        threading.Thread(target=self._transcribe_and_paste, args=(audio,), name="stt", daemon=True).start()

    def _transcribe_and_paste(self, audio):
        with self.stt_lock:
            try:
                text = self.transcriber.transcribe(audio)
            except Exception as e:
                log.exception("Розпізнавання")
                self.set_state("error", f"Помилка розпізнавання: {e}"[:60])
                return
            if not text:
                self.set_state("idle")
                return
            if self.cleaner.enabled() and len(text.split()) >= 4:
                self.set_state("processing", "Причісую текст…")
                text = self.cleaner.clean(text)
            self.last_text = text
            if self.cfg["save_history"]:
                append_history(text)
            winutil.paste_text(text + " ", self.target_hwnd, self.cfg["restore_clipboard"])
            self.set_state("idle")

    def on_esc(self):
        if self.speaker.speaking:
            self.speaker.stop()
        elif self.recorder.recording:
            self.recorder.stop(tail=False)
            self.toggle_mode = False
            self.set_state("idle")

    # ---------- читання ----------
    def on_read(self, _other=None):
        if self.speaker.speaking:
            self.speaker.stop()
            return
        text = winutil.copy_selection()
        if not text.strip():
            self.set_state("error", "Спершу виділіть текст")
            return
        log.info("Читаю %d символів", len(text))
        self.speaker.speak(text)

    # ---------- оновлення ----------
    def check_update(self):
        time.sleep(15)
        import updater
        from common import DEFAULTS

        repo = self.cfg["update_repo"] or DEFAULTS["update_repo"]  # "none" = не перевіряти
        self.update = None if repo == "none" else updater.check(repo)
        if self.update:
            log.info("Доступне оновлення %s", self.update["tag"])
            try:
                if self.tray:
                    self.tray.update_menu()
            except Exception:
                pass
            self.ask_update = True  # діалог покаже головний потік (tkinter — лише з нього)

    def prompt_update(self):
        from tkinter import messagebox

        u = self.update
        notes = "\n\nСписок змін — на сторінці релізу на GitHub."
        if not (u.get("asset") and u.get("sha256")):  # без перевіреного файлу — лише сторінка релізу
            if messagebox.askyesno(
                "Голос", f"Доступна нова версія {u['tag']}.{notes}\n\nВідкрити сторінку завантаження?"
            ):
                import webbrowser

                webbrowser.open(u["page"])
            return
        if messagebox.askyesno(
            "Голос — оновлення",
            f"Доступна нова версія {u['tag']} (у вас {VERSION}).{notes}\n\n"
            "Оновити зараз? Налаштування й моделі збережуться.",
        ):
            threading.Thread(target=self.install_update, daemon=True).start()

    def install_update(self):
        import updater

        u = self.update
        try:
            path = updater.download(u, lambda pct: self.set_state("loading", f"Завантажую оновлення… {pct:.0f}%"))
            self.set_state("loading", "Встановлюю оновлення…")
            log.info("Оновлення: запускаю %s", path)
            updater.run_installer(path)
            time.sleep(1)
            self.quit()
        except Exception as e:
            log.exception("Оновлення")
            self.set_state("error", f"Не вдалося оновити: {e}"[:60])

    # ---------- прискорення NVIDIA для вже встановленої програми ----------
    def gpu_pack_offer(self):
        try:
            import cuda_pack
            from common import cuda_libs_available

            return cuda_pack.has_nvidia() and not cuda_libs_available()
        except Exception:
            return False

    def install_gpu_pack(self):
        def work():
            import cuda_pack

            try:
                cuda_pack.install(lambda d, t: self.set_state("loading", f"Прискорення NVIDIA: {d:.0f} / {t} МБ"))
                self.set_state("loading", "Перезапускаю розпізнавання…")
                self.transcriber.load()
                self.set_state("idle")
                self.update_tray_title()
                if self.tray:
                    self.tray.update_menu()
            except Exception as e:
                log.exception("Пакет прискорення")
                self.set_state("error", f"Прискорення: {e}"[:60])

        threading.Thread(target=work, daemon=True).start()

    # ---------- трей ----------
    def update_tray_title(self):
        if self.tray:
            dev = self.transcriber.device or "…"
            self.tray.title = (
                f"Голос — готовий ({dev.upper()})\n"
                f"Диктування: {self.cfg['dictate_hotkey']}\nЧитання: {self.cfg['read_hotkey']}"
            )

    def run_tray(self):
        import pystray
        from PIL import Image

        from tts import list_uk_voices

        try:
            img = Image.open(RES_DIR / "holos.png")
        except Exception:
            img = Image.new("RGBA", (64, 64), (0, 87, 183, 255))

        cfg = self.cfg
        M, Item = pystray.Menu, pystray.MenuItem

        def radio(key, value, label):
            return Item(label, lambda: cfg.set(key, value), checked=lambda _: cfg[key] == value, radio=True)

        def open_path(p):
            def _open():
                try:
                    if not p.exists():
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text("", encoding="utf-8")
                    os.startfile(str(p))  # noqa: S606 — відкрити файл у програмі за замовчуванням
                except Exception:
                    log.exception("Не вдалося відкрити %s", p)

            return _open

        voices = list_uk_voices()
        menu = M(
            Item(
                lambda _: (
                    (
                        f"Стан: готовий ({(self.transcriber.device or '').upper()})"
                        if self.ready.is_set()
                        else "Стан: завантаження…"
                    )
                    + f"  ·  v{VERSION}"
                ),
                None,
                enabled=False,
            ),
            M.SEPARATOR,
            Item(
                "Мова диктування",
                M(
                    radio("stt_language", "auto", "Автовизначення"),
                    radio("stt_language", "uk", "Українська"),
                    radio("stt_language", "ru", "Русский"),
                    radio("stt_language", "en", "English"),
                ),
            ),
            Item(
                "Голос читання (укр.)",
                M(*[radio("uk_voice", v, v) for v in voices])
                if voices
                else M(Item("немає голосів", None, enabled=False)),
            ),
            Item(
                "Голос читання (рус./англ.)",
                M(
                    radio("ru_voice", "female", "Жіночий (рус.)"),
                    radio("ru_voice", "male", "Чоловічий (рус.)"),
                    radio("en_voice", "female", "Female (EN)"),
                    radio("en_voice", "male", "Male (EN)"),
                ),
            ),
            Item(
                "Розумне очищення (Ollama)",
                lambda: cfg.set("cleanup", "off" if cfg["cleanup"] != "off" else "auto"),
                checked=lambda _: cfg["cleanup"] != "off",
            ),
            Item("Швидкість читання", M(*[radio("speed", s, f"{s:.1f}×") for s in (0.8, 0.9, 1.0, 1.1, 1.2)])),
            Item(
                lambda _: f"⬆ Оновити до {self.update['tag']}" if self.update else "",
                lambda: setattr(self, "ask_update", True),
                visible=lambda _: bool(self.update),
            ),
            Item("⚡ Увімкнути прискорення NVIDIA", self.install_gpu_pack, visible=lambda _: self.gpu_pack_offer()),
            M.SEPARATOR,
            Item(
                "Скопіювати останню диктовку",
                lambda: winutil.clip_set(self.last_text),
                enabled=lambda _: bool(self.last_text),
            ),
            Item("Історія диктувань", open_path(HISTORY_PATH)),
            Item("Налаштування (config.json)", open_path(CONFIG_PATH)),
            Item("Журнал помилок", open_path(LOGS / "holos.log")),
            Item("Запускати разом з Windows", self.toggle_autostart, checked=lambda _: self.autostart_enabled()),
            M.SEPARATOR,
            Item("Вийти", self.quit),
        )
        self.tray = pystray.Icon("holos", img, "Голос — завантаження…", menu)
        self.update_tray_title()
        self.tray.run()

    # Автозапуск = значення в реєстрі HKCU\...\Run (як у більшості програм).
    # Якщо exe переміщено чи видалено, Windows мовчки пропускає запис — жодних вікон з помилкою.
    RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    RUN_NAME = "Holos"

    def _autostart_cmd(self):
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        return f'"{pyw}" "{os.path.abspath(__file__)}"'

    def _run_get(self):
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY) as k:
                return winreg.QueryValueEx(k, self.RUN_NAME)[0]
        except OSError:
            return None

    def _run_set(self, value):
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.RUN_KEY) as k:
            if value is None:
                try:
                    winreg.DeleteValue(k, self.RUN_NAME)
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(k, self.RUN_NAME, 0, winreg.REG_SZ, value)

    def autostart_enabled(self):
        return os.name == "nt" and self._run_get() is not None

    def toggle_autostart(self):
        try:
            self._run_set(None if self.autostart_enabled() else self._autostart_cmd())
        except Exception:
            log.exception("Автозапуск")

    @staticmethod
    def _legacy_startup_files():
        from pathlib import Path

        d = Path(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
        return [d / "Holos.vbs", d / "Голос.lnk"]

    def repair_autostart(self):
        """Версії до 0.3.1 клали Holos.vbs / ярлик у теку «Автозавантаження».
        Коли exe переїжджав, Windows при старті показувала «The system cannot find the file specified».
        Прибираємо їх і переносимо автозапуск у реєстр; битий шлях у реєстрі — оновлюємо."""
        if os.name != "nt":
            return
        try:
            had_legacy = False
            for p in self._legacy_startup_files():
                if p.exists():
                    p.unlink()
                    had_legacy = True
                    log.info("Прибрано старий автозапуск: %s", p)
            cur = self._run_get()
            if cur is None:
                if had_legacy:
                    self._run_set(self._autostart_cmd())
            else:
                target = cur.split('"')[1] if cur.startswith('"') else cur.split(" ")[0]
                if not os.path.exists(target):
                    self._run_set(self._autostart_cmd())
                    log.info("Автозапуск оновлено: %s", self._autostart_cmd())
        except Exception:
            log.exception("Автозапуск")

    def quit(self):
        log.info("Вихід")
        try:
            self.speaker.stop()
            if self.tray:
                self.tray.stop()
        finally:
            self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()
        os._exit(0)


def _ollama_running() -> bool:
    import urllib.request

    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=1)
        return True
    except Exception:
        return False


def first_run_setup() -> bool:
    """Вікно першого запуску: завантаження моделей з прогресом."""
    from tkinter import ttk

    from download_models import STEPS, download_all

    win = tk.Tk()
    win.title("Голос — перше налаштування")
    win.resizable(False, False)
    try:
        win.iconbitmap(str(RES_DIR / "holos.ico"))
    except Exception:
        pass
    frm = ttk.Frame(win, padding=20)
    frm.pack()
    ttk.Label(frm, text="Голос: диктування і читання вслух", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(
        frm,
        justify="left",
        wraplength=440,
        text=(
            "Для роботи потрібно один раз завантажити моделі (~3 ГБ). "
            "Після цього програма працює повністю офлайн — ваш голос і тексти нікуди не надсилаються."
        ),
    ).pack(anchor="w", pady=(6, 12))
    labels = []
    for st in STEPS:
        lb = ttk.Label(frm, text="○  " + st)
        lb.pack(anchor="w")
        labels.append(lb)

    # --- необов'язкові доповнення ---
    import cuda_pack
    from cleanup import Cleaner
    from common import cuda_libs_available

    extras = ttk.Frame(frm)
    extras.pack(anchor="w", fill="x", pady=(10, 0))
    var_gpu = tk.BooleanVar(value=False)
    if cuda_pack.has_nvidia() and not cuda_libs_available():
        var_gpu.set(True)
        ttk.Checkbutton(
            extras,
            variable=var_gpu,
            text=(
                f"Прискорення на відеокарті NVIDIA (+{cuda_pack.APPROX_MB / 1000:.1f} ГБ) — "
                "розпізнавання у 5–10 разів швидше"
            ),
        ).pack(anchor="w")
    cfg = Config()
    cleaner = Cleaner(cfg)
    ollama_models = cleaner.available_models()
    var_llm = tk.BooleanVar(value=False)
    ollama_up = bool(ollama_models) or cleaner.pick_model() is not None or _ollama_running()
    if ollama_up and not cleaner.pick_model():
        ttk.Checkbutton(
            extras, variable=var_llm, text=("Розумне очищення тексту: завантажити модель qwen3:8b в Ollama (~5 ГБ)")
        ).pack(anchor="w")
    elif not ollama_up:
        lnk = ttk.Label(
            extras,
            foreground="#2f6fd6",
            cursor="hand2",
            text=("Необов'язково: для «розумного очищення» тексту встановіть Ollama (ollama.com)"),
        )
        lnk.pack(anchor="w")
        lnk.bind("<Button-1>", lambda _: __import__("webbrowser").open("https://ollama.com/download/windows"))

    bar = ttk.Progressbar(frm, length=440, maximum=len(STEPS))
    bar.pack(pady=12)
    status = ttk.Label(frm, text="", foreground="#555")
    status.pack(anchor="w")
    btns = ttk.Frame(frm)
    btns.pack(anchor="e", pady=(10, 0))
    result = {"ok": False, "err": None, "step": 0, "done": False, "msg": ""}

    def progress(i, n, msg):
        result["step"] = i

    def worker():
        try:
            download_all(progress)
            if var_gpu.get():
                result["msg"] = "Прискорення NVIDIA…"
                cuda_pack.install(lambda d, t: result.update(msg=f"Прискорення NVIDIA: {d:.0f} / {t} МБ"))
            if var_llm.get():
                try:
                    cleaner.pull("qwen3:8b", lambda pct, m: result.update(msg=f"Модель очищення: {pct:.0f}%"))
                except Exception as e:
                    logging.warning("Ollama pull: %s", e)  # не критично — програма працює й без очищення
            result["ok"] = True
        except Exception as e:
            logging.exception("Завантаження моделей")
            result["err"] = str(e)
        result["done"] = True

    def poll():
        i = result["step"]
        for k, lb in enumerate(labels):
            mark = (
                "✓"
                if k < i - 1 or result["ok"] or (i == len(STEPS) and result["msg"])
                else ("⏳" if k == i - 1 else "○")
            )
            lb.config(text=f"{mark}  {STEPS[k]}")
        bar["value"] = len(STEPS) if result["ok"] else max(0, i - 1)
        if result["msg"] and not result["done"]:
            status.config(text=result["msg"])
        if result["done"]:
            if result["ok"]:
                status.config(text="Готово! Запускаю…")
                win.after(800, win.destroy)
                return
            status.config(text="Помилка: " + (result["err"] or "")[:80] + "\nПеревірте інтернет і спробуйте ще раз.")
            start_btn.config(state="normal", text="Спробувати ще раз")
            return
        win.after(200, poll)

    def start():
        start_btn.config(state="disabled")
        status.config(text="Завантажую… це може зайняти 5–15 хвилин.")
        result.update(done=False, err=None)
        threading.Thread(target=worker, daemon=True).start()
        poll()

    start_btn = ttk.Button(btns, text="Завантажити", command=start)
    start_btn.pack(side="right")
    ttk.Button(btns, text="Вийти", command=win.destroy).pack(side="right", padx=8)
    win.mainloop()
    return result["ok"]


def selftest() -> int:
    """holos.exe --selftest : перевірка всіх рушіїв без інтерфейсу (для діагностики)."""
    import numpy as np

    out = open(LOGS / "selftest.txt", "w", encoding="utf-8")  # закривається у finally

    def say(*a):
        msg = " ".join(str(x) for x in a)
        print(msg, flush=True)
        out.write(msg + "\n")
        out.flush()

    try:
        from stt import Transcriber
        from tts import Speaker

        cfg = Config()
        t = time.time()
        tr = Transcriber(cfg)
        tr.load()
        say("STT ok:", tr.device, f"{time.time() - t:.1f}s")
        sp = Speaker(cfg, lambda *a: None)
        t = time.time()
        sp.load_uk()
        say("TTS uk ok:", sp.uk.device, f"{time.time() - t:.1f}s")
        a, sr = sp._synth("Записуємо бабусю 1890 року народження.", "uk", 1.0)
        say("synth uk:", a.shape, sr)
        for lang in ("ru", "en"):
            b, sr2 = sp._synth({"ru": "Проверка русского голоса.", "en": "English voice check."}[lang], lang, 1.0)
            say(f"synth {lang}:", b.shape, sr2)
        idx = (np.arange(int(len(a) * 16000 / sr)) * sr / 16000).astype(int)
        say("STT roundtrip:", tr.transcribe(a[idx]))
        say("SELFTEST OK")
        return 0
    except Exception:
        import traceback

        say(traceback.format_exc())
        say("SELFTEST FAILED")
        return 1
    finally:
        out.close()


SMOKE_MODULES = [
    # сторонні бібліотеки, які PyInstaller мав покласти в збірку
    "numpy",
    "sounddevice",
    "soundfile",
    "ctranslate2",
    "faster_whisper",
    "torch",
    "onnxruntime",
    "piper",
    "styletts2_inference",
    "ukrainian_word_stress",
    "ipa_uk",
    "stanza",
    "transformers.models.m2m_100",
    "huggingface_hub",
    "pystray",
    "PIL.Image",
    "keyboard",
    "pyperclip",
    # власні модулі
    "stt",
    "tts",
    "cleanup",
    "updater",
    "cuda_pack",
    "hotkeys",
    "download_models",
]


def smoke() -> int:
    """holos.exe --smoke : перевірка самої збірки (CI) — усе імпортується; моделі не потрібні.
    Результат — у logs/smoke.txt і в коді виходу."""
    import importlib
    import traceback

    failed = 0
    # пишемо по рядку одразу: якщо збірка впаде на імпорті, у файлі буде видно, на якому
    with open(LOGS / "smoke.txt", "w", encoding="utf-8") as out:

        def say(line):
            print(line, flush=True)
            out.write(line + "\n")
            out.flush()

        say(f"Holos {VERSION}")
        for name in SMOKE_MODULES:
            say(f"...   {name}")
            try:
                importlib.import_module(name)
                say(f"ok    {name}")
            except Exception:
                failed += 1
                say(f"FAIL  {name}\n{traceback.format_exc()}")
        say("SMOKE OK" if not failed else f"SMOKE FAILED: {failed}")
    return 1 if failed else 0


def main():
    if "--smoke" in sys.argv:
        sys.exit(smoke())
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--download" in sys.argv:  # завантаження моделей без вікна
        from download_models import download_all

        download_all()
        return
    if not winutil.single_instance():
        log.info("Вже запущено — виходжу")
        return
    log.info("Старт Голос, Python %s, дані: %s", sys.version.split()[0], ROOT)
    if not READY_FLAG.exists():
        if not first_run_setup():
            return
        os.environ["HF_HUB_OFFLINE"] = "1"
    App().run()


if __name__ == "__main__":
    main()
