---
title: "Day 27: Green on Every Push"
description: "From checks you remember to run to checks that run themselves. Every push now goes through lint, a secret scan, the full offline test suite and a coverage gate on GitHub Actions, and configuration is documented in a .env.example that a test keeps honest."
series: "ai-engineering"
order: 29
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "github actions", "ruff", "secret scan", "coverage gate"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day27`](https://github.com/hakmimi/AIEngineering/tree/main/Day27). Layers touched: L4 System.

## Goals

- **G1. Set up a CI workflow that runs the same checks on every push.**  
  You can: walk `.github/workflows/ci.yml` step by step and say why it needs no repository secrets.
- **G2. Keep secrets out of the repo with an automated scan.**  
  You can: run `python -m scripts.check_secrets` and explain what it flags and what it skips.
- **G3. Make configuration a tested contract.**  
  You can: show `.env.example` and the test that fails when the code reads a variable it doesn't list.
- **G4. Add lint rules that find likely bugs, not just style.**  
  You can: explain one `ruff` finding that was fixed, like `zip(..., strict=True)`.

## System map

The runtime system is the same as Day 26. The new map is the delivery path: what happens between `git push` and a green or red badge.

> Code push → GitHub Actions → install dependencies → ruff → secret scan → pytest + coverage gate → pass/fail signal

<div class="ae-map" role="img" aria-label="A developer pushes to main or a development branch. GitHub Actions reads ci.yml at the repository root, sets up Python 3.13 with a pip cache in the folder named by env.PROJECT and installs requirements-dev.txt. It runs ruff with the rules in pyproject.toml over code that had 35 lint findings fixed, then check_secrets.py, then pytest with a 95 % coverage gate, which includes the new repo-hygiene tests that keep .env.example in sync with the code. The result is a pass or fail signal and the README badge."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 492" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">DEVELOPER</text><text class="lane" x="264" y="18">GITHUB ACTIONS</text><text class="lane" x="508" y="18">CHECKS</text><text class="lane" x="752" y="18">PROJECT · DAY27</text><text class="lane" x="996" y="18">SIGNAL</text><path class="edge" d="M200,191 C230,191 230,138 261,138" marker-end="url(#mka)"></path><path class="edge-old" d="M354,180 L354,199" marker-end="url(#mkm)"></path><path class="edge" d="M444,244 C474,244 474,85 505,85" marker-end="url(#mka)"></path><path class="edge" d="M444,244 C474,244 474,191 505,191" marker-end="url(#mka)"></path><path class="edge" d="M444,244 C474,244 474,297 505,297" marker-end="url(#mka)"></path><path class="edge" d="M688,85 C718,85 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M688,297 C718,297 718,191 749,191" marker-end="url(#mka)"></path><path class="edge" d="M842,242 L842,261" marker-end="url(#mka)"></path><path class="edge" d="M688,297 C840,297 840,191 993,191" marker-end="url(#mka)"></path><path class="edge-back" d="M1086,233 V374 H110 V224" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="160"></rect><text class="nt t" text-anchor="middle" x="110" y="184">git push / PR</text><text class="ns s" text-anchor="middle" x="110" y="204">main · development/**</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="96"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="128">ci.yml</text><text class="ns s" text-anchor="middle" x="354" y="147">repo root · env.PROJECT</text><text class="ns s" text-anchor="middle" x="354" y="162">Python 3.13 + pip cache</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="109">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="202"></rect><text class="nt t" text-anchor="middle" x="354" y="234">pip install</text><text class="ns s" text-anchor="middle" x="354" y="253">requirements-dev.txt</text><text class="ns s" text-anchor="middle" x="354" y="268">+ pytest-cov, pyyaml</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="215">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="43"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="75">ruff check .</text><text class="ns s" text-anchor="middle" x="598" y="94">pyproject.toml</text><text class="ns s" text-anchor="middle" x="598" y="109">F · E4/7/9 · I · B</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="56">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="149"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="181">check_secrets.py</text><text class="ns s" text-anchor="middle" x="598" y="200">sk-… keys · literal</text><text class="ns s" text-anchor="middle" x="598" y="215">OPENAI_API_KEY=</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="162">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="255"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="287">pytest --cov</text><text class="ns s" text-anchor="middle" x="598" y="306">--cov-fail-under=95</text><text class="ns s" text-anchor="middle" x="598" y="321">no API key</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="268">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" text-anchor="middle" x="842" y="66">app code</text><text class="ns s" text-anchor="middle" x="842" y="85">35 lint findings fixed</text><text class="ns s" text-anchor="middle" x="842" y="100">zip(strict=True)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">CHANGED</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="752" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="172">test_repo_hygiene</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="190">.py</text><text class="ns s" text-anchor="middle" x="842" y="209">8 tests: config, secrets</text><text class="ns s" text-anchor="middle" x="842" y="224">CI file, .dockerignore</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="264"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="296">.env.example</text><text class="ns s" text-anchor="middle" x="842" y="315">every variable the</text><text class="ns s" text-anchor="middle" x="842" y="330">code reads</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="277">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="149"></rect><text class="nt t" text-anchor="middle" x="1086" y="181">pass / fail</text><text class="ns s" text-anchor="middle" x="1086" y="200">README badge</text><text class="ns s" text-anchor="middle" x="1086" y="215">Actions tab</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="162">NEW</text></g><rect class="elbg" height="15" rx="3" width="53" x="204" y="148"></rect><text class="el" text-anchor="middle" x="230" y="158">trigger</text><rect class="elbg" height="15" rx="3" width="59" x="846" y="240"></rect><text class="el" text-anchor="start" x="848" y="252">in sync?</text><rect class="elbg" height="15" rx="3" width="78" x="559" y="367"></rect><text class="el" text-anchor="middle" x="598" y="378">green / red</text><text class="lane" style="fill:var(--ghost)" x="20" y="422">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="254" x="20" y="432"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="147" y="459">Day 28 · portfolio packaging</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="294" y="432"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="424" y="459">Day 29 · decision agent starts</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Checks that depend on memory

- Tests, lint and coverage ran only when someone remembered to run them
- No list of the environment variables the app reads
- The root `.gitignore` rule `.env.*` would also have hidden `.env.example`
- Nothing stopped a key pasted into a file from being committed

### After this episode: Checks that run themselves

- `ci.yml` at the repo root: install → `ruff` → secret scan → `pytest` with a 95 % coverage gate
- `.env.example` lists every variable, and a test fails if code and file drift apart
- `scripts/check_secrets.py` fails the build on `sk-…` keys or a literal `OPENAI_API_KEY=`
- `!.env.example` in `.gitignore`; 35 lint findings fixed; 400 tests, 99.21 % coverage in a clean venv

> **Why it matters:** a check that depends on someone remembering it will eventually be skipped. CI makes "the tests pass" a fact attached to every commit, and running with no API key means any fork or pull request can be verified without trusting anyone with a secret.

## Code walkthrough

Five snippets: the workflow, the lint config, the secret scanner, the config-sync test and one lint fix.

### .github/workflows/ci.yml · the pipeline

```yaml
env:
  PROJECT: Day56
