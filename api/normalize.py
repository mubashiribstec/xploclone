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

Pause preservation (human-voice work, 2026-10-30): normalisation keeps
the *meaning* (numbers, dates, postcodes) and *flattens* the *typography*
(dashes, quotes) into ASCII forms the model's text encoder handles —
but it must NOT flatten *pauses*: a comma, a full stop, an em-dash and
a line break are different pauses in human speech, so they map to
different ASCII forms (comma, full stop, hyphen) instead of all
becoming commas. See ``humanize_text`` below for the sentence-break step.

Tag policy (gap A4, skill: prosody/emotion tags): Chatterbox was
trained with vocalisation tags such as ``[laugh]``. They are allowed
in FILE GENERATION only (``POST /v1/tts``), and only from the
whitelist below. The live-call path (Phase 3) strips ALL tags, and
any tag not on the whitelist is stripped everywhere — user text must
never pass ``[scream]`` or an invented tag through to the model.
"""

import re

# Chatterbox trained tags, whitelisted for file generation only.
WHITELISTED_TAGS = frozenset({"laugh", "sigh", "chuckle", "gasp", "cough"})

_TAG_RE = re.compile(r"\[([A-Za-z][A-Za-z _\-]{0,30})\]")


def apply_tag_policy(text: str, allow_tags: bool = True) -> str:
    """Apply the vocalisation-tag policy to raw user text.

    ``allow_tags=True`` (file generation, ``POST /v1/tts``): keep
    whitelisted tags exactly as written, strip every other ``[tag]``.
    ``allow_tags=False`` (live-call / default path, Phase 3): strip
    ALL tags, whitelisted or not — a phone call must never laugh,
    sigh or cough on a caller's behalf because the text said so.
    Tag names are matched case-insensitively; kept tags are written
    lower-case. Stray brackets without a closing ``]`` are left alone.
    """
    if allow_tags:

        def _keep(match: re.Match[str]) -> str:
            name = match.group(1).strip().lower()
            return f"[{name}]" if name in WHITELISTED_TAGS else ""

        out = _TAG_RE.sub(_keep, text)
    else:
        out = _TAG_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def humanize_text(text: str) -> str:
    """Make normalised text read like a human speaking, not a list.

    - Line breaks become sentence breaks: a line that does not end
      with terminal punctuation gets a full stop, so the pause the
      writer intended survives chunking (comma < full stop < line
      break in pause length).
    - Long sentences (> 180 chars) are split at the first comma past
      60 chars into two short sentences — one idea per sentence.
      Over-long chunks force flat, rushed delivery; short sentences
      let the model breathe.
    - No fake breath sounds, no background noise, no added words:
      this step only inserts punctuation breaks. It never
      over-articulates — the words stay exactly as written.
    """
    lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[-1].isalnum() or line[-1] in ")\"'":
            line += "."
        lines.append(line)
    joined = " ".join(lines)
    sentences = re.split(r"(?<=[.!?])\s+", joined)
    out: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            out.extend(_split_long_sentence(sentence))
    return " ".join(out)


def _split_long_sentence(sentence: str) -> list[str]:
    """Split one over-long sentence at a comma into two sentences."""
    if len(sentence) <= 180:
        return [sentence]
    comma = sentence.find(",", 60)
    if comma == -1 or comma > len(sentence) - 40:
        return [sentence]
    first = sentence[:comma].rstrip()
    rest = sentence[comma + 1 :].strip()
    if not first or not rest:
        return [sentence]
    if not first.endswith((".", "!", "?")):
        first += "."
    rest = rest[0].upper() + rest[1:]
    return [first, rest]


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
    # "st." is NOT here — it is handled in normalize_text (m2): "Main St."
    # is a street, "St. John" is a saint. A blanket expansion is wrong.
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
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_STREET_ST_RE = re.compile(r"(\b[A-Z][A-Za-z]*)\s+St\.")
_REMAINING_ST_RE = re.compile(r"\bSt\.", re.IGNORECASE)
_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
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


def _iso_date_to_words(match: re.Match[str]) -> str:
    """ISO YYYY-MM-DD -> spoken date, e.g. 'January five, twenty twenty six' (m2)."""
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return match.group(0)
    year_match = re.match(r"(\d{4})", match.group(1))
    year_words = _year_to_words(year_match) if year_match else str(year)  # type: ignore[arg-type]
    return f"{_MONTHS[month - 1]} {_int_to_words(day)}, {year_words}"


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
        .replace("—", " - ")  # em-dash: hyphen pause, NOT a comma
        .replace("–", " - ")  # en-dash: same — distinct from a comma
        .replace("…", ". ")  # ellipsis: full-stop pause, NOT a comma
    )
    # "St." — street vs saint (m2): "123 Main St." -> "Main Street";
    # a leading "St. John" -> "Saint John". Do the street case first.
    out = _STREET_ST_RE.sub(r"\1 Street", out)
    out = _REMAINING_ST_RE.sub("Saint", out)
    # Abbreviations first (they contain periods that look like sentence ends).
    for abbr, full in _ABBREVIATIONS.items():
        out = re.sub(rf"\b{re.escape(abbr)}", full, out, flags=re.IGNORECASE)
    out = _MONEY_RE.sub(_money_to_words, out)
    out = _PERCENT_RE.sub(
        lambda m: (
            _int_to_words(int(float(m.group(1)))) + " percent"
            if float(m.group(1)).is_integer()
            else m.group(1) + " percent"
        ),
        out,
    )
    out = _TIME_RE.sub(_time_to_words, out)
    # ISO dates before the year/integer passes (m2): "2026-01-05" must not
    # become "twenty twenty six-one-five".
    out = _ISO_DATE_RE.sub(_iso_date_to_words, out)
    out = _YEAR_RE.sub(_year_to_words, out)
    out = _INT_RE.sub(lambda m: _int_to_words(int(m.group(0))), out)
    # Postcodes LAST (m3): their digits must stay digits ("S W 1 A 1 A A"),
    # and the integer pass above would have spelled isolated digits.
    out = _POSTCODE_RE.sub(_postcode_to_words, out)
    out = re.sub(r"\s+", " ", out).strip()
    return out
