"""Command-line firewall. Usage:

    python -m vidhi_delta.cli check draft.docx
    python -m vidhi_delta.cli check draft.md --json
    python -m vidhi_delta.cli check draft.docx --out matter-42 --links

Exit code is the verdict, so it can gate a pre-filing hook:
    0 = FILING-SAFE   1 = VERIFY-BEFORE-FILING   2 = DO-NOT-FILE
"""
from __future__ import annotations

import argparse
import os

from . import online, report as _report
from .extract import read_document
from .firewall import check_document
from .ledger import (render_ledger, render_list_of_authorities,
                     write_ledger, write_list_of_authorities)
from .types import FilingVerdict

_EXIT = {
    FilingVerdict.FILING_SAFE: 0,
    FilingVerdict.VERIFY_BEFORE_FILING: 1,
    FilingVerdict.DO_NOT_FILE: 2,
}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="vidhi-delta",
        description="Citation-verification filing firewall for Indian pleadings. "
                    "Surfaces fabricated/unverified authority before you file. "
                    "Decision-support, not legal advice.")
    sub = p.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="check a draft's citations")
    c.add_argument("draft", help="path to the draft (.docx / .pdf / .md / .txt)")
    c.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON instead of a report")
    c.add_argument("--out", metavar="DIR",
                   help="also write vidhi-ledger.txt + list-of-authorities.txt + report.json")
    c.add_argument("--links", action="store_true",
                   help="print Indian Kanoon verification URLs (constructed locally; "
                        "the tool sends nothing)")
    args = p.parse_args(argv)

    if args.cmd != "check":
        p.print_help()
        return 0

    text = read_document(args.draft)
    rep = check_document(text, source=os.path.basename(args.draft))

    if args.json:
        print(_report.to_json(rep))
    else:
        print(_report.format_report(rep))
        if args.links:
            print()
            print(online.annotate_links(rep))

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        write_ledger(rep, os.path.join(args.out, "vidhi-ledger.txt"))
        write_list_of_authorities(rep, os.path.join(args.out, "list-of-authorities.txt"))
        with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fh:
            fh.write(_report.to_json(rep))
        print(f"\nWrote: {args.out}/vidhi-ledger.txt (private), "
              f"list-of-authorities.txt (clean), report.json")

    return _EXIT[rep.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
