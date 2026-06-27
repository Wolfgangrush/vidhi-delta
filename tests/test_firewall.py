"""Unit tests for the deterministic checks. Stdlib unittest, zero dependencies."""
from __future__ import annotations

import unittest

from vidhi_delta import accept, check_document
from vidhi_delta.reporters import (CURRENT_YEAR, check_air, check_neutral,
                                    check_reported)
from vidhi_delta.statutes import check_currency
from vidhi_delta.types import CiteStatus, FilingVerdict


class ReporterPlausibility(unittest.TestCase):
    def test_good_scc_is_clean(self):
        self.assertEqual(check_reported(2014, 10, "SCC", 473), [])

    def test_future_year_is_impossible(self):
        codes = [d.code for d in check_reported(CURRENT_YEAR + 50, 7, "SCC", 1200)]
        self.assertIn("year-in-future", codes)

    def test_scc_volume_99_is_impossible(self):
        codes = [d.code for d in check_reported(2015, 99, "SCC", 5)]
        self.assertIn("volume-impossible", codes)

    def test_unknown_reporter_is_flag_not_trap(self):
        codes = [d.code for d in check_reported(2015, 3, "ZZZ", 10)]
        self.assertIn("reporter-unknown", codes)
        # not an impossible-coordinate code -> must not be trap-worthy
        self.assertNotIn("volume-impossible", codes)

    def test_air_sc_before_1950_is_impossible(self):
        codes = [d.code for d in check_air(1850, "SC", 12)]
        self.assertIn("year-before-origin", codes)

    def test_air_sc_1973_is_clean(self):
        self.assertEqual(check_air(1973, "SC", 1461), [])

    def test_neutral_before_system_is_impossible(self):
        codes = [d.code for d in check_neutral(2019, "INSC", 5)]
        self.assertIn("neutral-before-system", codes)

    def test_neutral_2024_is_clean(self):
        self.assertEqual(check_neutral(2024, "INSC", 716), [])


class StatuteCurrency(unittest.TestCase):
    def test_ipc_302_maps_to_bns(self):
        d = check_currency("IPC", "302")
        self.assertIsNotNone(d)
        self.assertIn("BNS s.103", d.fix)

    def test_evidence_65b_maps_to_bsa(self):
        d = check_currency("Evidence Act", "65B")
        self.assertIsNotNone(d)
        self.assertIn("BSA s.63", d.fix)

    def test_current_code_has_no_delta(self):
        self.assertIsNone(check_currency("BNSS", "483"))


class ConfirmGate(unittest.TestCase):
    def test_accept_is_the_only_path_to_filing_safe(self):
        text = ("The point is settled in A v. B, (2014) 10 SCC 473, and in "
                "C v. D, (2020) 7 SCC 1.")
        rep = check_document(text)
        self.assertIs(rep.verdict, FilingVerdict.VERIFY_BEFORE_FILING)
        self.assertEqual(len(rep.unverified), 2)
        # advocate confirms both after reading them
        accept(rep, ["(2014) 10 SCC 473", "(2020) 7 SCC 1"])
        self.assertIs(rep.verdict, FilingVerdict.FILING_SAFE)
        self.assertEqual(len(rep.confirmed), 2)

    def test_a_trap_blocks_filing_safe_even_after_accept(self):
        text = "See X v. Y, (2099) 7 SCC 1200 and Z v. W, (2014) 10 SCC 473."
        rep = check_document(text)
        accept(rep, ["(2014) 10 SCC 473", "(2099) 7 SCC 1200"])
        # a trap can never be confirmed away
        self.assertIs(rep.verdict, FilingVerdict.DO_NOT_FILE)


if __name__ == "__main__":
    unittest.main()
