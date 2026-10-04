"""Build one self-contained, white, print-friendly HTML file for a series from the built site.

    npm run build
    python scripts/build_print.py [series] [--dist dist] [--out print/<series>.html]

Reads dist/series/<series>/NN-*/index.html, keeps the article text, tables and figures (embedded as base64),
turns code into plain monospace, and replaces interactive widgets with a note pointing to the online post.
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: #111; font: 11pt/1.55 "Segoe UI", Georgia, "Times New Roman", serif; }
main { max-width: 820px; margin: 0 auto; padding: 24px 20px 60px; }
h1, h2, h3, h4 { font-family: "Segoe UI", Arial, sans-serif; color: #000; line-height: 1.2; }
h1 { font-size: 24pt; margin: .2em 0 .3em; }
h2 { font-size: 16pt; margin: 1.6em 0 .5em; padding-bottom: .15em; border-bottom: 1.5px solid #222; }
h3 { font-size: 13pt; margin: 1.3em 0 .4em; }
h4 { font-size: 11.5pt; margin: 1.1em 0 .3em; }
p, li { orphans: 3; widows: 3; }
a { color: #0a3d91; text-decoration: none; }
.part { page-break-before: always; }
.part:first-of-type { page-break-before: auto; }
.eyebrow { text-transform: uppercase; letter-spacing: .08em; font-size: 9pt; color: #555; font-family: Arial, sans-serif; }
.lede { font-size: 12.5pt; color: #333; }
.byline { color: #666; font-size: 9.5pt; }
pre { background: #f4f4f4; border: 1px solid #ccc; border-radius: 4px; padding: 8px 10px; font: 8.6pt/1.45 Consolas, "Courier New", monospace; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; margin: .5em 0 1em; }
pre[data-language="output"] { background: #fff; border-left: 4px solid #888; }
pre[data-language]::before { content: attr(data-language); display: block; font: 700 7pt Arial, sans-serif; letter-spacing: .1em; text-transform: uppercase; color: #666; margin-bottom: 4px; }
code { font-family: Consolas, "Courier New", monospace; font-size: .9em; background: #f1f1f1; padding: 0 3px; border-radius: 3px; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: .8em 0 1.2em; page-break-inside: avoid; }
th, td { border: 1px solid #999; padding: 4px 7px; text-align: left; vertical-align: top; }
th { background: #eaeaea; }
img { max-width: 100%; height: auto; display: block; margin: .8em auto .2em; page-break-inside: avoid; }
em { color: #333; }
blockquote { margin: 1em 0; padding: .3em 1em; border-left: 4px solid #999; background: #f7f7f7; }
.callout { border: 1px solid #999; border-left: 5px solid #444; border-radius: 4px; padding: 6px 12px; margin: 1em 0; background: #f9f9f9; page-break-inside: avoid; }
.callout.gotcha { border-left-color: #b00020; }
.callout.tip { border-left-color: #b8860b; }
.widget { border: 1.5px dashed #777; border-radius: 4px; padding: 8px 12px; margin: 1em 0; color: #333; background: #fafafa; font-size: 10pt; }
.toc { page-break-after: always; }
.toc li { margin: .25em 0; }
.cover { text-align: left; padding: 60px 0 30px; }
.cover h1 { font-size: 30pt; }
.notes { margin-top: 1.5em; border: 1px solid #bbb; padding: 10px; }
.notes h3 { margin-top: 0; }
.notes .lines { height: 120px; background: repeating-linear-gradient(#fff, #fff 23px, #ccc 24px); }
.ae-map { --accent:#0a7f76; --accent-soft:#d9f2ef; --surface:#fff; --ghost:#888; --ink:#111; --muted:#555; --line:#bbb; --ok:#0a7f76; border:1px solid #bbb; padding:6px; margin:1em 0; page-break-inside: avoid; }
.ae-map svg { width: 100%; height: auto; min-width: 0; }
.ae-map .node-new rect { fill: var(--accent-soft); stroke: var(--accent); stroke-width: 1.6; }
.ae-map .node-changed rect { fill: #fff; stroke: var(--accent); stroke-width: 1.6; stroke-dasharray: 6 3; }
.ae-map .node-existing rect { fill: #fff; stroke: var(--line); stroke-width: 1.2; }
.ae-map .node-external rect { fill: #fff; stroke: var(--ink); stroke-width: 1.2; }
.ae-map .node-ghost rect { fill: none; stroke: var(--ghost); stroke-width: 1.2; stroke-dasharray: 5 4; }
.ae-map .node-existing .t { fill: var(--muted); } .ae-map .node-ghost .t, .ae-map .node-ghost .s { fill: var(--ghost); }
.ae-map .nt { font-size: 14px; font-weight: 600; fill: var(--ink); } .ae-map .ns { font-size: 11.5px; fill: var(--muted); }
.ae-map .lane, .ae-map .el { font-family: Consolas, monospace; fill: var(--muted); } .ae-map .lane { font-size: 11px; } .ae-map .el { font-size: 10.5px; }
.ae-map .edge { fill: none; stroke: var(--accent); stroke-width: 1.5; } .ae-map .edge-old { fill: none; stroke: var(--muted); stroke-width: 1.2; }
.ae-map .edge-back { fill: none; stroke: var(--ok); stroke-width: 1.5; } .ae-map .edge-ghost { fill: none; stroke: var(--ghost); stroke-width: 1.1; stroke-dasharray: 3 3; }
.ae-map .elbg { fill: #fff; }
.ae-legend { --accent:#0a7f76; --accent-soft:#d9f2ef; --ghost:#888; display:flex; flex-wrap:wrap; gap:.3rem 1rem; font-size:9pt; color:#555; }
.ae-legend i { display:inline-block; width:18px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px; }
.ae-quiz details { border:1px solid #bbb; border-radius:4px; padding:6px 10px; margin:.5em 0; page-break-inside: avoid; }
.ae-quiz summary { font-weight:700; }
@media print { a { color: #000; } main { padding: 0; } .part { page-break-before: always; } }
"""


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"