...
jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ${{ env.PROJECT }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
      ...
      - name: Lint (ruff)
        run: ruff check .
      - name: Secret scan
        run: python -m scripts.check_secrets
      # No OPENAI_API_KEY here on purpose: the whole suite is offline (LLM/embeddings are faked).
      - name: Tests + coverage gate
        run: python -m pytest --cov=. --cov-report=term --cov-fail-under=95
```

**One job, four checks, zero secrets.** On Day 27 `PROJECT` pointed at `Day27`; the repo file has since moved on to the newest folder. `--cov-fail-under=95` turns coverage from a number you look at into a gate that fails the build.

### pyproject.toml · lint that finds bugs

```toml
[tool.ruff.lint]
# E4/E7/E9 + F = pyflakes-class correctness errors; I = import order; B = likely bugs (bugbear)
select = ["E4", "E7", "E9", "F", "I", "B"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["B011", "B017"]          # tests intentionally use bare assert False / broad raises in a few places
"scripts/*" = ["E402"]                # scripts adjust global state (memory store) before importing the app
```

**Narrow on purpose: correctness, import order, likely bugs.** `ruff format --check` was left out, because reformatting the whole code base would bury the real changes. Every ignore has a comment saying why.

### scripts/check_secrets.py · what counts as a secret

```python
SKIP_FILES = {".env"}                                    # local secrets file: git-ignored on purpose
KEY_PATTERN = re.compile(r"sk-(?:proj-)?[A-Za-z0-9_\-]{20,}")
ASSIGNMENT = re.compile(r"OPENAI_API_KEY\s*=\s*['\"]?([^\s'\"#]{12,})")
PLACEHOLDERS = ("your-key-here", "xxxxxxxx", "<", "changeme")


def scan_text(text: str) -> list[str]:
    findings = []
    for match in KEY_PATTERN.finditer(text):
        if not any(p in match.group(0).lower() for p in PLACEHOLDERS):
            findings.append(f"key-like token {match.group(0)[:8]}...")
```

**Flag the shape of a key, and never print the whole thing.** Findings show only the first 8 characters, so the scanner's own output can't leak a key into CI logs. Keep the highlighted pattern in mind for the break-it segment.

### tests/test_repo_hygiene.py · config stays documented

```python
def _env_vars_used_in_code() -> set[str]:
    names = set()
    for path in SOURCE_FILES:
        names |= set(re.findall(r'getenv\("([A-Z][A-Z0-9_]+)"', path.read_text(encoding="utf8")))
    return names
...
def test_env_example_lists_every_variable_the_code_reads():
    used, documented = _env_vars_used_in_code(), _env_vars_in_example()
    assert used, "found no getenv calls - the scan is broken"
    assert not used - documented, f"missing from .env.example: {sorted(used - documented)}"
```

**Documentation that's tested can't go stale.** A set difference in each direction: nothing the code reads is missing from the example, and nothing in the example is dead. The `assert used` line guards against a scan that silently finds nothing.

### similarity.py · a lint fix that matters

```python
def cosine_similarity(a: list[float], b :list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Vectors must have the same dimension")

    dot_product = sum(x * y for x,y in zip(a,b, strict=True))
```

**Plain `zip` stops at the shorter list without a word.** Bugbear rule B905 asks you to say what should happen when lengths differ. Here they must match, so `strict=True` makes a mismatch raise instead of quietly computing a wrong score.

## Run it

Run from `Day27` in PowerShell, in the same order as the CI job, with the key cleared like on the runner.

**Step 1**

```powershell
pip install -r requirements-dev.txt
$env:OPENAI_API_KEY=""
```

**Expect:** Dev tools installed, including `pytest-cov` and `pyyaml`. No key in this shell.

**Step 2**

```text
ruff check .
```

**Expect:** `All checks passed!`

**Step 3**

```powershell
python -m scripts.check_secrets
```

**Expect:** `no secrets found`, exit code 0. Your real `.env` is skipped on purpose.

**Step 4**

```powershell
python -m pytest --cov=. --cov-fail-under=95
```

**Expect:** `400 passed` and `Required test coverage of 95% reached`, about 99 %.

**Step 5**

```powershell
python -m pytest tests/test_repo_hygiene.py -v
```

**Expect:** 8 passed: env example in sync both ways, no secrets, scanner catches planted keys, `.dockerignore` keeps `.env` out, CI file valid.

**Step 6**

```powershell
git checkout -b development/ci-demo
git push -u origin development/ci-demo
```

**Expect:** With `PROJECT` and `paths` pointing at `Day27`, open the Actions tab: install, lint, secret scan and tests run, then the badge turns green.

### Break it on purpose

#### 1 · A real bug: the scanner flags ordinary words

`KEY_PATTERN` has no word boundary, so any word ending in "sk" followed by a long hyphenated run matches. Add the comment `# Flag high-risk-transactions-for-manual-review before routing.` to any `.py` file and run `python -m scripts.check_secrets`: it prints `key-like token sk-trans...` and exits 1, so CI goes red. "mask-credit-card-numbers-in-all-logs" does the same. This matters next month, when the project is about payment risk. Require that `sk-` isn't preceded by a letter or digit.

```python
KEY_PATTERN = re.compile(r"(?<![A-Za-z0-9])sk-(?:proj-)?[A-Za-z0-9_\-]{20,}")
```

#### 2 · Add a setting without documenting it

In `config.py`, add a field that reads `os.getenv("NEW_FLAG", "0")`. Run `python -m pytest tests/test_repo_hygiene.py -q`: `test_env_example_lists_every_variable_the_code_reads` fails with `missing from .env.example: ['NEW_FLAG']`. Add `NEW_FLAG=0` with a comment to `.env.example` and it's green again.

> CI is only as useful as its checks are trustworthy. A check that misses things gives false comfort, and a check that fires on innocent text teaches people to ignore it. Test your checks the same way you test your code, in both directions.

## Cheat sheet

- **Continuous integration (CI)**: Running the same automated checks on every push or pull request, so breakage shows up right away.
- **GitHub Actions**: GitHub's CI service. Workflows are YAML files in `.github/workflows/` at the repo root.
- **Workflow / job / step**: A workflow file holds jobs; a job runs on one machine; steps run in order inside it.
- **Trigger**: The events that start a workflow, here pushes to `main` or `development/**` and pull requests touching the project folder.
- **Coverage gate**: `--cov-fail-under=95` fails the build if coverage drops below 95 %.
- **Lint**: Static checks that find likely bugs without running the code, here with `ruff`.
- **Secret scanning**: Searching files for things that look like credentials before they reach the repo.
- **.env.example**: A committed template of every environment variable, with safe defaults and no real secrets.
- **Status badge**: An image in the README that shows the latest CI result for the workflow.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why does the CI job run without an <code>OPENAI_API_KEY</code>?</summary><p>The whole suite is offline, since LLM and embeddings are faked. That means forks and pull requests can be verified without secrets, and a leaked CI log can't leak a key.</p></details>
<details><summary>Why does the workflow file live at the repo root and use <code>env.PROJECT</code>?</summary><p>GitHub only reads workflows from the root <code>.github/workflows/</code>. Each day is its own folder, so the job sets <code>working-directory</code> to the folder named in <code>PROJECT</code>.</p></details>
<details><summary>What does <code>test_env_example_lists_every_variable_the_code_reads</code> protect against?</summary><p>Adding a <code>getenv</code> setting without documenting it. The test compares the variables in the code with the ones in <code>.env.example</code> and fails on any difference.</p></details>
<details><summary>Why was <code>!.env.example</code> added to <code>.gitignore</code>?</summary><p>The existing <code>.env.*</code> rule would have ignored <code>.env.example</code> too, so the documented config would never have been committed.</p></details>
<details><summary>What does <code>zip(a, b, strict=True)</code> change?</summary><p>Plain <code>zip</code> stops at the shorter list and hides a length mismatch. With <code>strict=True</code> a mismatch raises <code>ValueError</code>, so a bug can't quietly produce a wrong result.</p></details>
</div>

**Next:** Day 28 – The Portfolio Case Study

<style>
.ae-map{--accent:var(--teal);--accent-soft:color-mix(in srgb,var(--teal) 14%,var(--card));--surface:var(--card);--ghost:var(--muted);--ok:var(--teal);margin:1.2rem 0;overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:.8rem}
.ae-map svg{display:block;min-width:900px;width:100%;height:auto}
.ae-map .node-new rect{fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.6}
.ae-map .node-changed rect{fill:var(--surface);stroke:var(--accent);stroke-width:1.6;stroke-dasharray:6 3}
.ae-map .node-existing rect{fill:var(--surface);stroke:var(--line);stroke-width:1.2}
.ae-map .node-external rect{fill:var(--surface);stroke:var(--ink);stroke-width:1.2}
.ae-map .node-ghost rect{fill:none;stroke:var(--ghost);stroke-width:1.2;stroke-dasharray:5 4}
.ae-map .node-existing .t{fill:var(--muted)}.ae-map .node-ghost .t,.ae-map .node-ghost .s{fill:var(--ghost)}
.ae-map .nt{font-size:14px;font-weight:600;fill:var(--ink)}.ae-map .ns{font-size:11.5px;fill:var(--muted)}
.ae-map .lane,.ae-map .el{font-family:ui-monospace,Consolas,monospace;fill:var(--muted)}.ae-map .lane{font-size:11px;letter-spacing:1.2px}.ae-map .el{font-size:10.5px}
.ae-map .edge{fill:none;stroke:var(--accent);stroke-width:1.5}.ae-map .edge-old{fill:none;stroke:var(--muted);stroke-width:1.2}
.ae-map .edge-back{fill:none;stroke:var(--ok);stroke-width:1.5}.ae-map .edge-ghost{fill:none;stroke:var(--ghost);stroke-width:1.1;stroke-dasharray:3 3}
.ae-map .elbg{fill:var(--surface)}
.ae-legend{display:flex;flex-wrap:wrap;gap:.4rem 1.1rem;font-size:.84rem;color:var(--muted);--accent:var(--teal);--accent-soft:color-mix(in srgb,var(--teal) 14%,var(--card));--ghost:var(--muted)}
.ae-legend i{display:inline-block;width:18px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:6px}
.ae-quiz details{border:1px solid var(--line);border-radius:8px;background:var(--card);padding:.7rem 1rem;margin:.6rem 0}
.ae-quiz summary{cursor:pointer;font-weight:600;color:var(--ink)}
.ae-quiz details[open] summary{margin-bottom:.4rem}
.ae-quiz p{margin:.3rem 0;color:var(--text)}
</style>
