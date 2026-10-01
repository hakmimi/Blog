---
title: "Day 26: Tests Without a Network"
description: "From a pile of tests added day by day to a test suite with a shape: unit, API and integration markers, shared fixtures, and a coverage number. All 392 tests run in about 17 seconds with no network and no API key, and the retrieval tests run on the real documents and a real FAISS index."
series: "ai-engineering"
order: 28
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "pytest", "markers", "fakes", "coverage"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day26`](https://github.com/hakmimi/AIEngineering/tree/main/Day26). Layers touched: L1 Data, L4 System.

## Goals

- **G1. Organise tests into categories you can run separately.**  
  You can: run `pytest -m unit`, `-m api` and `-m integration` and explain what's real and what's faked in each.
- **G2. Test retrieval on real data without calling OpenAI.**  
  You can: explain `HashEmbedder` and why its 32,768 dimensions matter.
- **G3. Cover the API surface: validation, auth, rate limit and error shapes.**  
  You can: show the 500 test that proves internal messages never leak, and the rate-limit window test.
- **G4. Measure coverage and read what it does and doesn't prove.**  
  You can: run `pytest --cov=.` and say why 99 % of application code isn't the same as "the answers are good".

## System map

This map shows the test harness around the system. The application didn't change. The new parts are the markers, the shared fixtures, a fake embedder and three new test files that exercise real code paths.

> Code change → pytest (unit + api + integration) → coverage → confidence

<div class="ae-map" role="img" aria-label="pytest reads pytest.ini for test paths and markers, and pytest-cov measures application code only. Tests are split into unit, api and integration. API tests drive the unchanged FastAPI app through TestClient. Integration tests use conftest fixtures: fake_index builds a real FAISS index from the real documents in data/docs.json using HashEmbedder, and real_retrieval patches only the embedding call. OpenAI is never called. The run returns a pass or fail and a coverage figure."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 459" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">RUNNER</text><text class="lane" x="264" y="18">TEST LAYERS</text><text class="lane" x="508" y="18">FIXTURES + FAKES</text><text class="lane" x="752" y="18">SYSTEM UNDER TEST</text><text class="lane" x="996" y="18">EXTERNAL</text><path class="edge-old" d="M200,122 C230,122 230,68 261,68" marker-end="url(#mkm)"></path><path class="edge" d="M200,122 C230,122 230,167 261,167" marker-end="url(#mka)"></path><path class="edge" d="M200,122 C230,122 230,273 261,273" marker-end="url(#mka)"></path><path class="edge" d="M444,167 C596,167 596,126 749,126" marker-end="url(#mka)"></path><path class="edge" d="M444,273 C474,273 474,80 505,80" marker-end="url(#mka)"></path><path class="edge" d="M598,250 L598,231" marker-end="url(#mka)"></path><path class="edge" d="M598,144 L598,125" marker-end="url(#mka)"></path><path class="edge" d="M688,80 C718,80 718,216 749,216" marker-end="url(#mka)"></path><path class="edge-ghost" d="M932,126 C962,126 962,174 993,174" marker-end="url(#mkx)"></path><path class="edge-back" d="M842,156 V341 H110 V166" marker-end="url(#mkg)"></path><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="112">pytest.ini</text><text class="ns s" text-anchor="middle" x="110" y="130">testpaths · markers</text><text class="ns s" text-anchor="middle" x="110" y="146">unit / api / integration</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="92">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="186"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="218">pytest-cov</text><text class="ns s" text-anchor="middle" x="110" y="236">app code only</text><text class="ns s" text-anchor="middle" x="110" y="252">scripts/ tests/ excluded</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="198">NEW</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="264" y="34"></rect><text class="nt t" text-anchor="middle" x="354" y="66">unit · 295</text><text class="ns s" text-anchor="middle" x="354" y="85">Days 8–25 tests, now tagged</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="47">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="125"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="157">test_api.py</text><text class="ns s" text-anchor="middle" x="354" y="176">validation · auth · 429</text><text class="ns s" text-anchor="middle" x="354" y="191">error shapes</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="138">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="231"></rect><text class="nt t" text-anchor="middle" x="354" y="263">integration · 53</text><text class="ns s" text-anchor="middle" x="354" y="282">relevance · data paths</text><text class="ns s" text-anchor="middle" x="354" y="297">FAISS files</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="244">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="38"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="70">conftest.py</text><text class="ns s" text-anchor="middle" x="598" y="89">fake_index · real_retrieval</text><text class="ns s" text-anchor="middle" x="598" y="104">settings_override</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="51">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="144"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="176">HashEmbedder</text><text class="ns s" text-anchor="middle" x="598" y="195">tf-idf hash, 32,768 dims</text><text class="ns s" text-anchor="middle" x="598" y="210">deterministic</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="157">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="508" y="250"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="274">data/docs.json</text><text class="ns s" text-anchor="middle" x="598" y="293">real 53 docs · 77 chunks</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="95"></rect><text class="nt t" text-anchor="middle" x="842" y="119">FastAPI + graph</text><text class="ns s" text-anchor="middle" x="842" y="138">Day 25 code, unchanged</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="178"></rect><text class="nt t" text-anchor="middle" x="842" y="202">retrieval + FAISS</text><text class="ns s" text-anchor="middle" x="842" y="221">real ranking, filters</text><text class="ns s" text-anchor="middle" x="842" y="236">sibling expansion</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="996" y="144"></rect><text class="nt t" text-anchor="middle" x="1086" y="168">OpenAI</text><text class="ns s" text-anchor="middle" x="1086" y="187">never called in tests</text></g><rect class="elbg" height="15" rx="3" width="72" x="560" y="129"></rect><text class="el" text-anchor="middle" x="596" y="140">TestClient</text><rect class="elbg" height="15" rx="3" width="72" x="602" y="230"></rect><text class="el" text-anchor="start" x="604" y="240">chunk_text</text><rect class="elbg" height="15" rx="3" width="72" x="602" y="124"></rect><text class="el" text-anchor="start" x="604" y="134">fake_index</text><rect class="elbg" height="15" rx="3" width="78" x="679" y="131"></rect><text class="el" text-anchor="middle" x="718" y="142">monkeypatch</text><rect class="elbg" height="15" rx="3" width="46" x="939" y="133"></rect><text class="el" text-anchor="middle" x="962" y="144">mocked</text><rect class="elbg" height="15" rx="3" width="117" x="418" y="334"></rect><text class="el" text-anchor="middle" x="476" y="345">392 passed · 99 %</text><text class="lane" style="fill:var(--ghost)" x="20" y="389">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="426">Day 27 · CI on GitHub Actions</text></g><g class="node-ghost"><rect height="44" rx="8" width="254" x="300" y="399"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="427" y="426">Day 28 · portfolio packaging</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: 314 tests, no shape

- One flat `tests/` folder, no categories, no way to run only the fast ones
- Every retrieval test mocked retrieval itself, so ranking on real data was never tested offline
- No tests for auth, rate limiting or the FAISS file handling
- Coverage was 87 %, and that number included the scripts

### After this episode: 392 tests with a map

- `pytest.ini` markers, auto-assigned in `conftest.py`: 295 unit, 44 api, 53 integration
- `HashEmbedder` + `real_retrieval`: real chunks, real FAISS, only the network faked
- `test_api.py`: 8 bad payloads, auth on every protected endpoint, 429 and window expiry, no leaked internals
- 99 % coverage of application code, about 17 s, no key, every file passes on its own

> **Why it matters:** tests are what let you change the system without fear. Next episode, CI runs them on every push, and that only works if they need no secrets, no network and no luck. Today makes that true.

## Code walkthrough

Five snippets from `Day26/tests`. The application code is untouched; this is all test infrastructure.

### tests/fakes.py · a deterministic embedder

```python
DIM = 32768        # large on purpose: few hash collisions, so unrelated words really score ~0
...
    def __call__(self, text: str) -> list[float]:
        vec = [0.0] * DIM
        for word, count in Counter(_WORD.findall(text.lower())).items():
            vec[zlib.crc32(word.encode()) % DIM] += count * self.idf.get(word, self.default_idf)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
