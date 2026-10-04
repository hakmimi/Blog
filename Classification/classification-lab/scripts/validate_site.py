"""Validate source completeness and the rendered Astro site."""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.urls: list[tuple[str, str]] = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("href", "src"):
            if key in values:
                self.urls.append((tag, values[key]))


def target_for(page: Path, url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme or url.startswith(("mailto:", "tel:", "#")):
        return None
    page_url = "/" + page.relative_to(DIST).as_posix()
    resolved = urlparse(urljoin(page_url, parsed.path)).path.lstrip("/")
    target = DIST / resolved
    if target.is_dir() or (not target.suffix and (target / "index.html").exists()):
        target = target / "index.html"
    return target


def main() -> None:
    errors: list[str] = []
    root_articles = ROOT / "src" / "content" / "articles"
    every = sorted(root_articles.rglob("*.md"))
    is_he = lambda a: a.relative_to(root_articles).parts[0] == "he"
    articles = [a for a in every if not is_he(a)]          # English parts: these are the ones indexed and searched
    he_articles = [a for a in every if is_he(a)]
    forbidden = re.compile(r"(TODO|lorem ipsum|placeholder image)", re.I)
    for article in every:
        text = article.read_text(encoding="utf-8")
        head = re.match(r"---\n(.*?)\n---", text, re.S)
        meta = head.group(1) if head else ""
        for field in ("title:", "description:", "series:", "date:", "keywords:"):
            if field not in meta:
                errors.append(f"{article.name} missing frontmatter {field}")
        body = text[head.end():] if head else text
        words = re.findall(r"[\w’'-]+", body) if is_he(article) else re.findall(r"[A-Za-z][A-Za-z’'-]*", body)
        if len(words) < 500:
            errors.append(f"{article.name} is unexpectedly short ({len(words)} words)")
        if forbidden.search(text):
            errors.append(f"unfinished marker in {article.name}")
        for alt in re.findall(r"!\[(.*?)\]\(", text):
            if not alt.strip():
                errors.append(f"empty figure alt text in {article.name}")

    for manifest_path in (ROOT / "series").glob("*/artifacts/data_manifest.json"):
        manifest = json.loads(manifest_path.read_text())
        if manifest["rows"] != 41188 or manifest["input_features"] != 20:
            errors.append(f"{manifest_path.parent.parent.name}: dataset manifest is not the full additional variant")

    html_pages = list(DIST.rglob("*.html"))
    broken: list[str] = []
    katex_pages = 0
    for page in html_pages:
        text = page.read_text(encoding="utf-8")
        parser = Links(); parser.feed(text)
        if 'class="katex"' in text:
            katex_pages += 1
        for _, url in parser.urls:
            target = target_for(page, url)
            if target is not None and not target.exists():
                broken.append(f"{page.relative_to(DIST)} -> {url}")
    if broken:
        errors.append("broken local links:\n  " + "\n  ".join(sorted(set(broken))))

    search = json.loads((DIST / "search-index.json").read_text(encoding="utf-8"))
    if len(search) != len(articles) or not all(x.get("text") for x in search):
        errors.append(f"search index has {len(search)} entries for {len(articles)} articles")
    if errors:
        raise SystemExit("VALIDATION FAILED\n" + "\n".join(errors))
    print(f"VALIDATION PASSED: {len(articles)} articles (+{len(he_articles)} Hebrew), {len(html_pages)} pages, no broken local links")


if __name__ == "__main__":
    main()
