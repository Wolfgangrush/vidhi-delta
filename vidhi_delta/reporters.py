"""Indian law-report registry + structural-plausibility checks.

The discipline here is PRECISION-FIRST. A citation earns a TRAP verdict only when
its coordinates are *impossible* — a year in the future, a court that did not yet
exist, a reporter volume that the series never reaches. An *unfamiliar* reporter
is never a trap (the firewall does not know every regional reporter, and nuking a
real citation it failed to recognise would be the worst failure of all); it is a
FLAG so the advocate confirms it. This is the same two-sided grade the PII auditor
uses: catch the fabrication (recall) without burning the reals (precision).

Nothing here is exhaustive. It is enough to catch the structurally-impossible
fabrications that an LLM most often invents. RSH-VERIFY everything else.
"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from .types import Defect, Tier

# Computed once. The floor guards against a machine clock set absurdly far back.
CURRENT_YEAR = max(date.today().year, 2026)


class Reporter:
    def __init__(self, key: str, name: str, since: int,
                 yearly_volume_cap: Optional[int] = None,
                 page_cap: int = 9999):
        self.key = key                          # token as it appears, e.g. "SCC"
        self.name = name
        self.since = since                      # first year of the series
        self.yearly_volume_cap = yearly_volume_cap  # max volume number within a year (None = no volume)
        self.page_cap = page_cap


# --- the registry -----------------------------------------------------------
# yearly_volume_cap is deliberately generous: SCC runs ~8-13 volumes a year, so 15
# is a safe ceiling that still catches "(2015) 99 SCC 5".
REPORTERS: Dict[str, Reporter] = {
    "SCC": Reporter("SCC", "Supreme Court Cases", since=1969, yearly_volume_cap=15),
    "SCR": Reporter("SCR", "Supreme Court Reports", since=1950, yearly_volume_cap=15),
    "SCALE": Reporter("SCALE", "SCALE", since=1980, yearly_volume_cap=20),
    "JT": Reporter("JT", "Judgments Today", since=1987, yearly_volume_cap=20),
    "AIR": Reporter("AIR", "All India Reporter", since=1914, yearly_volume_cap=None, page_cap=20000),
    "CriLJ": Reporter("CriLJ", "Criminal Law Journal", since=1904, yearly_volume_cap=None, page_cap=20000),
    "MhLJ": Reporter("MhLJ", "Maharashtra Law Journal", since=1962, yearly_volume_cap=12),
    "BomCR": Reporter("BomCR", "Bombay Cases Reporter", since=1985, yearly_volume_cap=12),
    "ALLMR": Reporter("ALLMR", "All Maharashtra Reporter", since=1999, yearly_volume_cap=12),
}

# Court tokens (for AIR "AIR <year> <COURT> <page>" and neutral SC/HC) with the
# year the court began sitting under that name. The Supreme Court of India began
# 26-01-1950 — "AIR 1949 SC ..." is therefore impossible.
COURT_SINCE: Dict[str, int] = {
    "SC": 1950, "SUPREME": 1950,
    # High Courts (rough founding years; only used to catch wild anachronisms)
    "BOM": 1862, "CAL": 1862, "MAD": 1862, "ALL": 1866, "DEL": 1966,
    "KAR": 1884, "KER": 1956, "AP": 1954, "TS": 2019, "GUJ": 1960,
    "MP": 1956, "RAJ": 1949, "PH": 1947, "PAT": 1916, "ORI": 1948,
    "JHAR": 2000, "UTT": 2000, "CHH": 2000, "HP": 1971, "GAU": 1948,
    "JK": 1928, "SIK": 1975, "MANI": 2013, "MEGH": 2013, "TRI": 2013,
}

# Neutral-citation systems and the year India switched them on. A neutral citation
# dated before the system existed is a fabrication tell.
NEUTRAL_SINCE: Dict[str, int] = {
    "INSC": 2023,   # Supreme Court of India neutral citations
    "BHC": 2023,    # Bombay High Court (e.g. 2023:BHC-NAG:1234)
    "DHC": 2023, "MHC": 2023, "KAR": 2021, "APHC": 2021, "TLHC": 2021,
    "PHHC": 2023, "ALD": 2023, "JKLHC": 2023, "CGHC": 2023, "RJ": 2023,
}


def _year_defect(year: int, lower: int, label: str) -> Optional[Defect]:
    if year > CURRENT_YEAR:
        return Defect(Tier.STRUCTURE, "year-in-future",
                      f"{label} is dated {year}, which is in the future "
                      f"(current year {CURRENT_YEAR}). A citation cannot post-date today.",
                      fix="This citation cannot exist. Remove it or find the real authority.")
    if year < lower:
        return Defect(Tier.STRUCTURE, "year-before-origin",
                      f"{label} is dated {year}, before it could exist "
                      f"(earliest possible {lower}).",
                      fix="Check the year — the series/court did not exist then. Likely fabricated.")
    return None


def check_reported(year: int, volume: Optional[int], reporter_token: str,
                   page: int) -> List[Defect]:
    """Plausibility of a reported citation like '(2014) 10 SCC 473'."""
    defects: List[Defect] = []
    rep = REPORTERS.get(_norm(reporter_token))
    if rep is None:
        defects.append(Defect(
            Tier.STRUCTURE, "reporter-unknown",
            f"'{reporter_token}' is not a reporter VIDHI-DELTA recognises. "
            f"That does not make it wrong — but it cannot be structurally checked.",
            fix="Confirm the reporter abbreviation and the citation by hand."))
        # Still apply a sane future-year guard even for unknown reporters.
        d = _year_defect(year, 1900, "This citation")
        if d:
            defects.append(d)
        return defects

    d = _year_defect(year, rep.since, f"This {rep.key} citation")
    if d:
        defects.append(d)

    if rep.yearly_volume_cap is not None and volume is not None:
        if volume < 1 or volume > rep.yearly_volume_cap:
            defects.append(Defect(
                Tier.STRUCTURE, "volume-impossible",
                f"{rep.key} volume {volume} is impossible — {rep.name} resets its "
                f"volume each year and never reaches {volume} (cap ~{rep.yearly_volume_cap}).",
                fix="A real-looking name welded to an impossible volume is the classic "
                    "fabricated-citation tell. Do not file."))

    if page < 1 or page > rep.page_cap:
        defects.append(Defect(
            Tier.STRUCTURE, "page-implausible",
            f"Page {page} is outside the plausible range for {rep.key}.",
            fix="Re-check the page number against the actual report."))
    return defects


def check_air(year: int, court_token: str, page: int) -> List[Defect]:
    """Plausibility of 'AIR 1973 SC 1461' / 'AIR 2019 Bom 45'."""
    defects: List[Defect] = []
    court = _norm(court_token).upper()
    since = COURT_SINCE.get(court)
    lower = since if since else 1914  # AIR itself since 1914
    d = _year_defect(year, lower, f"This AIR {court_token} citation")
    if d:
        defects.append(d)
    elif since and year < since:
        defects.append(Defect(
            Tier.STRUCTURE, "court-not-yet-existing",
            f"AIR {year} {court_token}: the {court_token} did not exist in {year} "
            f"(began {since}).",
            fix="Impossible coordinate — the court post-dates the citation year."))
    if page < 1 or page > 20000:
        defects.append(Defect(Tier.STRUCTURE, "page-implausible",
                              f"AIR page {page} is implausible.", fix="Re-check the page."))
    return defects


def check_neutral(year: int, system_token: str, number: int) -> List[Defect]:
    """Plausibility of '2023 INSC 456' / '2024:BHC-NAG:1234'."""
    defects: List[Defect] = []
    sys_key = _norm(system_token).upper().split("-")[0]
    since = NEUTRAL_SINCE.get(sys_key)
    if year > CURRENT_YEAR:
        defects.append(Defect(Tier.STRUCTURE, "year-in-future",
                              f"Neutral citation dated {year} is in the future.",
                              fix="Cannot exist — remove."))
    elif since and year < since:
        defects.append(Defect(
            Tier.STRUCTURE, "neutral-before-system",
            f"{system_token} neutral citations did not exist before {since}; "
            f"this one is dated {year}.",
            fix="A pre-{0} neutral citation is a fabrication tell. Do not file.".format(since)))
    elif since is None:
        defects.append(Defect(
            Tier.STRUCTURE, "neutral-system-unknown",
            f"Neutral-citation system '{system_token}' is not recognised.",
            fix="Confirm the court's neutral-citation prefix by hand."))
    if number < 1:
        defects.append(Defect(Tier.STRUCTURE, "number-impossible",
                              f"Neutral citation number {number} is impossible.",
                              fix="Re-check the running number."))
    return defects


def _norm(token: str) -> str:
    """Normalise a reporter/court token: strip dots, spaces, case-fold sensibly."""
    t = token.replace(".", "").replace(" ", "")
    aliases = {
        "scconline": "SCCOnLine", "crilj": "CriLJ", "cril.j": "CriLJ",
        "mhlj": "MhLJ", "bomcr": "BomCR", "allmr": "ALLMR",
    }
    return aliases.get(t.lower(), t)