```

**It knows nothing about meaning, which is exactly what makes it predictable.** Shared words score, nothing else does. A first version with 2,048 dimensions had hash collisions that made unrelated queries look slightly similar, and the "unrelated queries return nothing" test caught it.

### tests/conftest.py · real retrieval, fake network

```python
@pytest.fixture
def real_retrieval(monkeypatch, fake_index):
    """Real retrieval code (FAISS, ranking, filters, sibling expansion) over real chunks; only embeddings are faked."""
    import retrieval
    embedder, store = fake_index
    monkeypatch.setattr(retrieval, "get_embedding", embedder)
    monkeypatch.setattr(retrieval, "get_store", lambda: store)
    original = retrieval.settings.min_chunk_score
    object.__setattr__(retrieval.settings, "min_chunk_score", 0.05)     # bag-of-words cosines are small; scale the floor
    yield retrieval
    object.__setattr__(retrieval.settings, "min_chunk_score", original)
```

**Patch the two seams, keep every line in between real.** `fake_index` is session-scoped, so the index is built once. The score floor is lowered because bag-of-words cosines are smaller than real embedding scores, and it's always restored after the test.

### tests/conftest.py · markers without decorators

```python
_API_FILES = {"test_api.py", "test_assistant.py"}
_INTEGRATION_FILES = {"test_retrieval_relevance.py", "test_llm_and_data_paths.py", "test_vector_store.py"}


