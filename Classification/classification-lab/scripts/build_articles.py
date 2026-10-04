"""Render the Classification article templates from the experiment artifacts.

Templates live in series/classification/articles/NN-slug.md. A token of the form @@name@@ or @@name:arg|arg@@ is
replaced by a table or number computed from series/classification/artifacts, so a number in the prose cannot drift
from the experiment that produced it. Rendered files go to src/content/articles/classification/.

    python scripts/build_articles.py            # render all
    python scripts/build_articles.py 03 04      # selected parts
    python scripts/build_articles.py --check    # fail if a token is unknown or a rendered number is missing
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "series" / "classification" / "scripts"))
import article_data as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "series" / "classification" / "articles"
OUT = ROOT / "src" / "content" / "articles" / "classification"
TOKEN = re.compile(r"@@([A-Za-z0-9_]+)(?::([^@]*))?@@")


def write_retry(path: Path, text: str, tries: int = 8) -> None:
    """Windows can briefly lock a file the dev server is reading; retry instead of failing the whole render."""
    import time
    for i in range(tries):
        try:
            path.write_text(text, encoding="utf-8", newline="\n")
            return
        except OSError:
            time.sleep(0.5 * (i + 1))
    path.write_text(text, encoding="utf-8", newline="\n")


def render(text: str) -> str:
    def sub(m: re.Match) -> str:
        name, arg = m.group(1), m.group(2)
        fn = D.TOKENS.get(name)
        if fn is None:
            raise KeyError(f"unknown token @@{name}@@")
        args = arg.split("|") if arg else []
        return str(fn(*args))

    return TOKEN.sub(sub, text)


FENCE = re.compile(r"```(python|output)\n(.*?)\n```", re.S)
CACHE_FILE = ROOT / "series" / "classification" / "artifacts" / "snippet_cache.json"
DATA_DIR = ROOT / "series" / "classification" / "data" / "raw"


def run_snippets(text: str, name: str, cache: dict, force: bool = False) -> str:
    """Execute the python blocks of one article in order (one shared namespace, cwd = the data folder) and
    replace the *next* output block with what they printed. A block starting with '# schematic' is not run."""
    ns: dict = {"__name__": "__snippet__"}
    history = ""
    blocks: list[str] = []      # python blocks seen so far
    done = 0                    # how many of them have been executed in ns
    cwd0 = os.getcwd()
    pieces, pos, pending = [], 0, None        # pending: (index in pieces of the output block to fill, captured text)
    matches = list(FENCE.finditer(text))
    out_text = text
    replacements = []
    last_py_output = None
    for i, m in enumerate(matches):
        kind, body = m.group(1), m.group(2)
        if kind == "python":
            last_py_output = None
            if body.lstrip().startswith("# schematic"):
                continue
            history += body + "\n"
            key = hashlib.sha1(history.encode()).hexdigest()
            blocks.append(body)
            if key in cache and not force:
                captured = cache[key]
            else:
                # A changed block may use names defined by earlier blocks that came from the cache: run those first.
                for j in range(done, len(blocks) - 1):
                    with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        os.chdir(DATA_DIR)
                        try:
                            exec(compile(blocks[j], f"<{name} replay {j}>", "exec"), ns)
                        finally:
                            os.chdir(cwd0)
                buf = io.StringIO()
                cwd = os.getcwd()
                os.chdir(DATA_DIR)
                try:
                    with contextlib.redirect_stdout(buf), warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        exec(compile(body, f"<{name} block {i}>", "exec"), ns)
                finally:
                    os.chdir(cwd)
                captured = buf.getvalue().rstrip()
                cache[key] = captured
                done = len(blocks)
            last_py_output = captured
        elif kind == "output" and last_py_output is not None:
            replacements.append((m.start(2), m.end(2), last_py_output))
            last_py_output = None
    for a, b, new in reversed(replacements):
        out_text = out_text[:a] + new + out_text[b:]
    return out_text


def main() -> int:
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")]
    OUT.mkdir(parents=True, exist_ok=True)
    run = "--no-run" not in sys.argv
    cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}
    for f in sorted(SRC.glob("[0-9][0-9]*-*.md")):
        if wanted and f.name.split("-")[0] not in wanted:
            continue
        out = render(f.read_text(encoding="utf-8")).replace("\r\n", "\n")
        if run:
            out = run_snippets(out, f.name, cache, force="--force" in sys.argv)
            write_retry(CACHE_FILE, json.dumps(cache, indent=0))
        # remove the previously rendered file for this part (the slug may have changed)
        for old in OUT.glob(f"{f.name.split(chr(45))[0]}-*.md"):
            if old.name != f.name:
                old.unlink()
        write_retry(OUT / f.name, out)
        print(f"rendered {f.name}  {len(out.split())} words")
    return 0


if __name__ == "__main__":
    sys.exit(main())