RTL_CSS = """
body { font-family: "Segoe UI", "Arial Hebrew", Arial, sans-serif; }
pre, code, .katex, .katex-display, table { direction: ltr; unicode-bidi: isolate; text-align: left; }
.prose table th, .prose table td, table th, table td { text-align: right; }
ul, ol { padding-right: 1.4em; padding-left: 0; }
blockquote, .callout { border-left: 0; border-right: 4px solid #888; }
"""


def clean_article(page: Path, dist: Path, base: str, he: bool = False) -> tuple[str, str]:
    soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
    hero = soup.select_one(".article-hero")
    prose = soup.select_one(".prose")
    title = hero.select_one("h1").get_text(" ", strip=True)

    for pre in prose.select("pre"):
        text = pre.get_text()
        lang = pre.get("data-language") or "text"
        for a in list(pre.attrs):
            del pre[a]
        pre["data-language"] = lang
        pre.clear()
        code = soup.new_tag("code")
        code.string = text.rstrip("\n")
        pre.append(code)
    for wrap in prose.select("div.codeblock"):
        wrap.unwrap()
    for bar in prose.select(".codebar"):
        bar.decompose()
    for svg in prose.select("svg"):
        svg.attrs.pop("style", None)
    for d in prose.select("details"):
        d["open"] = ""
    for s in prose.select("script, style, button"):
        s.decompose()
    for w in prose.select("div.threshold-lab, div.prior-shift-lab, div.sigmoid-lab, div.apple-grid-lab"):
        note = soup.new_tag("div", attrs={"class": "widget"})
        note.string = ("ווידג׳ט אינטראקטיבי (מחוונים וגרפים חיים). פתחו את הפוסט באתר כדי להשתמש בו: " if he else "Interactive widget (slider and live charts). Open the online post to use it: ") + title
        w.replace_with(note)

    for img in prose.select("img"):
        src = img.get("src", "")
        rel = src[len(base):] if src.startswith(base) else src
        f = dist / rel.lstrip("/")
        if f.exists():
            img["src"] = data_uri(f)
        for a in ("srcset", "sizes", "loading", "decoding", "width", "height", "style", "class"):
            img.attrs.pop(a, None)
    for a in prose.select("a[href]"):
        h = a["href"]
        m = re.search(r"/series/[\w-]+/(\d\d[a-z]?)-[\w-]+/?(#.*)?$", h)
        if m:
            a["href"] = f"#part-{m.group(1)}"

    eyebrow = hero.select_one(".eyebrow").get_text(" ", strip=True)
    lede = hero.select_one(".lede").get_text(" ", strip=True)
    byline = hero.select_one(".byline").get_text(" ", strip=True)
    num = page.parent.name.split("-")[0]
    html = (f'<section class="part" id="part-{num}"><p class="eyebrow">{eyebrow}</p><h1>{title}</h1>'
            f'<p class="lede">{lede}</p><p class="byline">{byline}</p>{prose.decode_contents()}'
            f'<div class="notes"><h3>{"ההערות שלי" if he else "My notes"}</h3><div class="lines"></div></div></section>')
    return title, html


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("series", nargs="?", default="classification")
    ap.add_argument("--dist", type=Path, default=Path("dist"))
    ap.add_argument("--out", type=Path)
    ap.add_argument("--title", help="cover title (default: the series slug)")
    ap.add_argument("--lang", choices=["en", "he"], default="en", help="he builds the Hebrew right-to-left edition from dist/he/series")
    ap.add_argument("--base", default="", help="site base path prefix used in the build, e.g. /Blog")
    args = ap.parse_args()
    he = args.lang == "he"
    out = args.out or Path("print") / (f"{args.series}-he.html" if he else f"{args.series}.html")

    pages = sorted(((args.dist / "he" if he else args.dist) / "series" / args.series).glob("[0-9][0-9]*-*/index.html"))
    if not pages:
        print("no built pages found; run `npm run build` first", file=sys.stderr)
        return 1
    parts = [clean_article(p, args.dist, args.base, he) for p in pages]
    pk = lambda p: p.parent.name.split("-")[0]
    word = "חלק" if he else "Part"
    toc = "".join(f'<li><a href="#part-{pk(p)}">{word} {pk(p).lstrip("0") or "0"}. {t}</a></li>'
                  for p, (t, _) in zip(pages, parts))
    cover = (f'<div class="cover"><p class="eyebrow">Applied ML Notebook</p><h1>{args.title or args.series.replace("-", " ").title()}</h1>'
             f'<p class="lede">{"מהדורה להדפסה. האיורים משובצים; ווידג׳טים אינטראקטיביים הוחלפו בהערה." if he else "Printable edition. Figures are embedded; interactive widgets are replaced by a note."}</p></div>'
             f'<div class="toc"><h2>{"תוכן עניינים" if he else "Contents"}</h2><ol style="list-style:none;padding:0">{toc}</ol></div>')
    html = (f'<!doctype html><html lang="{args.lang}" dir="{'rtl' if he else 'ltr'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{args.series} (printable)</title><style>{CSS}{RTL_CSS if he else ""}</style></head><body><main>{cover}'
            + "".join(h for _, h in parts) + "</main></body></html>")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"{out}  {len(parts)} parts  {out.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