def pytest_collection_modifyitems(items):
    for item in items:
        name = item.path.name
        item.add_marker(pytest.mark.api if name in _API_FILES else
                        pytest.mark.integration if name in _INTEGRATION_FILES else pytest.mark.unit)
```

**Every test gets a category, even the 314 written before today.** A pytest hook tags tests by file, so no old test needed editing. A new file is `unit` by default unless you add it to one of the sets.

### tests/test_api.py · errors never leak

```python
def test_unexpected_errors_never_leak_details(monkeypatch):
    monkeypatch.setattr(routes, "run_graph", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret internals")))
    response = client.post("/rag/graph", json={"query": "hello there"})
    assert response.status_code == 500 and "secret internals" not in response.text
    assert set(response.json()) == {"detail", "request_id"}
```

**Test the failure contract, not only the success one.** The generator-throw trick raises from inside a lambda. The test pins the exact shape of a 500 body: a generic message and the request id from Day 23, nothing else.

### tests/test_api.py · control the clock

```python
def test_rate_limit_window_expires(fake_graph, settings_override, monkeypatch):
    settings_override(rate_limit_per_minute=1)
    now = [1000.0]
    monkeypatch.setattr(security.time, "time", lambda: now[0])
    assert client.post("/rag/graph", json={"query": "hello"}).status_code == 200
    assert client.post("/rag/graph", json={"query": "hello"}).status_code == 429
    now[0] += 61
    assert client.post("/rag/graph", json={"query": "hello"}).status_code == 200
```

**Don't sleep for 61 seconds in a test. Move the clock.** Replacing `time.time` in `security.py` makes a time-based rule testable in milliseconds. `settings_override` changes the frozen settings for one test and restores them after.

## Run it

Run from `Day26` in PowerShell. Clear the key first to prove the point of the episode.

**Step 1**

```powershell
pip install -r requirements-dev.txt
$env:OPENAI_API_KEY=""
```

**Expect:** `pytest-cov` installed. The key is now empty for this shell.

**Step 2**

```powershell
python -m pytest
```

**Expect:** `392 passed` in roughly 17 s. `-ra` from `pytest.ini` prints a short summary of anything skipped.

**Step 3**

```powershell
python -m pytest -m unit -q
python -m pytest -m api -q
python -m pytest -m integration -q
```

**Expect:** About 295, 44 and 53 passed, with the rest deselected each time.

**Step 4**

```powershell
python -m pytest --cov=. --cov-report=term
```

**Expect:** A per-file table ending in `TOTAL` at 99 %. Point at the few missed lines, like the optional `truststore` import fallback.

**Step 5**

```powershell
python -m pytest tests/test_retrieval_relevance.py -v
```

**Expect:** Twelve `test_topic_named_by_the_query_is_ranked_first[...]` cases and three unrelated queries, all green on the real 77 chunks.

**Step 6**

```powershell
python -m pytest tests/test_api.py -k "rate_limit or leak" -v
```

**Expect:** The 429 test, the window-expiry test and the no-leak 500 test pass.

### Break it on purpose

#### 1 · An off-by-one in the rate limiter

In `security.py`, change `if len(window) >= settings.rate_limit_per_minute:` to `>`. Run `python -m pytest -m api -q`. `test_rate_limit_returns_429_after_the_quota` fails with `[200, 200, 200, 200, 429]` instead of `[200, 200, 200, 429, 429]`: one extra paid request per minute per client. Put `>=` back.

```text
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
```

#### 2 · Write the red test for Day 25's `rules:` bug

The output guard refuses any answer containing "rules:". Add the regression test below to `tests/test_guardrails.py` and run it: it fails with `prompt_leak`. Remove `"rules:"` from `_LEAK_MARKERS` and it passes, while the existing `"My rules: answer from the context only."` test still passes on the other marker. Red, fix, green: that's the loop this suite exists for.

```python
def test_normal_answers_mentioning_rules_are_not_leaks():
    assert check_output("Shabbat rules: most shops close on Saturday.", 0.9, "Shabbat shops close").ok
```

> Deterministic tests prove the code does what you decided. They can't prove the model answers well; that's the job of the eval scripts, which need the real model. Keep the two apart and each one stays fast and honest about what it measures.

## Cheat sheet

- **Unit test**: Tests one function or rule with everything around it faked.
- **API test**: Drives the real FastAPI app through `TestClient` with the graph behind it faked.
- **Integration test**: Runs real code paths over real data (chunking, FAISS, files) and fakes only the network.
- **Marker**: A pytest label (`unit`, `api`, `integration`) you can select with `-m`.
- **Fixture**: Reusable setup that pytest injects by argument name, like `real_retrieval` or `settings_override`.
- **monkeypatch**: A pytest fixture that replaces an attribute for one test and restores it afterwards.
- **Fake vs mock**: A fake is a working, simplified implementation (`HashEmbedder`); a mock just returns what the test told it to.
- **Coverage**: The share of code lines that ran during the tests. It shows what's untested, not what's correct.
- **Test isolation**: Each test passes alone and in any order, and never touches real state like `data/memory.db`.
- **Regression test**: A test written for a bug you found, so the same bug can't come back unnoticed.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>What's real and what's fake in the integration tests?</summary><p>Real: the 53 documents, chunking, the FAISS index, ranking, filters and sibling expansion. Fake: only the embedding call, replaced by <code>HashEmbedder</code>.</p></details>
<details><summary>Why does <code>HashEmbedder</code> use 32,768 dimensions?</summary><p>With fewer buckets, different words collide into the same slot and unrelated text looks slightly similar. The "unrelated queries retrieve nothing" test caught that with 2,048.</p></details>
<details><summary>Why mock OpenAI instead of calling it in tests?</summary><p>Speed (17 s instead of minutes), determinism (output varies even at temperature 0), zero cost, and the ability to inject failures like 429s, timeouts and invalid JSON on demand.</p></details>
<details><summary>Coverage is 99 %. Does that mean the assistant gives good answers?</summary><p>No. It means almost every line ran. Answer quality needs the real model and is measured by <code>evaluate</code>, <code>llm_eval</code> and <code>e2e_smoke</code>.</p></details>
<details><summary>How do the old tests from Days 8–25 get a marker without being edited?</summary><p><code>pytest_collection_modifyitems</code> in <code>conftest.py</code> tags every collected test by its file name, defaulting to <code>unit</code>.</p></details>
</div>

**Next:** Day 27 – Green on Every Push

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
