---
title: "Day 8: A Real Vector Index"
description: "From a Python loop that computes cosine similarity against every chunk on every request, to a FAISS index that is built once, saved to disk and searched in C. The answers stay the same; the search step gets about 65 times faster, and a comparison script proves both claims."
series: "ai-engineering"
order: 10
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "faiss indexflatip", "numpy", "benchmark"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day8`](https://github.com/hakmimi/AIEngineering/tree/main/Day8). Layers touched: L1 Data, L4 System.

## Goals

- **G1. Replace the list scan with a persisted FAISS index.**  
  You can: delete `data/faiss.index`, restart, and show the `faiss_rebuilt` log line and the new files in `data/`.
- **G2. Understand why normalised vectors in an inner-product index give cosine similarity.**  
  You can: explain why the Day 5 thresholds still work without retuning.
- **G3. Prove a swap changed speed and nothing else.**  
  You can: run `compare_retrieval.py` and read top-1 agreement, overlap and both timings aloud.
- **G4. Know where the time goes in a retrieval request.**  
  You can: point at `embed_ms` vs `search_ms` in the log and say which one to attack next.

## System map

Only the retrieval column changed today. The FAISS index sits between the embedded chunks on disk and the ranking you built on Day 5.

> Query → embed (OpenAI) → FAISS index (top_k × 3) → keyword re-rank → filter → LLM → Response

<div class="ae-map" role="img" aria-label="The client calls /rag. rag.py routes the question and calls get_relevant_chunks in retrieval.py. retrieval.py embeds the query with OpenAI, then calls faiss_search, which asks the VectorStore for top_k times 3 candidates. The VectorStore is loaded from data/faiss.index and faiss_meta.json, or rebuilt from embedded_chunks.json when stale. Candidates are re-ranked with the keyword boost and filtered, then the LLM answers and the response returns to the client. compare_retrieval.py runs legacy_search and faiss_search side by side."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 507" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · API</text><text class="lane" x="508" y="18">L1 · RETRIEVAL.PY</text><text class="lane" x="752" y="18">L1 · VECTOR_STORE.PY</text><text class="lane" x="996" y="18">L1 · RANKING</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,198 C230,198 230,198 261,198" marker-end="url(#mka)"></path><path class="edge" d="M444,198 C474,198 474,92 505,92" marker-end="url(#mka)"></path><path class="edge" d="M598,136 L598,155" marker-end="url(#mka)"></path><path class="edge" d="M688,200 C718,200 718,84 749,84" marker-end="url(#mka)"></path><path class="edge" d="M842,133 L842,152" marker-end="url(#mka)"></path><path class="edge" d="M688,306 C718,306 718,312 749,312" marker-end="url(#mka)"></path><path class="edge" d="M932,84 C962,84 962,140 993,140" marker-end="url(#mka)"></path><path class="edge" d="M1176,140 C1206,140 1206,198 1237,198" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,236 V389 H110 V232" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="168"></rect><text class="nt t" text-anchor="middle" x="110" y="192">Client</text><text class="ns s" text-anchor="middle" x="110" y="211">PowerShell · /docs</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="160"></rect><text class="nt t" text-anchor="middle" x="354" y="184">main · routes · rag</text><text class="ns s" text-anchor="middle" x="354" y="204">router, timings, prompts</text><text class="ns s" text-anchor="middle" x="354" y="218">(Day 6–7, unchanged)</text></g><g class="node-changed"><rect height="87" rx="8" width="180" x="508" y="49"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="81">get_relevant_chun</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="99">ks</text><text class="ns s" text-anchor="middle" x="598" y="118">logs embed_ms + search_ms</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="62">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="158"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="190">faiss_search()</text><text class="ns s" text-anchor="middle" x="598" y="209">production path</text><text class="ns s" text-anchor="middle" x="598" y="224">top_k × 3 candidates</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="171">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="264"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="296">legacy_search()</text><text class="ns s" text-anchor="middle" x="598" y="315">old list scan, kept</text><text class="ns s" text-anchor="middle" x="598" y="330">for comparison only</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="277">CHANGED</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="752" y="34"></rect><text class="nt t" text-anchor="middle" x="842" y="66">VectorStore</text><text class="ns s" text-anchor="middle" x="842" y="85">IndexFlatIP · normalised</text><text class="ns s" text-anchor="middle" x="842" y="100">build / save / load /</text><text class="ns s" text-anchor="middle" x="842" y="115">search</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="155"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="187">data/faiss.index</text><text class="ns s" text-anchor="middle" x="842" y="206">+ faiss_meta.json</text><text class="ns s" text-anchor="middle" x="842" y="221">rebuilt when stale</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="168">NEW</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="752" y="261"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="293">compare_retrieval</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="311">.py</text><text class="ns s" text-anchor="middle" x="842" y="330">8 queries · agreement</text><text class="ns s" text-anchor="middle" x="842" y="345">· timing</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="274">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="98"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="130">_rank()</text><text class="ns s" text-anchor="middle" x="1086" y="150">keyword boost + score</text><text class="ns s" text-anchor="middle" x="1086" y="164">filter (Day 5 rules)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="112">CHANGED</text></g><g class="node-existing"><rect height="94" rx="8" width="180" x="996" y="204"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="228">embedded_chunks.j</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="246">son</text><text class="ns s" text-anchor="middle" x="1086" y="266">source of truth</text><text class="ns s" text-anchor="middle" x="1086" y="280">(embedding_pipeline.py)</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="1240" y="160"></rect><text class="nt t" text-anchor="middle" x="1330" y="184">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="204">query embedding</text><text class="ns s" text-anchor="middle" x="1330" y="218">+ answer</text></g><rect class="elbg" height="15" rx="3" width="66" x="198" y="182"></rect><text class="el" text-anchor="middle" x="230" y="192">POST /rag</text><rect class="elbg" height="15" rx="3" width="46" x="695" y="125"></rect><text class="el" text-anchor="middle" x="718" y="136">vector</text><rect class="elbg" height="15" rx="3" width="53" x="1180" y="152"></rect><text class="el" text-anchor="middle" x="1206" y="164">context</text><rect class="elbg" height="15" rx="3" width="98" x="671" y="382"></rect><text class="el" text-anchor="middle" x="720" y="393">{ results: … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="437">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="230" x="20" y="447"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="135" y="474">Day 9 · retrieval quality</text></g><g class="node-ghost"><rect height="44" rx="8" width="206" x="270" y="447"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="373" y="474">Day 10 · data pipeline</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: A loop over every chunk

- `get_relevant_chunks` looped over `load_embedded_chunks()` and called `cosine_similarity` in pure Python
- Every query paid O(n) Python math, about 20 ms for 77 chunks
- Nothing about the search was saved; the vectors lived in one big JSON file
- The retrieval log had one `took=` number, so you couldn't tell embedding time from search time

### After this episode: An index built once, searched fast

- `VectorStore` wraps a `faiss.IndexFlatIP` over L2-normalised vectors, so scores are still cosine
- `data/faiss.index` + `faiss_meta.json` persist the index; `load_or_build_store()` rebuilds when it's missing or older than the chunks
- `faiss_search` fetches `top_k × 3` candidates, then the same keyword re-rank and filter decide
- `compare_retrieval.py` shows 100 % top-1 agreement and ≈ 0.29 ms vs ≈ 19.6 ms search time

> **Why it matters:** a vector index is the piece that lets RAG scale past a toy dataset. Doing the swap behind the same function and proving equal results is how you change infrastructure in a real system. The log split also shows that the embedding API call is now the slow part.

## Code walkthrough

Four snippets from `Day8`. The first two are the new vector store, the last two show how it plugs into retrieval.

### vector_store.py · build

```python
def _normalise(matrix: np.ndarray) -> np.ndarray:
    matrix = np.ascontiguousarray(matrix, dtype="float32")
    faiss.normalize_L2(matrix)  # in place
    return matrix
