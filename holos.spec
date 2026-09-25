# PyInstaller: збірка Holos.exe (тека dist/Holos).  Запуск: pyinstaller holos.spec
import re
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# Версія — з app/common.py (єдине джерело); потрапляє у «Властивості» Holos.exe.
VERSION = re.search(r'^VERSION = "(.+)"', open("app/common.py", encoding="utf-8").read(), re.M).group(1)
_nums = (*(int(x) for x in re.findall(r"\d+", VERSION)[:3]), 0)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=_nums, prodvers=_nums),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "042204B0",
                    [
                        StringStruct("CompanyName", "Canadian Producer"),
                        StringStruct("FileDescription", "Голос — диктування і читання вголос"),
                        StringStruct("FileVersion", VERSION),
                        StringStruct("InternalName", "Holos"),
                        StringStruct("LegalCopyright", "© 2026 Oleksandr Potapenko · GPL-3.0"),
                        StringStruct("OriginalFilename", "Holos.exe"),
                        StringStruct("ProductName", "Голос (Holos)"),
                        StringStruct("ProductVersion", VERSION),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0422, 1200])]),
    ],
)

datas, binaries, hiddenimports = [("assets", "assets")], [], []

# Пакети з даними/бінарниками, які PyInstaller сам не знаходить повністю
for pkg in ["faster_whisper", "ctranslate2", "piper", "onnxruntime", "ukrainian_word_stress",
            "ukrainian_accentor", "ipa_uk", "styletts2_inference", "stanza", "librosa", "soundfile",
            "sounddevice", "_sounddevice_data", "marisa_trie", "sentencepiece", "espeakbridge"]:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:
        print("skip", pkg, e)

hiddenimports += collect_submodules("transformers.models.m2m_100")
hiddenimports += ["pystray._win32" if sys.platform == "win32" else "pystray._xorg",
                  "keyboard", "pyperclip", "PIL._tkinter_finder"]

a = Analysis(
    ["app/holos.py"],
    pathex=["app"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["matplotlib", "IPython", "jupyter", "notebook", "pytest", "tensorboard", "gradio",
              "torch.utils.tensorboard", "sympy.testing"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Holos",
    icon="assets/holos.ico",
    console=False,          # без чорного вікна
    upx=False,
    version=version_info,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Holos", upx=False)
