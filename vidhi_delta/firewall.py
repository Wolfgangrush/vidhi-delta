"""The deterministic firewall — code decides, never a model.

For each citation found, the firewall runs the structural and currency tiers and
assigns a status by a fixed rule:

    any IMPOSSIBLE-coordinate defect          -> TRAP        (do not file)
    a currency delta, or an UNKNOWN reporter  -> FLAG        (fix / confirm first)
    everything else (plausible, real-looking) -> UNVERIFIED  (read it before filing)

UNVERIFIED is the crux of the design. A structurally perfect citation is NOT
passed — because the one thing code cannot check offline is whether the case
exists and whether it actually holds what the draft says it holds. That is the
'partial-with-trap' failure mode: a real reporter coordinate carrying a fabricated
or mis-stated proposition. The firewall refuses to let any such citation through
silently; it routes it to the advocate with the asserted proposition attached.
"""
from __future__ import annotations

import re
from typing import List, Optional

from . import reporters, statutes
from .types import (CiteStatus, CitationCheck, Defect, FilingReport,
                    FilingVerdict, RawCite, Tier)

# defect codes that mean "this citation cannot exist" -> TRAP
_TRAP_CODES = {
    "year-in-future", "year-before-origin", "volume-impossible",
    "court-not-yet-existing", "neutral-before-system", "number-impossible",
}


# --- parsers (re-read the verbatim raw string into fields) ------------------

def _parse_reported(raw: str):
    m = re.search(r"\(\s*(\d{4})\s*\)\s+(\d{1,3})\s+([A-Za-z][A-Za-z.&]{1,12}?)\s+(\d{1,6})\b", raw)
    if not m:
        return None
    return {"year": int(m.group(1)), "volume": int(m.group(2)),
            "reporter": m.group(3), "page": int(m.group(4))}


def _parse_air(raw: str):
    m = re.search(r"\bAIR\s+(\d{4})\s+([A-Za-z&]{1,8})\s+(\d{1,6})\b", raw)
    if not m:
        return None
    return {"year": int(m.group(1)), "court": m.group(2), "page": int(m.group(3))}


def _parse_neutral(raw: str):
    m = re.search(r"\b(\d{4})\s+INSC\s+(\d{1,6})\b", raw)
    if m:
        return {"year": int(m.group(1)), "system": "INSC", "number": int(m.group(2))}
    m = re.search(r"\b(\d{4})\s*:\s*([A-Z]{2,}(?:-[A-Z]{2,5})?)\s*:\s*(\d{1,6})\b", raw)
    if m:
        return {"year": int(m.group(1)), "system": m.group(2), "number": int(m.group(3))}
    return None


def _parse_scc_online(raw: str):
    m = re.search(r"\b(\d{4})\s+SCC\s+OnLine\s+([A-Za-z][A-Za-z&]*)\s+(\d{1,6})\b", raw)
    if not m:
        return None
    return {"year": int(m.group(1)), "court": m.group(2), "number": int(m.group(3))}


def _parse_statute(raw: str):
    m = re.search(r"[Ss]ections?\s+(\d+[A-Za-z()]*)\s+(?:of\s+(?:the\s+)?)?(.+)$", raw)
    if not m:
        return None
    return {"section": m.group(1), "code": m.group(2).strip()}


# --- per-citation check -----------------------------------------------------

def check_citation(raw: RawCite) -> Optional[CitationCheck]:
    """Return a CitationCheck, or None for a citation that needs no surfacing
    (a current-code statute reference: nothing to verify, no delta)."""
    defects: List[Defect] = []
    parsed: dict = {}

    if raw.kind == "reported":
        parsed = _parse_reported(raw.raw) or {}
        if parsed:
            defects = reporters.check_reported(
                parsed["year"], parsed["volume"], parsed["reporter"], parsed["page"])
    elif raw.kind == "air":
        parsed = _parse_air(raw.raw) or {}
        if parsed:
            defects = reporters.check_air(parsed["year"], parsed["court"], parsed["page"])
    elif raw.kind == "neutral":
        parsed = _parse_neutral(raw.raw) or {}
        if parsed:
            defects = reporters.check_neutral(
                parsed["year"], parsed["system"], parsed["number"])
    elif raw.kind == "scc-online":
        parsed = _parse_scc_online(raw.raw) or {}
        # SCC OnLine ids run sequentially and large; only a future-year is impossible.
        if parsed and parsed["year"] > reporters.CURRENT_YEAR:
            defects = [Defect(Tier.STRUCTURE, "year-in-future",
                              f"SCC OnLine citation dated {parsed['year']} is in the future.",
                              fix="Cannot exist — remove.")]
    elif raw.kind == "statute":
        parsed = _parse_statute(raw.raw) or {}
        if parsed:
            d = statutes.check_currency(parsed["code"], parsed.get("section"))
            if d is None:
                return None  # current code, nothing to surface
            defects = [d]

    status = _status_from(defects)
    return CitationCheck(raw=raw, status=status, defects=defects, parsed=parsed)