...
    @classmethod
    def build(cls, chunks: list[dict]) -> "VectorStore":
        ...
        vectors = _normalise(np.array([c["embedded_text"] for c in chunks]))
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        metadata = [{k: v for k, v in c.items() if k != "embedded_text"} for c in chunks]
```

**Unit-length vectors turn the inner product into cosine similarity.** That's why the Day 5 thresholds (`0.55`, `0.30`) stay valid. The metadata list drops the vectors because FAISS already stores them: row i of the metadata describes vector i.

### vector_store.py · load or rebuild

```python
def _is_stale(index_path: Path, source_path: Path) -> bool:
    return not index_path.exists() or index_path.stat().st_mtime < source_path.stat().st_mtime


def load_or_build_store() -> VectorStore:
    ...
    if source.exists() and _is_stale(index_path, source):
        ...
        store = VectorStore.build(chunks)
        store.save(index_path, meta_path)
        ...
        return store
    return VectorStore.load(index_path, meta_path)
```

**The index is a cache of `embedded_chunks.json`, rebuilt when the source is newer.** Notice that `_is_stale` only looks at `faiss.index`. Keep that in mind for the break-it segment: the metadata file isn't part of the check.

### retrieval.py · the new production path

```python
@lru_cache(maxsize=1)
def get_store() -> VectorStore:
    return load_or_build_store()
