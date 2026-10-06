"""Helpers for writing the Hebrew copy of a part without touching its code.

    python scripts/he_tools.py show 05        # print the English template with code fences replaced by @@CODEn@@ / @@OUT@@
    python scripts/he_tools.py apply 05 FILE  # FILE = Hebrew text with the same markers -> series/classification/articles/he/05-*.md
    python scripts/he_tools.py links          # point links to parts that have a Hebrew copy at /he/..., drop "(באנגלית)"

Code blocks are copied from the English template byte for byte, so the Hebrew page prints exactly the same output
(the build fills every output block from the run). Only prose, headings, table headings and link text are translated.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "series" / "classification" / "articles"
HE = EN / "he"
FENCE = re.compile(r"```(\w*)\n(.*?)\n```", re.S)


def english(num: str) -> Path:
    return next(EN.glob(f"{num}-*.md"))


def split(text: str):
    """Return (marked_text, code_blocks) with every non-output fence replaced by a marker."""
    blocks: list[str] = []

    def sub(m: re.Match) -> str:
        if m.group(1) == "output":
            return "@@OUT@@"
        blocks.append(m.group(0))
        return f"@@CODE{len(blocks) - 1}@@"

    return FENCE.sub(sub, text), blocks


def show(num: str) -> None:
    marked, blocks = split(english(num).read_text(encoding="utf-8"))
    getattr(sys.stdout, "reconfigure", lambda **_: None)(encoding="utf-8")
    print(marked)
    print(f"\n[{len(blocks)} code blocks]")


def apply(num: str, src: str) -> None:
    en = english(num)
    _, blocks = split(en.read_text(encoding="utf-8"))
    text = Path(src).read_text(encoding="utf-8")
    for i, b in enumerate(blocks):
        assert f"@@CODE{i}@@" in text, f"missing @@CODE{i}@@"
        text = text.replace(f"@@CODE{i}@@", b)
    assert "@@CODE" not in text, "unknown code marker"
    text = text.replace("@@OUT@@", "```output\n(filled in by the build)\n```")
    HE.mkdir(parents=True, exist_ok=True)
    out = HE / en.name
    out.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT)}  {len(text.split())} words")


def links() -> None:
    have = {p.name.split("-")[0] for p in HE.glob("*.md")}
    changed = 0
    for f in HE.glob("*.md"):
        t = f.read_text(encoding="utf-8")

        def fix(m: re.Match) -> str:
            slug = m.group(1)
            if slug.split("-")[0] not in have:
                return m.group(0)
            return f"](/he/series/classification/{slug}/)"

        new = re.sub(r"\]\(/series/classification/(\d\d[a-z]?-[\w-]+)/\)", fix, t)
        # href="..." inside raw HTML (flowcharts)
        new = re.sub(r'href="/series/classification/(\d\d[a-z]?-[\w-]+)/"',
                     lambda m: f'href="/he/series/classification/{m.group(1)}/"' if m.group(1).split("-")[0] in have else m.group(0), new)
        # a link that now points to Hebrew no longer needs the "(באנגלית)" note right after it
        new = re.sub(r"(\]\(/he/series/classification/[\w-]+/\)) \(באנגלית\)", r"\1", new)
        if new != t:
            f.write_text(new, encoding="utf-8", newline="\n")
            changed += 1
    print(f"links updated in {changed} Hebrew templates")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "show":
        show(sys.argv[2])
    elif cmd == "apply":
        apply(sys.argv[2], sys.argv[3])
    elif cmd == "links":
        links()
