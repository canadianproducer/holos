# Журнал змін

Усі помітні зміни «Голосу». Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/),
версії — за [семантичним версіонуванням](https://semver.org/lang/uk/).

## [Unreleased]

## [0.3.1] — 2026-09-25

### Виправлено
- Після перезавантаження Windows більше не вискакує помилка
  «Holos.vbs … The system cannot find the file specified». Автозапуск тепер — запис у реєстрі,
  старий файл із теки «Автозавантаження» прибирається автоматично.
- Скрипт завантаження релізу на GitHub правильно читає збережений вхід.

### Змінено
- README: ім'я автора — Oleksandr Potapenko.
- Для розробників: описано порядок роботи з гілками й випусками (CONTRIBUTING.md).

## [0.3.0] — 2026-09-24

### Додано
- Інсталятор `Holos-Setup.exe` без прав адміністратора.
- Автоматичні оновлення з GitHub Releases.
- Пакет прискорення NVIDIA докачується при першому запуску.
- Розумне очищення через Ollama не затримує диктування.

## [0.2.0] — 2026-09-24

### Додано
- Перший робочий випуск: диктування (правий Ctrl) і читання вголос (Ctrl+Shift+Пробіл).

[Unreleased]: https://github.com/canadianproducer/holos/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/canadianproducer/holos/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/canadianproducer/holos/releases/tag/v0.3.0
