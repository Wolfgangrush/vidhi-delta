"""Optional online-assist — and why it never opens a socket.

The most sovereign way to help the advocate verify a citation online is NOT to
fetch it for him (that would mean a network call, and the temptation to send more
than a citation string). It is to hand him the verification URL and let HIM click
it in his own browser, on his own account, leaving the tool with no egress at all.

So this module constructs search URLs. It does not call them. There is no
`requests`, no `urllib.request.urlopen`, no socket. The document text never leaves
the machine because the tool never sends anything — by construction, not by config.
"""
from __future__ import annotations

from urllib.parse import quote_plus

from .types import CitationCheck

INDIAN_KANOON = "https://indiankanoon.org/search/?formInput="
SCI_JUDGMENTS = "https://www.sci.gov.in/judgements-judgement-date/"


def verification_url(check: CitationCheck) -> str:
    """A query the advocate can click to find the authority himself."""
    name = check.raw.case_name or ""
    query = (name + " " + check.raw.raw).strip()
    return INDIAN_KANOON + quote_plus(query)


def annotate_links(report) -> str:
    lines = ["VERIFICATION LINKS (click each yourself — the tool sends nothing):", ""]
    for c in report.checks:
        if c.raw.kind == "statute":
            continue
        lines.append(f"{c.raw.raw}")
        lines.append(f"   {verification_url(c)}")
    return "\n".join(lines)
