"""Render a FilingReport as a human report or as JSON."""
from __future__ import annotations

import json

from .types import CiteStatus, FilingReport, FilingVerdict

_MARK = {
    CiteStatus.TRAP: "[ TRAP  ]",
    CiteStatus.FLAG: "[ FLAG  ]",
    CiteStatus.UNVERIFIED: "[ READ? ]",
    CiteStatus.CONFIRMED: "[ OK ✓  ]",
}

_BANNER = {
    FilingVerdict.DO_NOT_FILE: "⛔  DO NOT FILE",
    FilingVerdict.VERIFY_BEFORE_FILING: "⚠️  VERIFY BEFORE FILING",
    FilingVerdict.FILING_SAFE: "✅  FILING-SAFE",
}


def format_report(report: FilingReport) -> str:
    out = ["=" * 78,
           f"VIDHI-DELTA · citation-verification filing firewall",
           f"source: {report.source}",
           "=" * 78,
           f"{_BANNER[report.verdict]} — {report.summary()}",
           ""]
    if not report.checks:
        out += [n for n in report.notes] + [""]
        out.append(_FOOTER)
        return "\n".join(out)

    # traps first, then flags, then the read-me list, then confirmed
    order = {CiteStatus.TRAP: 0, CiteStatus.FLAG: 1,
             CiteStatus.UNVERIFIED: 2, CiteStatus.CONFIRMED: 3}
    for c in sorted(report.checks, key=lambda x: order[x.status]):
        name = c.raw.case_name or "(case name not detected)"
        out.append(f"{_MARK[c.status]}  {c.raw.raw}")
        out.append(f"            {name}")
        for d in c.defects:
            out.append(f"            └─ {d.tier.value}: {d.message}")
            if d.fix:
                out.append(f"               → {d.fix}")
        if c.status is CiteStatus.UNVERIFIED:
            prop = c.raw.proposition or "(proposition not captured)"
            out.append(f"            offered for: \"{prop}\"")
            out.append(f"            → READ the authority and confirm it says this. "
                       f"Not yet verified.")
        out.append("")

    if report.notes:
        out.append("NOTES")
        for n in report.notes:
            out.append(f"  • {n}")
        out.append("")
    out.append(_FOOTER)
    return "\n".join(out)


def to_json(report: FilingReport) -> str:
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


_FOOTER = (
    "—" * 78 + "\n"
    "VIDHI-DELTA surfaces; it never certifies. A clean run is not a guarantee a\n"
    "citation is real — only that its coordinates are not impossible. Every [READ?]\n"
    "authority is YOURS to verify before it is filed. This report is a PRIVATE\n"
    "working file: it never enters a pleading and carries no place in the record.\n"
    "Decision-support, not legal advice."
)
