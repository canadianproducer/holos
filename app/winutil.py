"""Все, що стосується Windows: фокус вікна, буфер обміну, натискання клавіш.

Клавіші надсилаємо через SendInput з віртуальними кодами (VK) — це працює
незалежно від розкладки (українська/російська/англійська). Бібліотека
`keyboard` з іменами літер ламається на кириличних розкладках.
"""

import ctypes
import logging
import os
import time

import pyperclip

IS_WIN = os.name == "nt"

VK_CONTROL, VK_SHIFT, VK_MENU = 0x11, 0x10, 0x12
VK_LCONTROL, VK_RCONTROL, VK_LSHIFT, VK_RSHIFT = 0xA2, 0xA3, 0xA0, 0xA1
VK_LMENU, VK_RMENU, VK_LWIN, VK_RWIN = 0xA4, 0xA5, 0x5B, 0x5C
VK_C, VK_V = 0x43, 0x56
KEYEVENTF_KEYUP = 0x0002
INPUT_KEYBOARD = 1

if IS_WIN:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _U)]

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
    user32.IsWindow.argtypes = (wintypes.HWND,)
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.GetClipboardSequenceNumber.restype = wintypes.DWORD


def _key(vk, up=False):
    i = INPUT(type=INPUT_KEYBOARD)
    i.ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP if up else 0, time=0, dwExtraInfo=0)
    return i


def send_combo(*vks):
    """send_combo(VK_CONTROL, VK_V) -> Ctrl+V."""
    if not IS_WIN:
        return
    seq = [_key(v) for v in vks] + [_key(v, True) for v in reversed(vks)]
    arr = (INPUT * len(seq))(*seq)
    user32.SendInput(len(seq), arr, ctypes.sizeof(INPUT))


def release_modifiers():
    """Якщо користувач ще тримає Ctrl/Shift/Alt — «відпускаємо» їх програмно,
    щоб наш Ctrl+V не перетворився на Ctrl+Shift+V."""
    if not IS_WIN:
        return
    ups = [
        _key(vk, True)
        for vk in (VK_LSHIFT, VK_RSHIFT, VK_LMENU, VK_RMENU, VK_LWIN, VK_RWIN)
        if user32.GetAsyncKeyState(vk) & 0x8000
    ]
    if ups:
        arr = (INPUT * len(ups))(*ups)
        user32.SendInput(len(ups), arr, ctypes.sizeof(INPUT))


def modifiers_down() -> bool:
    if not IS_WIN:
        return False
    return any(
        user32.GetAsyncKeyState(vk) & 0x8000
        for vk in (VK_LCONTROL, VK_RCONTROL, VK_LSHIFT, VK_RSHIFT, VK_LMENU, VK_RMENU, VK_LWIN, VK_RWIN)
    )


def wait_modifiers_released(timeout=1.5):
    t = time.time()
    while modifiers_down() and time.time() - t < timeout:
        time.sleep(0.02)


def foreground_window():
    return user32.GetForegroundWindow() if IS_WIN else None


def focus_window(hwnd) -> bool:
    """Повертає фокус у вікно, де починали диктувати (виправляє «вставило не туди»)."""
    if not IS_WIN or not hwnd or not user32.IsWindow(hwnd):
        return False
    if user32.GetForegroundWindow() == hwnd:
        return True
    fg = user32.GetForegroundWindow()
    cur = kernel32.GetCurrentThreadId()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    tgt_thread = user32.GetWindowThreadProcessId(hwnd, None)
    try:
        user32.AttachThreadInput(cur, fg_thread, True)
        user32.AttachThreadInput(cur, tgt_thread, True)
        user32.SetForegroundWindow(hwnd)
    finally:
        user32.AttachThreadInput(cur, fg_thread, False)
        user32.AttachThreadInput(cur, tgt_thread, False)
    time.sleep(0.05)
    return user32.GetForegroundWindow() == hwnd


def clip_seq():
    return user32.GetClipboardSequenceNumber() if IS_WIN else 0


def clip_get() -> str:
    for _ in range(5):
        try:
            return pyperclip.paste() or ""
        except Exception:
            time.sleep(0.05)  # буфер тимчасово зайнятий іншою програмою
    return ""


