# VIDHI-DELTA — citation-verification filing firewall

**Vidhi Likhit family · private · v0.1.0-alpha**

> **विधि (vidhi)** — *law.* **delta** — *the gap, and the change.*
> VIDHI-DELTA reads a draft you are about to file, finds every case-law citation
> and statute reference in it, and measures the **delta between the authority you
> assert and the authority you can actually stand behind.** It catches the
> citations that *cannot exist* (a fabricated reporter, a court too young, a
> repealed Code cited as live), and it refuses to let the rest pass *as verified*
> until you have read them. Then it hands you a clean List of Authorities to sign —
> with no trace of the tool anywhere on it.

It runs **entirely on your own machine.** No internet. No cloud. **No AI reads your
draft** — extraction is plain regex, the law lives in code. That is not a setting
you switch on; it is how the tool is built. Sibling of **nyaya-check**
(cause-of-action checker) and **pramaan** (s.63 evidence integrity).

---

## Table of contents
1. [The problem, in one minute](#1-the-problem-in-one-minute)
2. [What VIDHI-DELTA does](#2-what-vidhi-delta-does)
3. [Install](#3-install)
4. [Quick start (copy-paste)](#4-quick-start-copy-paste)
5. [The four verdicts, per citation](#5-the-four-verdicts-per-citation)
6. [The document verdict + exit codes](#6-the-document-verdict--exit-codes)
7. [partial-with-trap — how it is graded](#7-partial-with-trap--how-it-is-graded)
8. [The two output files (and the wall between them)](#8-the-two-output-files-and-the-wall-between-them)
9. [Disclosure — the private-ledger resolution](#9-disclosure--the-private-ledger-resolution)
10. [Every command, explained](#10-every-command-explained)
11. [How it is built (for the technical reader)](#11-how-it-is-built-for-the-technical-reader)
12. [Privacy & the on-device wall](#12-privacy--the-on-device-wall)
13. [Testing it yourself](#13-testing-it-yourself)
14. [Limits, disclaimers & the RSH-VERIFY rule](#14-limits-disclaimers--the-rsh-verify-rule)
15. [Roadmap](#15-roadmap)
16. [Licence & firewall](#16-licence--firewall)

---

## 1. The problem, in one minute

A drafting model — or a tired junior — invents a citation. `Ramesh Kumar v. State,
(2099) 7 SCC 1200` *looks* exactly like a real Supreme Court citation. It is
impossible: 2099 is in the future, and SCC has never reached volume 99. Worse than
the obvious fake is the **subtle** one: a real case, correctly cited, offered for a
proposition it does not actually hold. File either and you risk the authority being
exposed in court — at best embarrassment, at worst sanctions
(*Mata v. Avianca*, 2023; Indian benches are now alert to the same).

You cannot catch these by re-reading the draft; the fakes are built to look right.
You need a gate that runs *between* "draft finished" and "draft filed" — and that
gate must do one honest thing: **separate what it can prove false, from what only
you, reading the case, can confirm true.**

## 2. What VIDHI-DELTA does

Four moves, on every citation it finds:

```
  ┌───────────┐   ┌──────────────┐   ┌─────────────────┐   ┌──────────────────┐
  │ read the  │ → │ find every   │ → │ check each one  │ → │ verdict + a clean│
  │ draft     │   │ citation     │   │ that CODE can:  │   │ List of          │
  │ (.docx…)  │   │ (regex)      │   │ structure /     │   │ Authorities you  │
  │           │   │              │   │ currency        │   │ sign yourself    │
  └───────────┘   └──────────────┘   └─────────────────┘   └──────────────────┘
```

- **Structure** — is the citation even *possible*? Future year, a court that did
  not exist, an SCC volume the series never reaches, a neutral citation before the
  neutral system began → **TRAP**.
- **Currency (the delta)** — does it cite a Code repealed on 01-07-2024 (CrPC → BNSS,
  IPC → BNS, Evidence Act → BSA) as if still governing? → **FLAG**, with the likely
  successor section.
- **Proposition** — does the case actually *hold* what the draft says? Code cannot
  know this offline. So the citation is never passed; it is routed to you as
  **UNVERIFIED**, with the sentence it was offered to support, to read and confirm.
- **It never blesses on its own.** A fresh run can never say "filing-safe". Only
  *you*, after reading, can confirm — and that is what makes your signature honest.

## 3. Install

VIDHI-DELTA needs **only Python 3.9+** — nothing to `pip install`.

```bash
cd ~/Desktop/vidhi-delta            # or wherever it lives
python3 -m vidhi_delta.cli check examples/sample_draft.md
```

`.docx` is read by unzipping it with Python's standard library (no `python-docx`).
`.pdf` input uses `pdftotext` (poppler) if you have it; otherwise convert to
`.docx`/`.txt` first. Optionally `pip install -e .` gives you a `vidhi-delta`
command instead of `python3 -m vidhi_delta.cli`.

## 4. Quick start (copy-paste)

```bash
# 1) check a draft, read the report
python3 -m vidhi_delta.cli check examples/sample_draft.md

# 2) check a real .docx and write the working files
python3 -m vidhi_delta.cli check ~/Desktop/AIO/SomeMatter/petition.docx --out run-01

#    -> run-01/vidhi-ledger.txt        (PRIVATE — your desk only, never filed)
#    -> run-01/list-of-authorities.txt (CLEAN  — finalise + sign this yourself)
#    -> run-01/report.json             (the structured result)

# 3) get one-click verification links (built locally; the tool sends nothing)
python3 -m vidhi_delta.cli check petition.docx --links

# 4) machine-readable
python3 -m vidhi_delta.cli check petition.docx --json
```

The command's **exit code is the verdict**, so it can gate a pre-filing hook:
`0` filing-safe · `1` verify-before-filing · `2` do-not-file.

## 5. The four verdicts, per citation

| Mark | Status | Meaning | What you do |
|---|---|---|---|
| `[ TRAP  ]` | **TRAP** | the coordinates are *impossible* — almost certainly fabricated | remove it / find the real authority. **Do not file.** |
| `[ FLAG  ]` | **FLAG** | a fixable defect — a repealed Code cited as live, an unknown reporter, an inconsistent parallel cite | fix or confirm before filing |
| `[ READ? ]` | **UNVERIFIED** | structurally plausible, but existence + proposition unconfirmed by code | **read the authority** and confirm it says what you claim |
| `[ OK ✓  ]` | **CONFIRMED** | *you* have personally verified it | nothing — it is verified, by you |

> **UNVERIFIED is not a pass.** It is a debt you discharge by reading. The whole
> design rests on the firewall refusing to pretend a structurally-perfect citation
> is *true* — because that is precisely where the dangerous fake hides.

## 6. The document verdict + exit codes

| Banner | Verdict | When | Exit |
|---|---|---|---|
| ⛔ **DO NOT FILE** | `DO_NOT_FILE` | ≥1 TRAP present | `2` |
| ⚠️ **VERIFY BEFORE FILING** | `VERIFY_BEFORE_FILING` | no traps, but unconfirmed / flagged authorities remain | `1` |
| ✅ **FILING-SAFE** | `FILING_SAFE` | every authority CONFIRMED by you, zero flags, zero traps | `0` |

A fresh run is **never** `FILING_SAFE` — the only path to it is confirming each
authority after you read it (see `accept()` in the API). The firewall cannot bless
a draft you have not verified.

## 7. partial-with-trap — how it is graded

The hard case is a draft that is **mostly clean reals with a trap hidden in it**.
VIDHI-DELTA is graded the way the PII-detector auditor is graded — **two-sided**:

- **RECALL** — every planted trap is caught at the right severity (the fabricated
  coordinates as TRAP, the dead-Code references as FLAG).
- **PRECISION** — **not one real citation is mis-flagged as a trap.** Nuking a real
  authority the tool failed to recognise would be the worst failure of all, so an
  *unfamiliar* reporter is never a trap — only a FLAG to confirm.

The benchmark (`tests/corpus/partial_with_trap.md` + `expected.json`,
checked by `tests/test_partial_with_trap.py`) plants four trap classes among five
real citations:

| Class | Example in the corpus | Caught as |
|---|---|---|
| **T1 fabricated coordinate** | `(2099) 7 SCC 1200`, `(2015) 99 SCC 5` | TRAP (deterministic) |
| **T2 anachronistic court** | `AIR 1850 SC 12` (SC since 1950) | TRAP (deterministic) |
| **T3 proposition-trap** | *Anvar P.V.* cited for "no certificate is required" | UNVERIFIED + the false proposition surfaced — never silently passed |
| **T4 currency delta** | `Section 302 IPC`, `Section 65B Evidence Act` | FLAG → BNS s.103 / BSA s.63 |

T3 is the point: code cannot know a real case is being mis-stated, so the firewall
does the one honest thing — it puts the sentence in front of you and makes you
confirm the case says it. The test asserts the fresh run confirms **nothing** on
its own.

## 8. The two output files (and the wall between them)

`--out DIR` writes two files on opposite sides of a hard wall:

- **`vidhi-ledger.txt` — PRIVATE.** Your worksheet. It lists every trap to remove,
  every delta to fix, and every authority still to be *read*, as tick-boxes. It is
  for your desk. **It never enters a filing.**
- **`list-of-authorities.txt` — CLEAN.** The ordinary List of Authorities that
  accompanies a pleading. **No tool name, no "AI", no watermark** — by construction
  (the build's test run greps it to prove zero fingerprint). You finalise it and
  sign it under your own hand. Trap-flagged citations are deliberately omitted.

## 9. Disclosure — the private-ledger resolution

A verification step naturally wants to emit a certificate — but a citation tool
should leave **no fingerprint of itself** on what is filed. VIDHI-DELTA resolves
this by **separating the artifacts and making the human verification real**:

> Every tool-touched artifact stays in the **private ledger**, which never enters
> the filing. The court sees only your **own attested List of Authorities** — which
> is *honest* because the firewall made you actually read each authority before you
> could call it safe. The duty to cite only verified authority is discharged by
> you; there is nothing about the tool in the filing to disclose, because the tool
> put nothing there.

This is enforced in code (`ledger.py`) and verified by a fingerprint grep in the
test run — the generated List of Authorities is asserted to contain no tool name.

## 10. Every command, explained

```bash
python3 -m vidhi_delta.cli check <DRAFT> [--json] [--out DIR] [--links]
```

| Option | What it does | Default |
|---|---|---|
| `<DRAFT>` | the draft to check: `.docx` / `.pdf` / `.md` / `.txt` | — |
| `--json` | emit the structured result as JSON instead of a report | off |
| `--out DIR` | also write `vidhi-ledger.txt` + `list-of-authorities.txt` + `report.json` | print only |
| `--links` | print Indian Kanoon verification URLs (constructed locally — the tool opens no socket) | off |

**Python API**

```python
from vidhi_delta import read_document, check_document, accept

report = check_document(read_document("petition.docx"), source="petition.docx")
print(report.summary())
for c in report.checks:
    print(c.status.value, c.raw.raw, "—", c.raw.case_name)

# after YOU have read them, confirm — the only path to FILING_SAFE:
accept(report, ["(1978) 1 SCC 248", "(2020) 7 SCC 1"])
```

## 11. How it is built (for the technical reader)

```
vidhi_delta/
  types.py        dataclasses + enums: Tier, CiteStatus, FilingVerdict, CitationCheck, FilingReport
  extract.py      read_document (.docx via stdlib zipfile, .pdf via pdftotext, .md/.txt) + regex scan
  reporters.py    Indian reporter registry + structural plausibility (precision-first)
  statutes.py     the 01-07-2024 currency map (CrPC→BNSS, IPC→BNS, Evidence→BSA)  ← legal content, human-authored
  firewall.py     the deterministic kernel — code decides; assigns TRAP/FLAG/UNVERIFIED; accept() for CONFIRMED
  ledger.py       the two artifacts + the wall between them (private ledger | clean List of Authorities)
  report.py       text report + JSON
  online.py       URL construction only — NO socket, by construction
  cli.py          the command-line firewall (exit code = verdict)
tests/            19 tests, stdlib unittest, zero dependencies, + the partial-with-trap benchmark
examples/         a sample draft to try
```

Design principles, inherited from the Vidhi Likhit family:
- **Deterministic core, zero dependencies** — nothing to hallucinate, nothing to
  install, runs anywhere Python runs.
- **AI reads nothing; code decides.** There is no model in this package at all.
  Extraction is regex; the law (reporter plausibility, statute currency) is code.
- **Precision-first.** Only the *impossible* earns a TRAP. The *unfamiliar* earns a
  FLAG. A real citation is never burned.
- **The firewall never blesses.** UNVERIFIED is the default; CONFIRMED is only ever
  set by the advocate.

## 12. Privacy & the on-device wall

- **No network.** The engine never opens a socket. `online.py` *constructs* search
  URLs for you to click yourself; it never calls them. Your draft never leaves the
  machine, because the tool never sends anything — by construction, not by config.
- **No model reads your draft.** Extraction is deterministic regex. There is no AI
  in the loop to leak to.
- **DPDP-aligned by construction.** Nothing is uploaded, so there is no third-party
  processing of personal data to account for.

## 13. Testing it yourself

```bash
python3 -m unittest discover -s tests -t .
# -> Ran 19 tests ... OK
```

The suite checks, among other things:
- impossible coordinates (future year, SCC vol 99, AIR-SC before 1950, neutral
  citation before the system existed) are caught as TRAP;
- an *unknown* reporter is a FLAG, never a TRAP (precision);
- the 01-07-2024 currency deltas map to the right successor sections;
- on the partial-with-trap corpus: every trap caught (recall) **and** every real
  citation left un-trapped (precision);
- a fresh run confirms nothing — `accept()` is the only path to FILING-SAFE;
- a trap can never be confirmed away.

Quick manual demo:
```bash
python3 -m vidhi_delta.cli check tests/corpus/partial_with_trap.md ; echo "exit=$?"
# ⛔ DO NOT FILE — 3 citation(s) look fabricated or impossible, out of 10 found.
# exit=2
```

## 14. Limits, disclaimers & the RSH-VERIFY rule

- **Not legal advice.** VIDHI-DELTA is decision-support. Your judgment governs.
- **A clean run is not a guarantee of truth.** It only means a citation's
  coordinates are not *impossible*. Whether the case exists and holds what you
  claim is the UNVERIFIED debt only you can discharge.
- **⚖️ RSH-VERIFY the statute map.** The CrPC/IPC/Evidence → BNSS/BNS/BSA section
  mappings are representative, not exhaustive — confirm each against the bare
  Sanhita before relying on it.
- **Coverage is finite.** The scanners catch SCC/SCR/AIR/SCC OnLine/INSC + colon-form
  neutral citations and the transition statutes. An unusual regional reporter may go
  undetected entirely — read the draft by eye too. Case-name detection is
  best-effort.
- **No `.pdf` without poppler.** Convert to `.docx`/`.txt` if `pdftotext` is absent.

## 15. Roadmap

- [ ] `confirm` subcommand: read a tick-list back in to mark authorities CONFIRMED and re-render the verdict
- [ ] more reporters (regional HC series), pin-cite range checks
- [ ] richer consistency: same case, contradictory parallel citations across series
- [ ] optional one-shot **local** verification against an offline Indian Kanoon mirror
- [ ] `.docx` output for the List of Authorities (open-in-Word ready)
- [ ] a pre-filing hook example (exit-code gate) for the drafting pipeline
- [ ] RSH-VERIFY: confirm the full CrPC/IPC/Evidence → Sanhita section maps

## 16. Licence & firewall

- **Private.** All rights reserved (RSH). Not for distribution.
- **No public release** without an explicit go and a clean leak/AAAK audit.
- **Brand:** Vidhi Likhit. **Part of:** the nyaya-check / pramaan / Vidhi Likhit
  lawtech family.
