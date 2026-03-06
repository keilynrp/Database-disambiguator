"""
Name normalization utilities for the Authority Resolution Layer.

Handles:
- Unicode NFD decomposition → diacritic stripping (García → garcia)
- 'Surname, Firstname' → 'Firstname Surname' reformatting (VIAF cataloguing format)
- Punctuation collapse and whitespace normalization
"""
from __future__ import annotations

import re
import unicodedata
from typing import List


def strip_diacritics(text: str) -> str:
    """NFD decompose then drop all combining (diacritic) characters."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_name(name: str) -> str:
    """
    Canonical form for fuzzy comparison:
      - strip diacritics  (García → garcia)
      - lowercase
      - collapse punctuation to single spaces
      - collapse whitespace
    """
    s = strip_diacritics(name)
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def reformat_surname_first(name: str) -> str:
    """
    Convert cataloguing-inverted format 'Surname, Firstname [Middle]'
    to natural order 'Firstname [Middle] Surname'.
    VIAF returns names in this inverted form.
    If no comma is present, returns the name unchanged.
    """
    if "," in name:
        parts = name.split(",", 1)
        return f"{parts[1].strip()} {parts[0].strip()}"
    return name


def name_variants(name: str) -> List[str]:
    """
    Return all normalised variants of a name to maximise recall against
    authority sources that use different conventions.
    """
    variants: list[str] = [normalize_name(name)]
    reformatted = reformat_surname_first(name)
    if reformatted != name:
        variants.append(normalize_name(reformatted))
    return variants
