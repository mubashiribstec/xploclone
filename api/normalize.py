"""English text normalisation for TTS (PLAN-v2 §6.3, Phase 1 scope).

Deterministic, no ML, no network. Runs *before* the engine so the model
hears words, not symbols.

What it does (English only in v1):
- expands currency (``£13.50`` -> "thirteen pounds fifty", ``$15`` ->
  "fifteen dollars"), common abbreviations (``Dr.`` -> "Doctor"),
  percentages, and times (``10am`` -> "10 a m" is left to the engine;
  ``10:30`` -> "ten thirty");
- expands integers 0-999 and years (``2026`` -> "twenty twenty six");
- keeps UK postcodes intact as letter-spelled tokens (``SW1A 1AA`` ->
  "S W 1 A 1 A A") so the engine spells rather than mangles them;
- collapses whitespace, fixes curly quotes / dashes to ASCII.

What it does NOT do in v1 (explicit non-goals):
- Urdu script, Roman Urdu transliteration, or code-switching — those belong
  to the gated Urdu work (docs/URDU-SPIKE.md). Urdu text reaching this
  module is passed through unchanged and will be rejected upstream by the
  voice router (``mubashir-ur`` has no engine in v1).
"""

from __future__ import annotations

import re

_ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]

_ABBREVIATIONS = {
    "dr.": "Doctor",
    "mr.": "Mister",
    "mrs.": "Missus",
    "ms.": "Miss",
    "st.": "Saint",
    "ave.": "Avenue",
    "rd.": "Road",
    "no.": "number",
    "vs.": "versus",
    "etc.": "etcetera",
    "e.g.": "for example",
    "i.e.": "that is",
}

_CURRENCY_WORDS = {"£": "pounds", "$": "dollars", "€": "euros"}

_POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b")
_MONEY_RE = re.compile(r"([£$€])\s*(\d+)(?:\.(\d{1,2}))?\b")
_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_INT_RE = re.compile(r"\b\d+\b")


def _int_to_words(n: int) -> str:
    """English words for 0-9999 (years handled separately by the caller)."""
    if n < 0 or n > 9999:
        return str(n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens] + (" " + _ONES[ones] if ones else "")
    if n < 1000:
        hundreds, rest = divmod(n, 100)
        return _ONES[hundreds] + " hundred" + (" " + _int_to_words(rest) if rest else "")
    thousands, rest = divmod(n, 1000)
    return _ONES[thousands] + " thousand" + (" " + _int_to_words(rest) if rest else "")


def _year_to_words(match: re.Match[str]) -> str:
    year = int(match.group(0))
    first, second = divmod(year, 100)
    if second == 0:
        return _int_to_words(first) + " hundred"
    if second < 10:
        return _int_to_words(first) + " oh " + _ONES[second]
    return _int_to_words(first) + " " + _int_to_words(second)


def _money_to_words(match: re.Match[str]) -> str:
    symbol, pounds, pence = match.group(1), int(match.group(2)), match.group(3)
    word = _CURRENCY_WORDS[symbol]
    major = _int_to_words(pounds) if pounds < 10000 else str(pounds)
    if not pence or int(pence) == 0:
        return f"{major} {word}"
    pence_int = int(pence.ljust(2, "0"))
    return (
        f"{major} {word} {pence_int} pence"
        if symbol == "£"
        else (f"{major} {word} {pence_int} cents")
    )


def _time_to_words(match: re.Match[str]) -> str:
    hour, minute = int(match.group(1)), int(match.group(2))
    if minute == 0:
        return _int_to_words(hour) + " o'clock"
    return _int_to_words(hour) + " " + _int_to_words(minute)


def _postcode_to_words(match: re.Match[str]) -> str:
    outward, inward = match.group(1), match.group(2)
    chars = " ".join(list(outward + inward))
    # Keep digits as digits inside the spelled form; the engine reads them.
    return chars


def normalize_text(text: str) -> str:
    """Normalise English text for synthesis. Idempotent on plain prose."""
    if not text or not text.strip():
        return ""
    out = text.strip()
    # ASCII-ify punctuation the engine was not trained on.
    out = (
        out.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("—", ", ")
        .replace("–", ", ")
        .replace("…", ", ")
    )
    # Abbreviations first (they contain periods that look like sentence ends).
    for abbr, full in _ABBREVIATIONS.items():
        out = re.sub(rf"\b{re.escape(abbr)}", full, out, flags=re.IGNORECASE)
    out = _POSTCODE_RE.sub(_postcode_to_words, out)
    out = _MONEY_RE.sub(_money_to_words, out)
    out = _PERCENT_RE.sub(
        lambda m: _int_to_words(int(float(m.group(1)))) + " percent"
        if float(m.group(1)).is_integer()
        else m.group(1) + " percent",
        out,
    )
    out = _TIME_RE.sub(_time_to_words, out)
    out = _YEAR_RE.sub(_year_to_words, out)
    out = _INT_RE.sub(lambda m: _int_to_words(int(m.group(0))), out)
    out = re.sub(r"\s+", " ", out).strip()
    return out
