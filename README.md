# Holos (Голос)

[![CI](https://github.com/canadianproducer/holos/actions/workflows/ci.yml/badge.svg)](https://github.com/canadianproducer/holos/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/canadianproducer/holos)](https://github.com/canadianproducer/holos/releases/latest)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)

**Offline dictation and read-aloud for Windows. Runs entirely on your computer — no cloud, no subscription. Ukrainian-first, also Russian and English.**

[English](README.md) · **[Українська](README.uk.md)**

---

## Features

| | |
|---|---|
| 🎙 **Dictation** | Hold **Right Ctrl** and speak. Release — the text appears wherever your cursor is: Word, a browser, a messenger, anywhere. |
| 🔊 **Read aloud** | Select text and press **Ctrl + Shift + Space**. Natural Ukrainian voices (31 to choose from), plus Russian and English. |
| ✨ **Smart cleanup** *(optional)* | A local LLM removes filler words, repetitions and self-corrections ("on Tuesday, no, Wednesday" → "on Wednesday") and fixes punctuation. Mixed-language speech is never translated. |
| 🔒 **Private** | Your voice and text never leave your computer. |

A short tap of Right Ctrl starts hands-free recording; tap again to finish. **Esc** cancels recording or stops reading.

The app's interface is in Ukrainian.

## Installation

1. Open **[Releases](../../releases/latest)** and download `Holos-Setup-<version>.exe`.
2. Run it. Windows may show a blue "Windows protected your PC" screen — this is normal for new apps without a paid code-signing certificate. Click **More info → Run anyway**.
3. On first launch the app downloads the speech models once (~3 GB, 5–15 minutes). After that everything works offline.
   - With an **NVIDIA** graphics card, tick "GPU acceleration" in the same window (+1.4 GB) — recognition becomes almost instant.
   - If [Ollama](https://ollama.com) is installed, you can download a model for smart cleanup right there.
4. A blue-and-yellow microphone icon appears in the system tray. Done!

**Requirements:** Windows 10 or 11 (64-bit), 8 GB RAM, ~5 GB of disk space. An NVIDIA GPU is optional.

### Smart cleanup (optional)

Install the free [Ollama](https://ollama.com) and a model, for example:
```
ollama pull qwen3:8b
```
Holos finds Ollama automatically. Toggle it from the tray menu.

## Updates

Holos checks GitHub for new versions. When one is available it asks "Update now?", then downloads and installs it. Settings and models are kept.

Every update is verified before it runs: the file size and SHA-256 checksum must match the values published by GitHub, so a corrupted or tampered installer is never executed.

## Settings

Right-click the tray icon: dictation language, reading voice, speed, smart cleanup, start with Windows.
Advanced options live in `config.json` (tray menu → settings). For example, `vocabulary` lists names and terms that must be spelled exactly as given (people, brands, jargon).

## Privacy

- Recognition, speech synthesis and cleanup run locally. Internet is only used to download models once and to check GitHub for updates.
- Dictated text is **never written to the log**, so the log is safe to attach to a bug report. For debugging you can enable it with `"log_text": true` in `config.json`.
- Dictation history is stored locally (`logs\history.txt`, tray menu → history). Disable with `"save_history": false`.

See [SECURITY.md](SECURITY.md) for the full list of network access.

## Troubleshooting

- Tray menu → **error log** shows what happened.
- [Open an issue](../../issues) and attach the log. Issues in Ukrainian are welcome too.

## For developers

Python 3.11: `faster-whisper` (recognition), StyleTTS2 (Ukrainian voices), Piper (Russian/English), tkinter + pystray (UI).
How it works: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Branching, versioning and releases: [CONTRIBUTING.md](CONTRIBUTING.md).

```
build.bat              # builds dist\Holos\Holos.exe (needs only internet and git)
build.bat cpu | gpu    # any PC / NVIDIA acceleration (CUDA build of torch)
build.bat release      # same as a release: CPU build + installer (Inno Setup)
Holos.exe --selftest   # checks every engine with the models
Holos.exe --smoke      # checks the build itself, no models needed

pip install -r requirements-dev.txt
pytest                 # unit tests (any OS)
ruff check . && ruff format --check .
pre-commit install     # run these checks before every commit
```

Releases are built by GitHub Actions: tag `vX.Y.Z` → build on a clean Windows runner → automated checks → release with the installer and `SHA256SUMS.txt`.

Pull requests and ideas are welcome!

## Author

**Oleksandr Potapenko ([Canadian Producer](https://github.com/canadianproducer))**

## How it was made

The code was written in pair with the AI assistant Claude — from the first idea to a working app, in conversation: the author set the goals, tested on his own computer and made the decisions; the assistant wrote and debugged the code.

## Acknowledgements

Holos stands on the shoulders of great open-source projects:

- [StyleTTS2 Ukrainian](https://huggingface.co/spaces/patriotyk/styletts2-ukrainian) by [patriotyk](https://github.com/patriotyk): Ukrainian voices, [ukrainian-word-stress](https://github.com/patriotyk/ukrainian-word-stress), [ipa-uk](https://github.com/patriotyk/ipa-uk)
- [Number verbalization](https://huggingface.co/skypro1111/m2m100-ukr-verbalization) by skypro1111
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (SYSTRAN) and [Whisper](https://github.com/openai/whisper) (OpenAI); large-v3-turbo in CTranslate2 format by Mobius Labs
- [Piper](https://github.com/OHF-Voice/piper1-gpl) — Russian and English voices
- [Stanza](https://stanfordnlp.github.io/stanza/) (Stanford NLP), [Ollama](https://ollama.com)
- Inspired by [Handy](https://github.com/cjpais/Handy), [OpenWhispr](https://github.com/OpenWhispr/openwhispr) and Wispr Flow

## License

[GPL-3.0](LICENSE). Speech and voice models have their own licenses — see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Notably, the English male Piper voice "ryan" is for non-commercial use only.
