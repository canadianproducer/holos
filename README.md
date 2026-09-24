# Голос (Holos)

**Диктування і читання вголос для Windows. Працює на вашому комп'ютері, без інтернету й підписок. Українська — в пріоритеті.**

*[English below](#english)*

---

## Що вміє

| | |
|---|---|
| 🎙 **Диктування** | Утримуйте **правий Ctrl** і говоріть. Відпустили — текст з'явився там, де стоїть курсор: у Word, браузері, месенджері, будь-де. |
| 🔊 **Читання вголос** | Виділіть текст і натисніть **Ctrl + Shift + Пробіл**. Природні українські голоси (31 на вибір), а також російська та англійська. |
| ✨ **Розумне очищення** *(за бажанням)* | Прибирає «е-е», повтори й самовиправлення («у вівторок, ні, в середу» → «в середу»), розставляє розділові знаки. Мішанину мов не перекладає. |
| 🔒 **Приватність** | Ваш голос і тексти нікуди не надсилаються. Усе працює локально. |

Коротке натискання правого Ctrl вмикає запис без утримання, повторне — завершує. **Esc** — скасувати запис або зупинити читання.

## Встановлення

1. Відкрийте сторінку **[Releases](../../releases/latest)** і завантажте `Holos-Setup.exe`.
2. Запустіть його. Windows може показати синє вікно «Windows захистила ваш комп'ютер» — це нормально для нових програм без платного підпису. Натисніть **«Докладніше» → «Однаково запустити»**.
3. Під час першого запуску програма один раз завантажить мовні моделі (~3 ГБ, 5–15 хвилин). Далі все працює офлайн.
   - Якщо у вас відеокарта **NVIDIA**, у тому ж вікні буде галочка «Прискорення на відеокарті» (+1,4 ГБ) — розпізнавання стане майже миттєвим.
   - Якщо встановлена [Ollama](https://ollama.com), можна одразу завантажити модель для «розумного очищення».
4. У треї (біля годинника) з'явиться синьо-жовта іконка з мікрофоном. Готово!

**Вимоги:** Windows 10 або 11 (64-bit), 8 ГБ оперативної пам'яті, ~5 ГБ на диску. Відеокарта NVIDIA не обов'язкова, але з нею розпізнавання працює майже миттєво.

### Розумне очищення (необов'язково)

Потрібна безкоштовна програма [Ollama](https://ollama.com) і модель, наприклад:
```
ollama pull qwen3:8b
```
«Голос» сам знайде Ollama. Увімкнути/вимкнути — у меню іконки в треї.

## Оновлення

Програма сама перевіряє, чи вийшла нова версія. Якщо так — запитає «Оновити зараз?», завантажить і встановить її сама. Налаштування й моделі зберігаються.

## Налаштування

Правий клік на іконці в треї: мова диктування, голос читання, швидкість, очищення, автозапуск.
Детальніші налаштування — у файлі `config.json` (пункт «Налаштування» в меню). Наприклад, у `vocabulary` можна додати свої слова й назви, які треба писати саме так (імена, бренди, терміни).

## Щось не працює?

- Меню трею → **«Журнал помилок»** — там видно, що сталося.
- Створіть [Issue](../../issues) і прикладіть журнал.

## Для розробників

Код на Python: `faster-whisper` (розпізнавання), StyleTTS2 (українські голоси), Piper (російська/англійська), tkinter + pystray (інтерфейс).

```
build.bat        # збирає dist\Holos\Holos.exe (потрібні лише інтернет і git)
build.bat cpu    # версія для будь-якого ПК
build.bat gpu    # з прискоренням NVIDIA (torch CUDA)
release.bat      # код на GitHub + інсталятор + завантаження в Releases (одним кліком)
Holos.exe --selftest   # перевірка всіх рушіїв без інтерфейсу
```

Структура: `app/holos.py` — інтерфейс і логіка, `stt.py` — запис і розпізнавання, `tts.py` — озвучення, `cleanup.py` — розумне очищення, `hotkeys.py`, `winutil.py` — робота з Windows.

Pull requests і ідеї — вітаються!

## Автор

**Alex Potapenko ([Canadian Producer](https://github.com/canadianproducer))**

## Як це зроблено

Код написано в парі з AI-асистентом Claude — від першої ідеї до робочої програми, у діалозі: автор ставив задачі, тестував на своєму комп'ютері й ухвалював рішення, асистент писав і налагоджував код.

<sub>Проєкт незалежний і не пов'язаний з Anthropic.</sub>

## Подяки

«Голос» стоїть на плечах чудових відкритих проєктів:

- [StyleTTS2 Ukrainian](https://huggingface.co/spaces/patriotyk/styletts2-ukrainian) — [patriotyk](https://github.com/patriotyk): українські голоси, [ukrainian-word-stress](https://github.com/patriotyk/ukrainian-word-stress), [ipa-uk](https://github.com/patriotyk/ipa-uk)
- [Вербалізація чисел](https://huggingface.co/skypro1111/m2m100-ukr-verbalization) — skypro1111
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (SYSTRAN) і [Whisper](https://github.com/openai/whisper) (OpenAI); модель large-v3-turbo у форматі CTranslate2 — Mobius Labs
- [Piper](https://github.com/OHF-Voice/piper1-gpl) — голоси для російської та англійської
- [Stanza](https://stanfordnlp.github.io/stanza/) (Stanford NLP), [Ollama](https://ollama.com)
- Натхнення: [Handy](https://github.com/cjpais/Handy), [OpenWhispr](https://github.com/OpenWhispr/openwhispr), Wispr Flow

## Ліцензія

[GPL-3.0](LICENSE). Моделі голосів і розпізнавання мають власні ліцензії (див. їхні сторінки). Зокрема, англійський чоловічий голос Piper «ryan» — лише для некомерційного використання.

---

<a name="english"></a>
## English

**Holos** ("voice" in Ukrainian) is a free, offline dictation and read-aloud tool for Windows, Ukrainian-first (also Russian and English).

- **Dictate:** hold **Right Ctrl**, speak, release — text is pasted wherever your cursor is.
- **Read aloud:** select text, press **Ctrl+Shift+Space**. Natural Ukrainian voices (StyleTTS2), Piper for RU/EN.
- **Smart cleanup (optional):** a local LLM via Ollama removes filler words and self-corrections, fixes punctuation, never translates.
- **Private:** everything runs locally.

Download `Holos-Setup.exe` from [Releases](../../releases/latest). First launch downloads models (~3 GB) once.

Made by **Alex Potapenko (Canadian Producer)**. The code was written in pair with the AI assistant Claude. This is an independent project, not affiliated with Anthropic. Licensed under GPL-3.0.
