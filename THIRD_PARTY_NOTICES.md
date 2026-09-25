# Сторонні компоненти

«Голос» поширюється за ліцензією [GPL-3.0](LICENSE) і спирається на чужі відкриті проєкти й моделі.
Повний список Python-пакетів збірки з версіями й ліцензіями генерується під час збірки
(`tools/third_party_licenses.py`) і лежить у теці встановленої програми: `THIRD_PARTY_LICENSES.md`.

## Моделі й дані (завантажуються при першому запуску, не входять в інсталятор)

| Що | Звідки | Ліцензія |
|---|---|---|
| Розпізнавання мовлення Whisper large-v3-turbo (формат CTranslate2) | [OpenAI Whisper](https://github.com/openai/whisper), конвертація — Hugging Face `dropbox-dash/faster-whisper-large-v3-turbo` | MIT |
| Українські голоси StyleTTS2 | [patriotyk/styletts2_ukrainian_multispeaker](https://huggingface.co/patriotyk/styletts2_ukrainian_multispeaker), голоси — [простір patriotyk/styletts2-ukrainian](https://huggingface.co/spaces/patriotyk/styletts2-ukrainian) | MIT |
| Вербалізація чисел | [skypro1111/m2m100-ukr-verbalization](https://huggingface.co/skypro1111/m2m100-ukr-verbalization) | MIT |
| Наголоси (дані Stanza) | [Stanford NLP Stanza](https://stanfordnlp.github.io/stanza/) | Apache-2.0 |
| Голоси Piper: ru irina, ru dmitri, en amy | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) | див. MODEL_CARD кожного голосу |
| Голос Piper en ryan | [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices) | **CC BY-NC-SA 4.0 — лише некомерційне використання** |
| Пакет прискорення NVIDIA (cuBLAS, cuDNN, CUDA runtime) — за бажанням | офіційні пакети NVIDIA з PyPI | NVIDIA Software License |

## Основні бібліотеки в інсталяторі

| Компонент | Ліцензія |
|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT |
| [PyTorch](https://pytorch.org/) | BSD-3-Clause |
| [styletts2-inference](https://github.com/patriotyk/styletts2-inference), [ukrainian-word-stress](https://github.com/lang-uk/ukrainian-word-stress), [ukrainian-accentor](https://github.com/egorsmkv/ukrainian-accentor) | MIT |
| [ipa-uk](https://github.com/patriotyk/ipa-uk) | див. сторінку проєкту |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) (разом з espeak-ng) | GPL-3.0-or-later |
| [ONNX Runtime](https://onnxruntime.ai/) | MIT |
| [Transformers](https://github.com/huggingface/transformers), [huggingface_hub](https://github.com/huggingface/huggingface_hub), [Stanza](https://github.com/stanfordnlp/stanza) | Apache-2.0 |
| [udapi](https://github.com/udapi/udapi-python) (залежність Stanza) | GPL-3.0-or-later |
| [pystray](https://github.com/moses-palmer/pystray) | LGPL-3.0 |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) + PortAudio, [keyboard](https://github.com/boppreh/keyboard) | MIT |
| [python-soundfile](https://github.com/bastibe/python-soundfile) + libsndfile | BSD-3-Clause / LGPL-2.1 |
| [NumPy](https://numpy.org/), [SciPy](https://scipy.org/), [pyperclip](https://github.com/asweigart/pyperclip) | BSD |
| [librosa](https://librosa.org/) | ISC |
| [Pillow](https://python-pillow.org/) | MIT-CMU |
| [Python](https://www.python.org/) (вбудований інтерпретатор) | PSF-2.0 |

Інсталятор створено за допомогою [Inno Setup](https://jrsoftware.org/isinfo.php), програму зібрано [PyInstaller](https://pyinstaller.org/).
