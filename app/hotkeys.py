"""Глобальні гарячі клавіші з підтримкою «утримання» (натиснув/відпустив).

Працюємо з іменами клавіш-модифікаторів, пробілу та F-клавіш — вони однакові
на будь-якій розкладці. Літери в комбінаціях не радимо (на кирилиці `keyboard`
їх називає інакше).
"""

import logging
import queue
import threading
import time

import keyboard

ALIASES = {
    "left ctrl": "ctrl",
    "control": "ctrl",
    "left control": "ctrl",
    "right control": "right ctrl",
    "left shift": "shift",
    "left alt": "alt",
    "alt gr": "right alt",
    "altgr": "right alt",
    "left windows": "win",
    "right windows": "win",
    "windows": "win",
    "escape": "esc",
}
GENERIC = {
    "ctrl": {"ctrl", "right ctrl"},
    "shift": {"shift", "right shift"},
    "alt": {"alt", "right alt"},
    "win": {"win"},
}


def norm(name: str) -> str:
    n = (name or "").lower().strip()
    return ALIASES.get(n, n)


class Hotkey:
    def __init__(self, combo: str, on_down, on_up):
        self.tokens = [norm(t) for t in combo.split("+")]
        self.on_down, self.on_up = on_down, on_up
        self.active = False
        self.other_pressed = False

    def token_hit(self, token, key):
        return key in GENERIC.get(token, {token})

    def involves(self, key):
        return any(self.token_hit(t, key) for t in self.tokens)

    def satisfied(self, pressed):
        return all(any(self.token_hit(t, k) for k in pressed) for t in self.tokens)


class HotkeyManager:
    def __init__(self):
        self.keys = []
        self.pressed = {}
        self.esc_callback = None
        self._lock = threading.Lock()
        # Одна черга подій -> натискання/відпускання обробляються строго по черзі.
        self._q = queue.Queue()
        threading.Thread(target=self._dispatch, name="hotkeys", daemon=True).start()
        keyboard.hook(self._on_event)

    def _dispatch(self):
        while True:
            fn, args = self._q.get()
            try:
                fn(*args)
            except Exception:
                logging.exception("Помилка обробника гарячої клавіші")

    def add(self, combo, on_down=None, on_up=None):
        hk = Hotkey(combo, on_down, on_up)
        self.keys.append(hk)
        logging.info("Гаряча клавіша: %s", combo)
        return hk

    def clear(self):
        self.keys = []

    def _fire(self, fn, *args):
        if fn:
            self._q.put((fn, args))

    def _on_event(self, e):
        key = norm(e.name)
        now = time.time()
        with self._lock:
            if e.event_type == keyboard.KEY_DOWN:
                if key in self.pressed:  # автоповтор
                    return
                # «застряглі» клавіші (відпущені у вікні адміністратора тощо)
                for k, t in list(self.pressed.items()):
                    if now - t > 30:
                        self.pressed.pop(k, None)
                self.pressed[key] = now
                if key == "esc" and self.esc_callback:
                    self._fire(self.esc_callback)
                for hk in self.keys:
                    if hk.active:
                        if not hk.involves(key):
                            hk.other_pressed = True
                    elif hk.involves(key) and hk.satisfied(self.pressed):
                        hk.active, hk.other_pressed = True, False
                        self._fire(hk.on_down)
            else:
                self.pressed.pop(key, None)
                for hk in self.keys:
                    if hk.active and hk.involves(key):
                        hk.active = False
                        self._fire(hk.on_up, hk.other_pressed)

    def any_pressed(self):
        return bool(self.pressed)
