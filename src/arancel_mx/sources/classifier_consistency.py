"""Cross-check tariff classifier pages expose consistent fraction data."""

from __future__ import annotations

import re

from arancel_mx.domain.normalization import fold_text


def _fold(value: object) -> str:
    return fold_text(value).casefold()


def normalize_duty(value: str | None) -> str:
    if value is None:
        return ""
    folded = _fold(value).replace(".", "")
    if folded in {"ex", "exento", "exenta"}:
        return "ex"
    match = re.search(r"(\d+(?:[.,]\d+)?)", folded)
    return match.group(1).replace(",", ".") if match else folded


def description_tokens(value: str) -> set[str]:
    stopwords = {
        "de",
        "la",
        "el",
        "los",
        "las",
        "y",
        "o",
        "a",
        "en",
        "para",
        "con",
        "sin",
        "del",
        "al",
        "por",
        "un",
        "una",
        "que",
        "se",
        "su",
    }
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", _fold(value))
        if len(token) > 2 and token not in stopwords
    }
    return tokens


def descriptions_consistent(left: str, right: str) -> bool:
    left_folded = _fold(left)
    right_folded = _fold(right)
    if left_folded in right_folded or right_folded in left_folded:
        return True
    left_tokens = description_tokens(left)
    right_tokens = description_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    overlap = left_tokens & right_tokens
    minimum = min(len(left_tokens), len(right_tokens))
    return len(overlap) >= max(2, minimum // 2)
