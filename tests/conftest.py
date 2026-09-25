"""Спільне для тестів.

Тести йдуть на будь-якій ОС (CI — Linux) без мікрофона, моделей і Windows API:
- тека даних програми — тимчасова (HOLOS_DATA_DIR), щоб не чіпати справжні налаштування;
- апаратні/Windows-бібліотеки (sounddevice, keyboard) замінено заглушками.
"""

import os
import sys
import tempfile
import types

os.environ["HOLOS_DATA_DIR"] = tempfile.mkdtemp(prefix="holos-test-")


def _stub(name, **attrs):
    if name not in sys.modules:
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        sys.modules[name] = mod


_stub("sounddevice", InputStream=object, play=lambda *a, **k: None, wait=lambda: None, stop=lambda: None)
_stub("keyboard", KEY_DOWN="down", KEY_UP="up", hook=lambda cb: None)
