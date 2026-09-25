# Third-party notices

Holos is licensed under [GPL-3.0](LICENSE) and builds on other open-source projects and models.
The complete list of Python packages in a build, with versions and licenses, is generated at build time
(`tools/third_party_licenses.py`) and installed with the app as `THIRD_PARTY_LICENSES.md`.

## Models and data (downloaded on first launch, not included in the installer)

| What | Source | License |
|---|---|---|
| Speech recognition: Whisper large-v3-turbo (CTranslate2 format) | [OpenAI Whisper](https://github.com/openai/whisper), converted by Hugging Face `dropbox-dash/faster-whisper-large-v3-turbo` | MIT |
| Ukrainian StyleTTS2 voices | [patriotyk/styletts2_ukrainian_multispeaker](https://huggingface.co/patriotyk/styletts2_ukrainian_multispeaker); voices from the [patriotyk/styletts2-ukrainian](https://huggingface.co/spaces/patriotyk/styletts2-ukrainian) space | MIT |
| Number verbalization | [skypro1111/m2m100-ukr-verbalization](https://huggingface.co/skypro1111/m2m100-ukr-verbalization) | MIT |
| Word stress (Stanza data) | [Stanford NLP Stanza](https://stanfordnlp.github.io/stanza/) | Apache-2.0 |
| Piper voices: ru irina, ru dmitri, en amy | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) | see each voice's MODEL_CARD |
| Piper voice: en ryan | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) | **CC BY-NC-SA 4.0 — non-commercial use only** |
| NVIDIA acceleration pack (cuBLAS, cuDNN, CUDA runtime) — optional | official NVIDIA packages on PyPI | NVIDIA Software License |

## Main libraries in the installer

| Component | License |
|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT |
| [PyTorch](https://pytorch.org/) | BSD-3-Clause |
| [styletts2-inference](https://github.com/patriotyk/styletts2-inference), [ukrainian-word-stress](https://github.com/lang-uk/ukrainian-word-stress), [ukrainian-accentor](https://github.com/egorsmkv/ukrainian-accentor) | MIT |
| [ipa-uk](https://github.com/patriotyk/ipa-uk) | see project page |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) (with espeak-ng) | GPL-3.0-or-later |
| [ONNX Runtime](https://onnxruntime.ai/) | MIT |
| [Transformers](https://github.com/huggingface/transformers), [huggingface_hub](https://github.com/huggingface/huggingface_hub), [Stanza](https://github.com/stanfordnlp/stanza) | Apache-2.0 |
| [udapi](https://github.com/udapi/udapi-python) (Stanza dependency) | GPL-3.0-or-later |
| [pystray](https://github.com/moses-palmer/pystray) | LGPL-3.0 |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) + PortAudio, [keyboard](https://github.com/boppreh/keyboard) | MIT |
| [python-soundfile](https://github.com/bastibe/python-soundfile) + libsndfile | BSD-3-Clause / LGPL-2.1 |
| [NumPy](https://numpy.org/), [SciPy](https://scipy.org/), [pyperclip](https://github.com/asweigart/pyperclip) | BSD |
| [librosa](https://librosa.org/) | ISC |
| [Pillow](https://python-pillow.org/) | MIT-CMU |
| [Python](https://www.python.org/) (embedded interpreter) | PSF-2.0 |

The installer is made with [Inno Setup](https://jrsoftware.org/isinfo.php); the app is packaged with [PyInstaller](https://pyinstaller.org/).