def clip_set(text: str):
    for _ in range(5):
        try:
            pyperclip.copy(text)
            return
        except Exception:
            time.sleep(0.05)
    logging.warning("Не вдалося записати в буфер обміну")


def paste_text(text: str, hwnd=None, restore=True):
    """Вставляє текст у активне поле через буфер обміну + Ctrl+V."""
    old = clip_get() if restore else ""
    clip_set(text)
    if hwnd:
        focus_window(hwnd)
    wait_modifiers_released(0.8)
    release_modifiers()
    time.sleep(0.03)
    send_combo(VK_CONTROL, VK_V)
    if restore and old:
        time.sleep(0.35)  # дати програмі забрати текст до відновлення буфера
        clip_set(old)
    # Якщо в буфері була картинка/файл (old == "") — залишаємо продиктований текст:
    # так його можна вставити вручну, якщо програма не прийняла Ctrl+V.


def copy_selection(timeout=0.6) -> str:
    """Копіює виділений текст активної програми, не псуючи буфер обміну."""
    old = clip_get()
    before = clip_seq()
    wait_modifiers_released()
    release_modifiers()
    send_combo(VK_CONTROL, VK_C)
    t = time.time()
    while clip_seq() == before and time.time() - t < timeout:
        time.sleep(0.02)
    if clip_seq() == before:
        return ""
    text = clip_get()
    if old:
        clip_set(old)
    return text


def message_box(text: str, title: str = "Голос"):
    """Просте вікно-повідомлення поверх усіх вікон (без tkinter)."""
    if IS_WIN:
        user32.MessageBoxW(None, text, title, 0x40 | 0x40000)  # MB_ICONINFORMATION | MB_TOPMOST


def run_elevated_and_wait(exe: str, params: str, timeout_ms: int = 600_000) -> int | None:
    """Запускає програму з правами адміністратора (Windows спитає дозволу) і чекає завершення.
    Повертає код виходу або None, якщо користувач відмовив."""
    if not IS_WIN:
        return None

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", ctypes.c_ulong),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", ctypes.c_void_p),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIconOrMonitor", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    info = SHELLEXECUTEINFOW(
        cbSize=ctypes.sizeof(SHELLEXECUTEINFOW), fMask=0x40, lpVerb="runas", lpFile=exe, lpParameters=params, nShow=0
    )  # SEE_MASK_NOCLOSEPROCESS, SW_HIDE
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        logging.warning("Запуск від імені адміністратора не вдався (код %s)", ctypes.get_last_error())
        return None  # 1223 = користувач натиснув «Ні»
    try:
        kernel32.WaitForSingleObject(info.hProcess, timeout_ms)
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
        return code.value
    finally:
        kernel32.CloseHandle(info.hProcess)


def single_instance(name="HolosVoiceApp") -> bool:
    if not IS_WIN:
        return True
    kernel32.CreateMutexW(None, False, name)
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS


# --- Вікно-плашка без фокуса -------------------------------------------------
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE, WS_EX_TOPMOST, WS_EX_TRANSPARENT, WS_EX_LAYERED = (
    0x80,
    0x08000000,
    0x8,
    0x20,
    0x80000,
)
SW_HIDE, SW_SHOWNOACTIVATE = 0, 4


def make_overlay(hwnd):
    """Плашка не краде фокус і пропускає кліки крізь себе."""
    if not IS_WIN:
        return
    get = user32.GetWindowLongPtrW if hasattr(user32, "GetWindowLongPtrW") else user32.GetWindowLongW
    setl = user32.SetWindowLongPtrW if hasattr(user32, "SetWindowLongPtrW") else user32.SetWindowLongW
    get.restype = ctypes.c_ssize_t
    get.argtypes = (wintypes.HWND, ctypes.c_int)
    setl.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t)
    style = get(hwnd, GWL_EXSTYLE)
    setl(
        hwnd,
        GWL_EXSTYLE,
        style | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST | WS_EX_TRANSPARENT | WS_EX_LAYERED,
    )


def show_no_activate(hwnd, show: bool):
    if IS_WIN:
        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE if show else SW_HIDE)