...
def faiss_search(query_embedding: list[float], query: str, top_k: int) -> list[dict]:
    """Day 8 approach: FAISS nearest-neighbour search, then the same keyword re-rank."""
    candidates = get_store().search(query_embedding, top_k * settings.faiss_candidate_multiplier)
    return _rank(query, candidates, top_k)
```

**Fetch more candidates than you need, then let your own scoring decide.** FAISS only knows cosine. The keyword boost can move a chunk up, so we ask for `top_k × 3` and re-rank. `lru_cache` means the index loads once per process.

### retrieval.py · split the timing

```python
    query_embedding = get_embedding(query)
    embed_ms = (time.perf_counter() - started_at) * 1000

    search_started = time.perf_counter()
    kept = [_public(c) for c in faiss_search(query_embedding, query, top_k)]
    search_ms = (time.perf_counter() - search_started) * 1000
```

**Measure the steps separately or you'll optimise the wrong one.** In a live request the search is well under a millisecond and the embedding call is over a second. The README calls caching the next lever.

## Run it

Run from `Day8` in PowerShell with the venv active. Keep the uvicorn terminal visible: the log lines are half the demo.

**Step 1**

```powershell
pip install -r requirements.txt
```

**Expect:** `faiss-cpu` and `numpy` install alongside the existing packages.

**Step 2**

```powershell
python compare_retrieval.py
```

**Expect:** One line per query with `top1_same=True`, `overlap=1.00`, and legacy vs faiss ms, then a summary dict. `data/retrieval_comparison.json` is written.

**Step 3**

```powershell
Remove-Item data\faiss.index
uvicorn main:app --reload
```

**Expect:** The server starts. The index is not built yet: `get_store()` is lazy.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Where can I float on salt water?"}').results
```

**Expect:** An answer with `[doc:chunk]` citations. In the server log: `faiss_index_built`, `faiss_index_saved`, `faiss_rebuilt`, then `retrieval backend=faiss ... embed_ms=... search_ms=...`.

**Step 5**

```powershell
python -m pytest tests -q
```

**Expect:** `41 passed`, including the 7 new tests in `test_vector_store.py`.

### Break it on purpose

#### 1 · Delete the metadata file, keep the index

