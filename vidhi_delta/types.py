"""Result types for VIDHI-DELTA.

A citation NEVER passes on the firewall's word that it is *true*. The firewall is
deterministic code; it can prove a citation is structurally *impossible* (a
fabricated reporter coordinate, a court that did not yet exist, a repealed Code
cited as live), and it can prove a citation is *unconfirmed* (structurally
plausible, but whether the case exists and whether it supports the asserted
proposition is something only a human reading the report can know). It can never
prove a citation is sound. So the firewall's honest default for every real-looking
citation is UNVERIFIED — the advocate must read it before it is filed.

The verdict is computed from the per-citation checks, never authored by a model.
No language model runs in this package at all: extraction is deterministic regex,
and the law (reporter plausibility, statute currency) lives in code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class Tier(str, Enum):
    """The check that produced a defect."""
    STRUCTURE = "STRUCTURE"        # the citation's coordinates are/aren't possible
    CONSISTENCY = "CONSISTENCY"    # the same case is/ isn't cited consistently
    CURRENCY = "CURRENCY"          # the provision is/ isn't the one in force
    PROPOSITION = "PROPOSITION"    # whether the authority supports the claim — human only


class CiteStatus(str, Enum):
    """Per-citation outcome.

    TRAP and FLAG are *earned* by deterministic proof of a defect. UNVERIFIED is
    the default a real-looking citation falls to — it is not a pass, it is a debt
    the advocate must discharge by reading the authority. CONFIRMED is only ever
    set by the advocate's own confirmation pass (never by the firewall on a fresh
    run), and it is what makes the advocate's later certification honest.
    """
    TRAP = "TRAP"              # structurally impossible / fabricated pattern — DO NOT FILE
    FLAG = "FLAG"              # a fixable defect (dead statute cited as live, inconsistent cite)
    UNVERIFIED = "UNVERIFIED"  # plausible, but existence + proposition unconfirmed — you must read it
    CONFIRMED = "CONFIRMED"    # the advocate has personally verified this authority


class FilingVerdict(str, Enum):
    DO_NOT_FILE = "DO_NOT_FILE"                  # >=1 TRAP present
    VERIFY_BEFORE_FILING = "VERIFY_BEFORE_FILING"  # no traps, but unconfirmed / flagged authorities remain
    FILING_SAFE = "FILING_SAFE"                  # every authority CONFIRMED, zero flags, zero traps


@dataclass
class Defect:
    tier: Tier
    code: str          # short machine code, e.g. "scc-volume-impossible"
    message: str       # what is wrong, in the advocate's language
    fix: Optional[str] = None  # what to do about it

    def to_dict(self) -> dict:
        return {"tier": self.tier.value, "code": self.code,
                "message": self.message, "fix": self.fix}


@dataclass
class RawCite:
    """A citation as found in the text, before any judgement is formed."""
    raw: str                       # the verbatim citation string
    kind: str                      # "reported" | "neutral" | "scc-online" | "statute"
    span: Tuple[int, int]          # character offsets in the source text
    case_name: Optional[str] = None  # nearest "X v. Y" preceding the cite, if found
    proposition: Optional[str] = None  # the sentence the cite is offered to support

    def to_dict(self) -> dict:
        return {"raw": self.raw, "kind": self.kind, "span": list(self.span),
                "case_name": self.case_name, "proposition": self.proposition}


@dataclass
class CitationCheck:
    raw: RawCite
    status: CiteStatus
    defects: List[Defect] = field(default_factory=list)
    # parsed structured fields (year/reporter/volume/page or statute/section), best-effort
    parsed: dict = field(default_factory=dict)

    @property
    def is_trap(self) -> bool:
        return self.status is CiteStatus.TRAP

    @property
    def is_flag(self) -> bool:
        return self.status is CiteStatus.FLAG

    @property
    def needs_human(self) -> bool:
        return self.status is CiteStatus.UNVERIFIED

    def to_dict(self) -> dict:
        return {
            "raw": self.raw.to_dict(),
            "status": self.status.value,
            "defects": [d.to_dict() for d in self.defects],
            "parsed": self.parsed,
        }


@dataclass
class FilingReport:
    source: str
    checks: List[CitationCheck]
    verdict: FilingVerdict
    notes: List[str] = field(default_factory=list)

    @property
    def traps(self) -> List[CitationCheck]:
        return [c for c in self.checks if c.status is CiteStatus.TRAP]

    @property
    def flags(self) -> List[CitationCheck]:
        return [c for c in self.checks if c.status is CiteStatus.FLAG]

    @property
    def unverified(self) -> List[CitationCheck]:
        return [c for c in self.checks if c.status is CiteStatus.UNVERIFIED]

    @property
    def confirmed(self) -> List[CitationCheck]:
        return [c for c in self.checks if c.status is CiteStatus.CONFIRMED]

    def summary(self) -> str:
        n = len(self.checks)
        if self.verdict is FilingVerdict.DO_NOT_FILE:
            return (f"DO NOT FILE — {len(self.traps)} citation(s) look fabricated or "
                    f"impossible, out of {n} found.")
        if self.verdict is FilingVerdict.VERIFY_BEFORE_FILING:
            return (f"VERIFY BEFORE FILING — {len(self.unverified)} authority(ies) you must "
                    f"read, {len(self.flags)} flag(s), out of {n} found. No fabricated "
                    f"coordinates detected.")
        return f"FILING-SAFE — all {n} authority(ies) confirmed; no flags, no traps."

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "verdict": self.verdict.value,
            "summary": self.summary(),
            "counts": {
                "found": len(self.checks),
                "trap": len(self.traps),
                "flag": len(self.flags),
                "unverified": len(self.unverified),
                "confirmed": len(self.confirmed),
            },
            "checks": [c.to_dict() for c in self.checks],
            "notes": self.notes,
        }
