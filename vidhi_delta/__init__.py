"""VIDHI-DELTA — citation-verification filing firewall (Vidhi Likhit family).

The delta between asserted authority and verified authority — measured, and not
let past the threshold unmeasured. Sibling of nyaya-check (cause-of-action checker)
and pramaan (s.63 evidence integrity): same house rules — deterministic core, zero
third-party dependencies, no model in the loop, on-device by construction.

Public API:
    from vidhi_delta import check_document, check_citation
    from vidhi_delta import FilingReport, CitationCheck, CiteStatus, FilingVerdict
"""
from __future__ import annotations

from .extract import read_document, scan
from .firewall import accept, check_citation, check_document
from .types import (CitationCheck, CiteStatus, Defect, FilingReport,
                    FilingVerdict, RawCite, Tier)

__all__ = [
    "read_document", "scan",
    "check_document", "check_citation", "accept",
    "CitationCheck", "CiteStatus", "Defect", "FilingReport",
    "FilingVerdict", "RawCite", "Tier",
]

__version__ = "0.1.0a0"