Stop uvicorn, run `Remove-Item data\faiss_meta.json`, start it again and send the same `/rag` request. You get **500** `{"detail": "FAISS index files are missing or corrupt"}` on every retrieval, even though `embedded_chunks.json` is right there to rebuild from. The cause: `_is_stale` checks only `faiss.index`, so `load_or_build_store()` goes to `VectorStore.load()`, which raises. The same happens when the two files drift out of sync. Fix it live so any load failure falls back to a rebuild.

```text
# vector_store.py, end of load_or_build_store()
if source.exists() and (_is_stale(index_path, source) or not meta_path.exists()):
    ...rebuild as before...
try:
    return VectorStore.load(index_path, meta_path)
except DataStoreError:
    if not source.exists():
        raise
    logger.warning("faiss_load_failed, rebuilding")
    store = VectorStore.build(json.loads(source.read_text(encoding="utf8")))
    store.save(index_path, meta_path)
    return store
```

#### 2 · Change the data under a running server

With uvicorn running, run `(Get-Item data\embedded_chunks.json).LastWriteTime = Get-Date` and send another request. No rebuild happens: `get_store()` is wrapped in `lru_cache`, so the process keeps the index it loaded first, and `--reload` only watches Python files. Restart uvicorn and the `faiss_rebuilt` line appears. Staleness is only checked once per process.

> A persisted index is a derived copy of your data. The code that decides when the copy is valid needs as much care as the search itself.

## Cheat sheet

- **Vector database**: A store built to answer nearest-neighbour queries over embeddings fast. FAISS is a library that does the core of this.
- **FAISS**: Facebook AI Similarity Search: a C++ library with Python bindings for indexing and searching dense vectors.
- **IndexFlatIP**: An exact FAISS index that compares the query with every vector using the inner product, in optimised C.
- **L2 normalisation**: Scaling a vector to length 1. For unit vectors the inner product equals cosine similarity.
- **Exact vs approximate search**: Exact checks every vector. Approximate indexes like IVF or HNSW skip most of them and pay off around 100k+ vectors.
- **Persistence**: Saving the index with `faiss.write_index` so a restart loads it instead of rebuilding it.
- **Metadata sidecar**: `faiss_meta.json`: row i describes vector i (doc, chunk, text). `load` checks `ntotal == len(metadata)`.
- **Candidate multiplier**: `FAISS_CANDIDATE_MULTIPLIER` (3): how many extra results to fetch so the keyword re-rank has room to reorder.
- **Top-1 agreement**: The share of queries where the old and new search return the same best chunk. 100 % here.
- **Staleness check**: Comparing file modification times to decide if a derived file must be rebuilt.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why didn't the retrieval thresholds need retuning after switching to FAISS?</summary><p>Vectors are L2-normalised before they go into an inner-product index, so the score FAISS returns is the same cosine similarity the old code computed.</p></details>
<details><summary>Why does faiss_search ask for top_k × 3 results instead of top_k?</summary><p>FAISS ranks by cosine only. The keyword boost in <code>_rank</code> can reorder chunks, so we fetch extra candidates and let our own score pick the final <code>top_k</code>.</p></details>
<details><summary>The search got 65× faster. Why does a /rag request barely feel faster?</summary><p>The query embedding is an API call of about a second. Search was around 20 ms before and is under 1 ms now, so it was never the main cost. <code>embed_ms</code> vs <code>search_ms</code> in the log shows it.</p></details>
<details><summary>What happens if faiss_meta.json is deleted but faiss.index and embedded_chunks.json remain?</summary><p><code>_is_stale</code> only checks the index file, so the code tries <code>VectorStore.load</code>, which raises <code>DataStoreError</code>. Every retrieval returns 500 until the index is deleted or the rebuild logic is fixed.</p></details>
<details><summary>When would you move off IndexFlatIP?</summary><p>When exact search gets too slow, roughly at 100k+ vectors. Then an approximate index like IVF or HNSW trades a little recall for much faster search.</p></details>
</div>

**Next:** Day 9 – Retrieval You Can Measure

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