def _status_from(defects: List[Defect]) -> CiteStatus:
    if any(d.code in _TRAP_CODES for d in defects):
        return CiteStatus.TRAP
    if defects:  # currency / unknown-reporter / implausible-page -> fixable
        return CiteStatus.FLAG
    return CiteStatus.UNVERIFIED


# --- document-level firewall ------------------------------------------------

def check_document(text: str, source: str = "<text>") -> FilingReport:
    from .extract import scan
    raws = scan(text)
    checks: List[CitationCheck] = []
    for r in raws:
        c = check_citation(r)
        if c is not None:
            checks.append(c)

    notes = _consistency_notes(checks)

    if any(c.status is CiteStatus.TRAP for c in checks):
        verdict = FilingVerdict.DO_NOT_FILE
    elif any(c.status in (CiteStatus.UNVERIFIED, CiteStatus.FLAG) for c in checks):
        verdict = FilingVerdict.VERIFY_BEFORE_FILING
    else:
        # only reachable when every check is CONFIRMED (i.e. after an accept pass)
        verdict = FilingVerdict.FILING_SAFE

    if not checks:
        notes.insert(0, "No citations were detected. Either the draft cites no "
                        "authority, or its citation format is one VIDHI-DELTA does "
                        "not yet scan — check by eye before relying on this.")

    return FilingReport(source=source, checks=checks, verdict=verdict, notes=notes)


def _consistency_notes(checks: List[CitationCheck]) -> List[str]:
    """Narrow, precision-safe consistency surfacing: the SAME case name carrying
    two DIFFERENT coordinates in the SAME reporter series is a real inconsistency
    (a citation-swap tell). Reported only — parallel cites across series are fine."""
    notes: List[str] = []
    by_name: dict = {}
    for c in checks:
        name = c.raw.case_name
        if not name or c.raw.kind != "reported" or not c.parsed:
            continue
        key = re.sub(r"\s+", " ", name.lower()).strip()
        rep = reporters._norm(c.parsed.get("reporter", ""))
        coord = (c.parsed.get("year"), c.parsed.get("volume"), c.parsed.get("page"))
        by_name.setdefault((key, rep), set()).add(coord)
    for (key, rep), coords in by_name.items():
        if len(coords) > 1:
            notes.append(
                f"CONSISTENCY: the same case appears with {len(coords)} different "
                f"{rep} coordinates — {sorted(coords)}. One of them is wrong; reconcile "
                f"before filing.")
    return notes


def accept(report: FilingReport, accepted_raws) -> FilingReport:
    """Mark the listed citations CONFIRMED (the advocate has personally read them).
    This is the ONLY path to FILING_SAFE — the firewall never sets it on its own.
    `accepted_raws` is an iterable of verbatim citation strings."""
    wanted = {re.sub(r"\s+", " ", s).strip() for s in accepted_raws}
    for c in report.checks:
        if c.status is CiteStatus.UNVERIFIED and \
           re.sub(r"\s+", " ", c.raw.raw).strip() in wanted:
            c.status = CiteStatus.CONFIRMED
    if any(c.status is CiteStatus.TRAP for c in report.checks):
        report.verdict = FilingVerdict.DO_NOT_FILE
    elif any(c.status in (CiteStatus.UNVERIFIED, CiteStatus.FLAG)
             for c in report.checks):
        report.verdict = FilingVerdict.VERIFY_BEFORE_FILING
    else:
        report.verdict = FilingVerdict.FILING_SAFE
    return report
