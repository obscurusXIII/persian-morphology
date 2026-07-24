import pytest

from persian_morphology.normalizer import ZWNJ, normalize


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("نمي روم", f"نمی{ZWNJ}روم"),
        ("مي   ساختم", f"می{ZWNJ}ساختم"),
        ("كتاب", "کتاب"),
        ("مـی\u200cرَوَم", f"می{ZWNJ}روم"),
        (f"می  {ZWNJ}  روم", f"می{ZWNJ}روم"),
        ("رفته ام", f"رفته{ZWNJ}ام"),
        ("رفته   اند", f"رفته{ZWNJ}اند"),
        ("نرفته بودم", "نرفته بودم"),
    ],
)
def test_normalize(source: str, expected: str) -> None:
    assert normalize(source) == expected


@pytest.mark.parametrize("text", ["نمي روم", "می\u200cروم", "رفته ام", "  كتاب‌ها  "])
def test_normalize_is_idempotent(text: str) -> None:
    normalized = normalize(text)
    assert normalize(normalized) == normalized
