"""Unit tests for English text normalisation (api/normalize.py)."""

from api.normalize import normalize_text


def test_plain_prose_unchanged() -> None:
    assert normalize_text("Hello, this is a test.") == "Hello, this is a test."


def test_currency_pounds() -> None:
    assert normalize_text("The pay is £13.50 per hour.") == (
        "The pay is thirteen pounds fifty pence per hour."
    )


def test_currency_dollars_no_pence() -> None:
    assert normalize_text("It costs $15.") == "It costs fifteen dollars."


def test_year() -> None:
    assert normalize_text("Founded in 2026.") == "Founded in twenty twenty six."


def test_time() -> None:
    assert normalize_text("Meet at 10:30.") == "Meet at ten thirty."


def test_percent() -> None:
    assert normalize_text("Save 20% today.") == "Save twenty percent today."


def test_abbreviation() -> None:
    assert normalize_text("Dr. Smith will see you.") == "Doctor Smith will see you."


def test_postcode_spelled() -> None:
    out = normalize_text("The office is at SW1A 1AA.")
    # Digits stay digits inside the spelled form (m3).
    assert out == "The office is at S W 1 A 1 A A."


def test_iso_date() -> None:
    # ISO dates are spoken as dates (m2), not "twenty twenty six-one-five".
    assert normalize_text("Meet on 2026-01-05.") == "Meet on January five, twenty twenty six."


def test_street_st() -> None:
    # "Main St." is a street (m2). The period after "St." is consumed
    # by the expansion, as with the other abbreviations.
    assert normalize_text("123 Main St.") == "one hundred twenty three Main Street"


def test_saint_st() -> None:
    # A leading "St." is a saint (m2).
    assert normalize_text("St. John will attend.") == "Saint John will attend."


def test_small_numbers() -> None:
    assert normalize_text("There are 3 roles.") == "There are three roles."


def test_blank() -> None:
    assert normalize_text("   ") == ""


def test_curly_quotes_and_dashes() -> None:
    out = normalize_text("“Hello” — she said.")
    assert "“" not in out and "—" not in out
