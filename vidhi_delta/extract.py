"""Read a draft and find its citations — deterministically, with no model.

read_document() turns a .docx / .pdf / .md / .txt draft into plain text:
  * .docx  -> unzipped with the stdlib `zipfile`; word/document.xml is stripped of
              tags. NO python-docx, nothing to pip install, nothing leaves the box.
  * .pdf   -> shelled out to `pdftotext` if present; if absent, a clear error.
  * .md/.txt -> read as-is.

scan() then runs a fixed set of regexes over that text. This is the tool's only
'extraction boundary' — and unlike an LLM extractor it is fully deterministic, so
there is nothing to hallucinate here either. Every hit is shown back to the
advocate (in the report) before any weight is placed on it.
"""
from __future__ import annotations

import os
import re
import subprocess
import zipfile
from typing import List, Optional

from .types import RawCite

# --- document readers -------------------------------------------------------

def read_document(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return _read_docx(path)
    if ext == ".pdf":
        return _read_pdf(path)
    if ext in (".md", ".txt", ".markdown", ""):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    raise ValueError(f"Unsupported input type '{ext}'. Use .docx, .pdf, .md or .txt.")


def _read_docx(path: str) -> str:
    """Pull text out of a .docx by unzipping it — stdlib only."""
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist()
                 if n == "word/document.xml" or re.match(r"word/(header|footer)\d*\.xml", n)]
        if "word/document.xml" not in names:
            names.insert(0, "word/document.xml")
        chunks = []
        for n in names:
            try:
                xml = z.read(n).decode("utf-8", errors="replace")
            except KeyError:
                continue
            # paragraph and break boundaries -> newlines, so citations aren't fused
            xml = re.sub(r"</w:p>", "\n", xml)
            xml = re.sub(r"<w:br\s*/?>", "\n", xml)
            xml = re.sub(r"<[^>]+>", "", xml)        # strip every remaining tag
            chunks.append(xml)
    return _unescape_xml("\n".join(chunks))


def _read_pdf(path: str) -> str:
    if not _which("pdftotext"):
        raise RuntimeError(
            "Reading .pdf needs `pdftotext` (poppler), which isn't installed. "
            "Install poppler, or convert the draft to .docx/.txt first.")
    out = subprocess.run(["pdftotext", "-layout", path, "-"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {out.stderr.strip()}")
    return out.stdout


def _unescape_xml(s: str) -> str:
    return (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'"))


def _which(cmd: str) -> bool:
    return any(os.access(os.path.join(p, cmd), os.X_OK)
               for p in os.environ.get("PATH", "").split(os.pathsep) if p)


# --- citation scanners ------------------------------------------------------
# Years are matched loosely as 4 digits and judged for plausibility downstream,
# so that impossible years (future / pre-court) are SEEN, not silently skipped.

_PATTERNS = [
    # SCC OnLine database id: "2023 SCC OnLine SC 1234"
    ("scc-online", re.compile(
        r"\b(\d{4})\s+SCC\s+OnLine\s+([A-Za-z][A-Za-z&]*)\s+(\d{1,6})\b")),
    # neutral SC: "2023 INSC 456"
    ("neutral", re.compile(r"\b(\d{4})\s+INSC\s+(\d{1,6})\b")),
    # neutral HC colon form: "2024:BHC-NAG:1234"
    ("neutral", re.compile(r"\b(\d{4})\s*:\s*([A-Z]{2,}(?:-[A-Z]{2,5})?)\s*:\s*(\d{1,6})\b")),
    # reported, parenthesised year: "(2014) 10 SCC 473"
    ("reported", re.compile(
        r"\(\s*(\d{4})\s*\)\s+(\d{1,3})\s+([A-Za-z][A-Za-z.&]{1,12}?)\s+(\d{1,6})\b")),
    # AIR: "AIR 1973 SC 1461"
    ("air", re.compile(r"\bAIR\s+(\d{4})\s+([A-Za-z&]{1,8})\s+(\d{1,6})\b")),
]

# Statute references whose currency we track (the 01-07-2024 transition codes).
_STATUTE = re.compile(
    r"\b[Ss]ections?\s+(\d+[A-Za-z()]*)\s+(?:of\s+(?:the\s+)?)?"
    r"(Cr\.?\s?P\.?\s?C\.?|CrPC|Code of Criminal Procedure(?:,?\s*1973)?|"
    r"I\.?\s?P\.?\s?C\.?|IPC|Indian Penal Code(?:,?\s*1860)?|"
    r"Indian Evidence Act(?:,?\s*1872)?|Evidence Act(?:,?\s*1872)?|"
    r"BNSS|BNS|BSA)\b")


def scan(text: str) -> List[RawCite]:
    found: List[RawCite] = []
    seen_spans = []

    def overlaps(span):
        return any(span[0] < e and s < span[1] for (s, e) in seen_spans)

    for kind, pat in _PATTERNS:
        for m in pat.finditer(text):
            if overlaps(m.span()):
                continue
            seen_spans.append(m.span())
            found.append(RawCite(
                raw=m.group(0).strip(), kind=kind, span=m.span(),
                case_name=_case_name_before(text, m.start()),
                proposition=_sentence_around(text, m.start(), m.end())))

    for m in _STATUTE.finditer(text):
        if overlaps(m.span()):
            continue
        seen_spans.append(m.span())
        found.append(RawCite(
            raw=m.group(0).strip(), kind="statute", span=m.span(),
            case_name=None,
            proposition=_sentence_around(text, m.start(), m.end())))

    found.sort(key=lambda c: c.span[0])
    return found


_VS = re.compile(r"\b(?:v\.?|vs\.?|versus)\b", re.IGNORECASE)
# A sentence break is ". " only when the period follows TWO letters or a digit
# (so "procedure.", "India.", "473.", "1." break) — never a lone letter, which is
# an initial or the versus abbreviation ("v.", "P.V.", "P.K."). Indian case names
# are full of these, and naively splitting on ". " shreds them.
_SENT_BREAK = re.compile(r"(?:(?<=[A-Za-z]{2})|(?<=[0-9]))\.\s")


def _line_start(text: str, start: int) -> int:
    nl = text.rfind("\n", 0, start)
    return nl + 1 if nl != -1 else 0


def _case_name_before(text: str, start: int) -> Optional[str]:
    # bound to the current line, then to the last real sentence break within it
    window = text[max(_line_start(text, start), start - 160):start]
    seg = _SENT_BREAK.split(window)[-1]
    # drop a leading list marker / lead-in clause up to the last " in "/" see "
    for lead in (" in ", " See ", " see ", " per ", " viz ", " e.g. "):
        i = seg.rfind(lead)
        if i != -1:
            seg = seg[i + len(lead):]
            break
    seg = re.sub(r"^(?:see\s+also|see|also|viz|cf\.?|e\.g\.)\s+", "", seg, flags=re.IGNORECASE)
    seg = seg.strip(" ,;")
    if _VS.search(seg) and len(seg) >= 5:
        return re.sub(r"\s+", " ", seg)[:120].strip(" ,")
    return None


def _sentence_around(text: str, start: int, end: int) -> Optional[str]:
    # left bound: the start of the line (the numbered ground / paragraph), capped
    left = max(_line_start(text, start), start - 280)
    # right bound: the next real sentence break, or the end of the line
    m = _SENT_BREAK.search(text, end, end + 280)
    right = m.end() if m else min(len(text), end + 200)
    nl = text.find("\n", end, right)
    if nl != -1:
        right = nl
    snippet = re.sub(r"\s+", " ", text[left:right]).strip()
    return snippet[:240] if snippet else None
