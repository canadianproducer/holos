# Architecture

A Windows tray application. One process, several threads; all computation is local.

## Modules (`app/`)

| Module | Responsibility |
|---|---|
| `holos.py` | Entry point, UI (tkinter overlay, tray menu), dictation and read-aloud flow, updates, autostart, first-run setup, `--selftest`, `--smoke` |
| `common.py` | Data folders, settings (`Config`), logging, device selection (CPU/CUDA). Imported before any ML library: sets `HF_HOME` etc. |
| `stt.py` | Microphone capture (`Recorder`), faster-whisper recognition (`Transcriber`), hallucination filter |
| `tts.py` | Speech: StyleTTS2 (Ukrainian), Piper (Russian/English), number verbalization, streaming playback |
| `cleanup.py` | Smart cleanup via a local Ollama; falls back to the raw text if the model is unavailable or the result looks wrong |
| `hotkeys.py` | Global hotkeys with hold/release, handled on a single queue |
| `winutil.py` | Win32: paste via clipboard + SendInput (layout-independent), window focus, non-activating overlay |
| `updater.py` | GitHub Releases check, download with SHA-256 verification, silent install |
| `cuda_pack.py` | NVIDIA acceleration pack: pinned PyPI wheels, SHA-256 verified |
| `download_models.py` | Model download on first launch |

## Dictation flow

```
Right Ctrl down ─ hotkeys ─► Recorder.start()           (audio buffered at 16 kHz)
Right Ctrl up   ─ hotkeys ─► Recorder.stop() ─► stt thread
                               Transcriber.transcribe()  (VAD, prompt with the user's vocabulary)
                               Cleaner.clean()           (only if Ollama already has the model loaded, ≤12 s)
                               winutil.paste_text()      (clipboard + Ctrl+V into the original window)
```
The UI is only touched from the main thread (tkinter); other threads post state changes to the `App.events` queue.

## User data

`%LOCALAPPDATA%\Holos` (or next to the exe when `portable.txt` exists, or `HOLOS_DATA_DIR`):
`config.json`, `models\` (~3 GB), `logs\holos.log` (rotated 2 MB × 3, no dictated text), `logs\history.txt`.

## Build and release

- `build.bat` runs the same way locally and in CI: uv + Python 3.11 → dependencies from `requirements.lock` →
  PyInstaller (`holos.spec`) → Inno Setup (`installer.iss`).
- The version lives only in `app/common.py`; the installer, the exe properties and the CI checks read it from there.
- `.github/workflows/ci.yml` — ruff and pytest on every push/PR; `release.yml` — build, smoke tests and publishing
  for a `vX.Y.Z` tag.

## Known limitations

- The installer is not code-signed (Windows SmartScreen shows a warning). Update integrity is guaranteed by SHA-256.
- Hugging Face models are downloaded from the `main` revision, not a pinned commit.
- Windows 10/11 x64 only.
