"""Run every ```python block of an article, in order, in one namespace, from the series data folder.

    python scripts/check_snippets.py 05 08        # chapters by number
    python scripts/check_snippets.py              # all

A block is skipped if its first line is `# no-run`. Blocks that end in `...` placeholders are skipped too.
Exit code 1 if any chapter raises.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "src" / "content" / "articles" / "classification"
CWD = ROOT / "series" / "classification" / "data" / "raw"
PRELUDE = '''import warnings; warnings.filterwarnings("ignore")
import sys; sys.path.insert(0, r"%s")
''' % (ROOT / "series" / "classification" / "scripts")

def blocks(text: str):
    for m in re.finditer(r"```python\n(.*?)```", text, re.S):
        code = m.group(1)
        if code.lstrip().startswith("# no-run") or "..." in code.replace("...)", "").replace("[...]", "") and re.search(r"^\s*\.\.\.\s*$", code, re.M):
            continue
        yield code

def main() -> int:
    wanted = sys.argv[1:]
    failures = 0
    for path in sorted(ARTICLES.glob("*.md")):
        if wanted and path.name[:2] not in wanted:
            continue
        code = PRELUDE + "\n".join(blocks(path.read_text(encoding="utf-8")))
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
        r = subprocess.run([sys.executable, f.name], cwd=CWD, capture_output=True, text=True)
        status = "ok " if r.returncode == 0 else "FAIL"
        print(f"{status} {path.name}")
        if r.returncode:
            failures += 1
            print(r.stderr[-1500:])
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
