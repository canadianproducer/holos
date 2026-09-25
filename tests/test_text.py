import pytest

from cleanup import postprocess
from stt import Transcriber
from tts import detect_lang, split_sentences


@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("Привіт, як справи? Їжак їсть яблуко.", "uk"),
        ("Привет, как дела? Это мышь.", "ru"),
        ("Hello, how are you?", "en"),
        ("12345 !!!", None),
    ],
)
def test_detect_lang(text, lang):
    assert detect_lang(text) == lang


def test_detect_lang_ambiguous_cyrillic_uses_default():
    assert detect_lang("мама мала", default_cyr="ru") == "ru"


def test_split_sentences_merges_short():
    text = "Так. Завтра зранку буде сильний дощ. Потім нарешті вийде сонце."
    assert split_sentences(text) == ["Так. Завтра зранку буде сильний дощ.", "Потім нарешті вийде сонце."]


def test_split_sentences_limits_length_without_losing_text():
    text = "Дуже довге речення, яке має коми, паузи і ще багато слів " * 8 + "кінець."
    parts = split_sentences(text, max_len=120)
    assert len(parts) > 1
    assert all(len(p) <= 120 for p in parts)
    assert "".join(parts).replace(" ", "") == text.replace(" ", "")


def test_split_sentences_empty():
    assert split_sentences("   ") == []


def make_transcriber(**cfg):
    return Transcriber({"replacements": {}, **cfg})


@pytest.mark.parametrize("junk", ["Дякую за перегляд!", "Thanks for watching.", "Субтитры сделал DimaTorzok", " ... "])
def test_hallucinations_are_dropped(junk):
    assert make_transcriber().clean(junk) == ""


def test_long_text_with_phrase_is_kept():
    text = "Я сказав йому: дякую за перегляд, але це було давно і зовсім в іншому контексті розмови."
    assert make_transcriber().clean(text) == text


def test_replacements_and_spacing():
    tr = make_transcriber(replacements={"гітхаб": "GitHub"})
    assert tr.clean("Код на  гітхаб , друзі !") == "Код на GitHub, друзі!"


@pytest.mark.parametrize(
    ("raw", "out", "expected"),
    [
        ("ну е-е завтра в середу", "Завтра в середу.", "Завтра в середу."),
        ("ну е-е завтра в середу", "<think>хм</think>\n«Завтра в середу.»", "Завтра в середу."),
        ("ну е-е завтра в середу", "", None),
        ("коротко", "Ось розгорнута відповідь на ваше питання з купою нових фактів і порад.", None),
        ("довгий текст " * 10, "ок", None),
    ],
)
def test_cleanup_postprocess(raw, out, expected):
    assert postprocess(raw, out) == expected
