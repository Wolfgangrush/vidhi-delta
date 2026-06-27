"""The two output artifacts — and the wall between them.

This module is where the disclosure question is resolved in code, by keeping two
artifacts strictly apart:

  1. vidhi-ledger.txt        — a PRIVATE working file. It records what the firewall
                               found and what the advocate must still read. It is
                               for the advocate's desk only. It NEVER enters a
                               filing and names no tool inside any filed document.

  2. list-of-authorities.txt — a CLEAN worksheet in the advocate's own register.
                               It is the ordinary List of Authorities that already
                               accompanies a pleading. It carries NO tool name, NO
                               'AI', NO watermark. The advocate ticks each entry as
                               he reads it and reproduces it under his OWN signature.

The court sees only the advocate's own attested authorities. It never sees the
firewall: there is no tool fingerprint to find on what is filed. And the
professional duty to cite only verified authority is honoured, because the firewall
forced the reading that makes the advocate's certification TRUE.
"""
from __future__ import annotations

from .types import CiteStatus, FilingReport


def write_ledger(report: FilingReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_ledger(report))


def render_ledger(report: FilingReport) -> str:
    lines = [
        "PRIVATE VERIFICATION LEDGER — NOT FOR FILING",
        "This file is for the advocate's desk only. Do not annex it, do not e-mail it,",
        "do not let it enter the record. It exists so the advocate's own List of",
        "Authorities is honestly verified before it is signed.",
        "=" * 78,
        f"source: {report.source}",
        f"verdict: {report.verdict.value} — {report.summary()}",
        "=" * 78,
        "",
    ]
    traps = report.traps
    if traps:
        lines.append("DO NOT FILE — remove or replace these before anything else:")
        for c in traps:
            lines.append(f"  ✗ {c.raw.raw}   [{c.raw.case_name or 'name?'}]")
            for d in c.defects:
                lines.append(f"      {d.message}")
        lines.append("")
    if report.flags:
        lines.append("FIX / CONFIRM these:")
        for c in report.flags:
            lines.append(f"  ! {c.raw.raw}   [{c.raw.case_name or 'name?'}]")
            for d in c.defects:
                lines.append(f"      {d.message}")
                if d.fix:
                    lines.append(f"      → {d.fix}")
        lines.append("")
    if report.unverified:
        lines.append("READ EACH OF THESE AND TICK IT — until then it is unverified:")
        for c in report.unverified:
            lines.append(f"  [ ] {c.raw.raw}   [{c.raw.case_name or 'name?'}]")
            if c.raw.proposition:
                lines.append(f"        offered for: \"{c.raw.proposition}\"")
        lines.append("")
    if report.confirmed:
        lines.append("CONFIRMED by you:")
        for c in report.confirmed:
            lines.append(f"  [x] {c.raw.raw}   [{c.raw.case_name or 'name?'}]")
        lines.append("")
    return "\n".join(lines)


def write_list_of_authorities(report: FilingReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_list_of_authorities(report))


def render_list_of_authorities(report: FilingReport) -> str:
    """A clean, fingerprint-free List of Authorities the advocate finalises under
    his own hand. No tool name appears here by design."""
    lines = ["LIST OF AUTHORITIES", "", "Cases", "-----"]
    n = 0
    cases = [c for c in report.checks if c.raw.kind != "statute"
             and c.status is not CiteStatus.TRAP]
    for c in cases:
        n += 1
        name = c.raw.case_name or "____________________"
        lines.append(f"{n:>3}. {name}, {c.raw.raw}")
    if not cases:
        lines.append("   (none)")
    statutes_cited = [c for c in report.checks if c.raw.kind == "statute"]
    if statutes_cited:
        lines += ["", "Statutes referred", "-----------------"]
        for i, c in enumerate(statutes_cited, 1):
            lines.append(f"{i:>3}. {c.raw.raw}")
    lines += ["", "(Trap-flagged citations are deliberately omitted — resolve them"
              " in the private ledger before adding them here.)"]
    return "\n".join(lines)
