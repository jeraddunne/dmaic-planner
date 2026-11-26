"""Input checks. Every bad input gets a sentence a person can act on, never a
stack trace.

The limits, and why:
  MIN_WORDS = 15        The dataset's own floor (schema.CaseRecord.validate rejects
                        narratives under 15 words). The shortest training narrative
                        is 27 words; below 15 there is too little to route.
  MAX_CHARS = 5,000     Just above the longest training narrative (4,471 characters,
                        about 650 words). Longer text is cut at the last whole word
                        before 5,000 characters and the user is told how much was
                        left out, so they can shorten it themselves if the key facts
                        came late. This also bounds the time one request can take.
  REJECT_CHARS = 50,000 Ten times the limit. Text that long is a whole document, not
                        one narrative, and classifying its first page would be
                        misleading, so it is refused instead of cut.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MIN_WORDS = 15
MAX_CHARS = 5_000
REJECT_CHARS = 50_000

_WORD = re.compile(r"[^\W\d_]", re.UNICODE)  # a "word" has at least one letter in it
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class CheckedInput:
    """text is what goes to the model; None means the input was refused and
    message says why. When text is set, message is an optional note (truncation)."""
    text: str | None
    message: str = ""
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.text is not None


def count_words(text: str) -> int:
    return sum(1 for token in text.split() if _WORD.search(token))


def check_narrative(value: object) -> CheckedInput:
    if value is None:
        return CheckedInput(None, "Please paste a process-problem narrative first.")
    if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], str):
        value = value[0]  # a common API slip: ["text"] instead of "text"
    if not isinstance(value, str):
        return CheckedInput(None, (
            f"Expected the narrative as text (a string), but got {type(value).__name__}. "
            "Send one plain-text narrative, for example "
            "\"Invoices wait two weeks for approval because ...\"."
        ))

    text = _CONTROL.sub(" ", value).strip()
    if not text:
        return CheckedInput(None, (
            "The narrative is empty. Describe one process problem in a few sentences: "
            "what happens, where, how often, what it costs, and whether anyone knows why."
        ))
    if len(text) > REJECT_CHARS:
        return CheckedInput(None, (
            f"That is {len(text):,} characters, which looks like a whole document rather "
            f"than one narrative. Paste a summary of a single process problem, up to "
            f"{MAX_CHARS:,} characters (about 800 words)."
        ))

    words = count_words(text)
    if words < MIN_WORDS:
        return CheckedInput(None, (
            f"That is {words} word{'s' if words != 1 else ''}; the model needs at least "
            f"{MIN_WORDS}. Add what happens, where, how often, and whether the cause is known."
        ))

    if len(text) <= MAX_CHARS:
        return CheckedInput(text)

    cut = text[:MAX_CHARS]
    space = cut.rfind(" ")
    if space > MAX_CHARS // 2:
        cut = cut[:space]
    cut = cut.rstrip()
    return CheckedInput(cut, truncated=True, message=(
        f"Your narrative is {len(text):,} characters; only the first {len(cut):,} "
        f"(about {count_words(cut):,} words) were used. If the key facts come later, "
        "shorten it and try again."
    ))
