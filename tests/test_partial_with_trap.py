"""The benchmark: a draft that is mostly clean reals WITH a trap hidden in it.

Graded two-sided, like the PII auditor:
  RECALL    — every planted trap is caught at the right severity.
  PRECISION — not one real citation is mis-flagged as a trap.

Run:  python -m unittest tests.test_partial_with_trap -v
"""
from __future__ import annotations

import json
import os
import unittest

from vidhi_delta import check_document
from vidhi_delta.types import CiteStatus, FilingVerdict, Tier

HERE = os.path.dirname(__file__)


def _norm(s: str) -> str:
    return " ".join(s.split()).strip()


class PartialWithTrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "corpus", "partial_with_trap.md"), encoding="utf-8") as fh:
            text = fh.read()
        with open(os.path.join(HERE, "corpus", "expected.json"), encoding="utf-8") as fh:
            cls.expected = json.load(fh)
        cls.report = check_document(text, source="partial_with_trap.md")
        cls.by_raw = {_norm(c.raw.raw): c for c in cls.report.checks}

    # --- RECALL: every trap caught ----------------------------------------
    def test_structural_traps_are_caught(self):
        traps = {_norm(c.raw.raw) for c in self.report.traps}
        for expected_trap in self.expected["traps"]:
            self.assertIn(_norm(expected_trap), traps,
                          f"MISSED TRAP (recall failure): {expected_trap}")

    def test_currency_deltas_are_flagged(self):
        for stat in self.expected["flags_currency"]:
            c = self.by_raw.get(_norm(stat))
            self.assertIsNotNone(c, f"currency citation not even detected: {stat}")
            self.assertIs(c.status, CiteStatus.FLAG, f"{stat} should be a FLAG")
            self.assertTrue(any(d.tier is Tier.CURRENCY for d in c.defects),
                            f"{stat} should carry a CURRENCY defect")

    # --- PRECISION: no real burned ----------------------------------------
    def test_real_citations_are_never_trapped(self):
        for real in self.expected["reals_must_be_unverified_never_trap"]:
            c = self.by_raw.get(_norm(real))
            self.assertIsNotNone(c, f"real citation not detected: {real}")
            self.assertIsNot(c.status, CiteStatus.TRAP,
                             f"PRECISION FAILURE — real citation flagged as trap: {real}")
            self.assertIs(c.status, CiteStatus.UNVERIFIED,
                          f"real citation should fall to UNVERIFIED (read-me), not "
                          f"{c.status.value}: {real}")

    # --- T3: proposition-trap is surfaced, never silently passed ----------
    def test_proposition_trap_is_surfaced_not_passed(self):
        pt = self.expected["proposition_trap"]
        c = self.by_raw.get(_norm(pt["citation"]))
        self.assertIsNotNone(c)
        self.assertIs(c.status, CiteStatus.UNVERIFIED,
                      "a real citation carrying a false proposition must be routed to "
                      "the human, never auto-passed")
        self.assertIsNotNone(c.raw.proposition, "the asserted proposition must be captured")
        self.assertIn(pt["proposition_contains"], c.raw.proposition.lower())

    # --- the document verdict ---------------------------------------------
    def test_document_verdict(self):
        self.assertIs(self.report.verdict, FilingVerdict.DO_NOT_FILE)
        self.assertEqual(self.report.verdict.value, self.expected["verdict"])

    # --- the firewall never blesses a fresh draft -------------------------
    def test_firewall_never_auto_blesses(self):
        self.assertEqual(len(self.report.confirmed), 0,
                         "a fresh run must produce ZERO confirmed citations — the "
                         "advocate's reading is the only path to confirmation")


if __name__ == "__main__":
    unittest.main()
