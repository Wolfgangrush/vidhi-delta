"""Statute-currency engine — the 'delta' VIDHI-DELTA is named for.

On 01-07-2024 three colonial-era codes were replaced:

    Code of Criminal Procedure, 1973  ->  Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)
    Indian Penal Code, 1860           ->  Bharatiya Nyaya Sanhita, 2023          (BNS)
    Indian Evidence Act, 1872         ->  Bharatiya Sakshya Adhiniyam, 2023      (BSA)

A pleading that cites the *old* Code as the *governing* provision is not
automatically wrong — by the savings clauses, a cause or offence that arose
before 01-07-2024 is still governed by the old Code. So this is always a FLAG,
never a TRAP: the firewall surfaces the delta and asks the advocate to confirm
which regime governs THIS matter, and — if the new one does — gives the successor
section. The section map below is REPRESENTATIVE, not exhaustive. RSH-VERIFY each
mapping against the bare Sanhita before relying on it.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

from .types import Defect, Tier

TRANSITION_DATE = "2024-07-01"

# Normalised old-code identifiers -> (successor code, human label of old code)
OLD_CODES: Dict[str, Tuple[str, str]] = {
    "crpc": ("BNSS", "Code of Criminal Procedure, 1973"),
    "codeofcriminalprocedure": ("BNSS", "Code of Criminal Procedure, 1973"),
    "ipc": ("BNS", "Indian Penal Code, 1860"),
    "indianpenalcode": ("BNS", "Indian Penal Code, 1860"),
    "evidenceact": ("BSA", "Indian Evidence Act, 1872"),
    "indianevidenceact": ("BSA", "Indian Evidence Act, 1872"),
}

# (old_code_key, old_section) -> successor section. Representative; RSH-VERIFY.
SECTION_MAP: Dict[Tuple[str, str], str] = {
    # CrPC -> BNSS
    ("crpc", "41"): "BNSS s.35",
    ("crpc", "154"): "BNSS s.173",
    ("crpc", "156"): "BNSS s.175",
    ("crpc", "161"): "BNSS s.180",
    ("crpc", "164"): "BNSS s.183",
    ("crpc", "173"): "BNSS s.193",
    ("crpc", "200"): "BNSS s.223",
    ("crpc", "311"): "BNSS s.348",
    ("crpc", "313"): "BNSS s.351",
    ("crpc", "437"): "BNSS s.480",
    ("crpc", "438"): "BNSS s.482",
    ("crpc", "439"): "BNSS s.483",
    ("crpc", "482"): "BNSS s.528",
    # IPC -> BNS
    ("ipc", "120B"): "BNS s.61",
    ("ipc", "302"): "BNS s.103",
    ("ipc", "304B"): "BNS s.80",
    ("ipc", "307"): "BNS s.109",
    ("ipc", "323"): "BNS s.115",
    ("ipc", "354"): "BNS s.74",
    ("ipc", "376"): "BNS s.64",
    ("ipc", "420"): "BNS s.318(4)",
    ("ipc", "498A"): "BNS s.85",
    ("ipc", "506"): "BNS s.351",
    # Evidence -> BSA
    ("evidenceact", "27"): "BSA s.23",
    ("evidenceact", "45"): "BSA s.39",
    ("evidenceact", "65B"): "BSA s.63",
    ("evidenceact", "114"): "BSA s.119",
}


def normalise_code(token: str) -> str:
    return (token.replace(".", "").replace(" ", "").replace(",", "")
            .replace("the", "").lower())


def check_currency(code_token: str, section: Optional[str]) -> Optional[Defect]:
    """If an old Code is cited, surface the delta. Always a FLAG, never a TRAP."""
    key = normalise_code(code_token)
    entry = OLD_CODES.get(key)
    if entry is None:
        return None  # already a current code, or one we don't track
    successor, old_label = entry
    succ = None
    if section is not None:
        succ = SECTION_MAP.get((key, section.upper()))
    detail = (f"the likely successor is {succ}" if succ
              else f"the successor Sanhita is the {successor}")
    return Defect(
        Tier.CURRENCY, "old-code-cited",
        f"This cites the {old_label}, replaced w.e.f. {TRANSITION_DATE} by the "
        f"{successor}. For a cause/offence on or after {TRANSITION_DATE}, {detail}.",
        fix=(f"Confirm which regime governs THIS matter. If it arose on/after "
             f"{TRANSITION_DATE}, cite {succ or successor}. If before, the old Code "
             f"is correct by the savings clause — keep it and say so."))
