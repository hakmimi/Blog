---
title: "Day 9: Retrieval You Can Measure"
description: "From a fast retriever that sends the LLM whatever the top 4 chunks happen to be, to one that uses metadata, topic-aware ranking and an adaptive cutoff to send less, better context. A labelled test set replaces eyeballing: precision goes from 0.43 to 0.91 with 57 % fewer chunks."
series: "ai-engineering"
order: 11
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "metadata", "re-ranking", "hit@k / mrr"]
readingTime: "7 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day9`](https://github.com/hakmimi/AIEngineering/tree/main/Day9). Layers touched: L1 Data, L2 LLM.

## Goals

- **G1. Attach metadata to every chunk and filter on it.**  
  You can: call `/search` with `"category":"nature"` and show every result carries `topic` and `category`.
- **G2. Improve ranking with a topic boost and contextual embeddings.**  
  You can: explain why `"<topic>: <text>"` is embedded while the stored text stays unchanged.
- **G3. Replace a fixed top-k with an adaptive cutoff.**  
  You can: show a clear question returning one or two chunks instead of four.
- **G4. Measure retrieval with a labelled set before and after a change.**  
  You can: run `retrieval_quality.py` and read hit@1, MRR, precision and avg chunks aloud.

## System map

The FAISS index from Day 8 stays. Today's changes sit on both sides of it: richer chunks going in, smarter ranking coming out, and a measuring stick next to it all.

> Query (+ category/topic) → embed → FAISS → metadata filter → score (cosine + keyword + topic) → relative cutoff → [doc:chunk\|topic] context → LLM → Response

<div class="ae-map" role="img" aria-label="The client sends a query with optional category and topic to /search or /rag. SearchRequest turns them into filters. retrieval.py embeds the query, searches FAISS (the whole index when filtering), filters by metadata, scores with cosine plus keyword and topic boosts, and keeps only chunks near the best score. rag.py formats context with the topic and calls the LLM. The embedding pipeline now writes topic and category from categories.json and embeds the topic-prefixed text. retrieval_quality.py runs 20 labelled queries and saves metrics."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 474" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · API</text><text class="lane" x="508" y="18">L1 · RETRIEVAL.PY</text><text class="lane" x="752" y="18">L1 · DATA</text><text class="lane" x="996" y="18">L2 · RAG.PY</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,182 C230,182 230,136 261,136" marker-end="url(#mka)"></path><path class="edge" d="M354,178 L354,198" marker-end="url(#mka)"></path><path class="edge" d="M444,235 C474,235 474,76 505,76" marker-end="url(#mka)"></path><path class="edge" d="M598,118 L598,137" marker-end="url(#mka)"></path><path class="edge" d="M598,224 L598,243" marker-end="url(#mka)"></path><path class="edge" d="M688,288 C840,288 840,235 993,235" marker-end="url(#mka)"></path><path class="edge" d="M1086,193 L1086,174" marker-end="url(#mka)"></path><path class="edge" d="M1176,129 C1206,129 1206,182 1237,182" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,212 V356 H110 V216" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="152"></rect><text class="nt t" text-anchor="middle" x="110" y="176">Client</text><text class="ns s" text-anchor="middle" x="110" y="194">query + category / topic</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="94"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="126">SearchRequest</text><text class="ns s" text-anchor="middle" x="354" y="146">category · topic</text><text class="ns s" text-anchor="middle" x="354" y="160">.filters()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="108">CHANGED</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="264" y="200"></rect><text class="nt t" text-anchor="middle" x="354" y="232">/search · /rag</text><text class="ns s" text-anchor="middle" x="354" y="252">pass filters through</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="214">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="66">faiss_search()</text><text class="ns s" text-anchor="middle" x="598" y="85">whole index when filtered</text><text class="ns s" text-anchor="middle" x="598" y="100">matches_filters()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="47">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="172">score_chunk()</text><text class="ns s" text-anchor="middle" x="598" y="191">cosine + keyword</text><text class="ns s" text-anchor="middle" x="598" y="206">+ topic boost 0.15</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="153">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="246"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="278">relative_cutoff()</text><text class="ns s" text-anchor="middle" x="598" y="297">keep chunks within</text><text class="ns s" text-anchor="middle" x="598" y="312">0.12 of the best</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="259">NEW</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="752" y="62"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="94">retrieval_quality</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="112">.py</text><text class="ns s" text-anchor="middle" x="842" y="130">20 labelled queries</text><text class="ns s" text-anchor="middle" x="842" y="146">hit@1 · MRR · precision</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="74">NEW</text></g><g class="node-changed"><rect height="117" rx="8" width="180" x="752" y="186"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="218">embedding_pipelin</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="236">e</text><text class="ns s" text-anchor="middle" x="842" y="254">topic + category per chunk</text><text class="ns s" text-anchor="middle" x="842" y="270">embeds "topic: text"</text><text class="ns s" text-anchor="middle" x="842" y="284">→ FAISS rebuilds (Day 8)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="198">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="87"></rect><text class="nt t" text-anchor="middle" x="1086" y="119">LLM gate</text><text class="ns s" text-anchor="middle" x="1086" y="138">RETRIEVAL_THRESHOLD</text><text class="ns s" text-anchor="middle" x="1086" y="153">0.55 → 0.40</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="100">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="193"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="225">build_context()</text><text class="ns s" text-anchor="middle" x="1086" y="244">[doc:chunk|topic] text</text><text class="ns s" text-anchor="middle" x="1086" y="259">best chunk first</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="206">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="152"></rect><text class="nt t" text-anchor="middle" x="1330" y="176">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="194">embeddings + answer</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="142"></rect><text class="el" text-anchor="middle" x="230" y="153">JSON</text><rect class="elbg" height="15" rx="3" width="53" x="448" y="138"></rect><text class="el" text-anchor="middle" x="474" y="150">filters</text><rect class="elbg" height="15" rx="3" width="46" x="1183" y="138"></rect><text class="el" text-anchor="middle" x="1206" y="150">prompt</text><rect class="elbg" height="15" rx="3" width="98" x="671" y="349"></rect><text class="el" text-anchor="middle" x="720" y="360">{ results: … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="404">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="414"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="441">Day 10 · multi-step pipelines</text></g><g class="node-ghost"><rect height="44" rx="8" width="182" x="300" y="414"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="391" y="441">Day 13 · evaluation</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Fast, but blind to quality

- Chunks had only `doc_id`, `chunk_id` and `text`, so there was nothing to filter on
- A chunk like "It is located…" was embedded without its subject
- `top_k` chunks went to the LLM even when only one was relevant
- "Is retrieval good?" was answered by reading a few outputs

### After this episode: Less context, the right context

- Every chunk carries `topic` and `category`; `/search` and `/rag` accept optional filters
- `score_chunk` adds a topic boost when the query names the chunk's topic
- `relative_cutoff` keeps only chunks within `0.12` of the best score
- `retrieval_quality.py` scores 20 labelled queries: precision 0.433 → 0.912, avg chunks 3.70 → 1.60

> **Why it matters:** the LLM can only be as good as the context it gets. Irrelevant chunks cost tokens and invite wrong answers. And without a labelled set you can't tell if a change helped; with one, you also catch side effects, like the threshold that suddenly refused a valid skiing question.

## Code walkthrough

Four snippets from `Day9`: what goes into the index, how results are scored and trimmed, and how filters work.

### embedding_pipeline.py · metadata + contextual embedding

```python
            topic = doc.get("topic")
            embedded.append({
                "doc_id": doc.get("id"),
                "chunk_id": chunk_id,
                "topic": topic,                              # metadata used for filtering + ranking
                "category": categories.get(topic, "other"),
                "text": text,
                # contextual embedding: a bare chunk ("It is located...") loses its subject, so prefix the topic
                "embedded_text": get_embedding(f"{topic}: {text}"),
            })
```

**Embed what the chunk means, store what the chunk says.** The vector sees `Dead Sea: It is located…`, but the text sent to the LLM is unchanged. The category comes from a hand-made map, which the README admits would come from the data source in a real system.

### retrieval.py · scoring and adaptive top-k

```python
def score_chunk(query: str, chunk_text: str, similarity: float, topic: str | None = None) -> float:
    """similarity + keyword-overlap boost + boost when the chunk's topic is named in the query."""
    score = similarity + settings.keyword_boost * keyword_overlap(query, chunk_text)
    return score + (settings.topic_boost if topic_in_query(query, topic) else 0.0)
...
def relative_cutoff(chunks: list[dict]) -> list[dict]:
    """Adaptive top-k: keep only chunks close to the best one (drops the noisy tail)."""
    if not chunks:
        return chunks
    floor = chunks[0]["score"] - settings.relative_score_margin
    return [c for c in chunks if c["score"] >= floor]
```

**Each rule is one line you can explain and tune.** No learned re-ranker, just three additive signals. The cutoff is relative to the best chunk, so a clear winner travels alone and a close race keeps several.

### retrieval.py · filtering without a WHERE clause

```python
def faiss_search(query_embedding: list[float], query: str, top_k: int, filters: dict | None = None) -> list[dict]:
    ...
    store = get_store()
    fetch = store.index.ntotal if filters else top_k * settings.faiss_candidate_multiplier
    candidates = [c for c in store.search(query_embedding, fetch) if matches_filters(c, filters)]
    return _rank(query, candidates, top_k)
```

**Filter after searching everything, because the index can't filter for you.** Fetching all 77 vectors costs nothing here. With a million you'd want a partitioned or filtered index, which is what managed vector databases sell.

### retrieval_quality.py · the measuring stick

```python
        results = get_relevant_chunks(query, 4, **kwargs)
        got = [topics[c["doc_id"]] for c in results]
        rank = next((i + 1 for i, t in enumerate(got) if t in expected), None)
        hit1 += rank == 1
        hit3 += bool(rank and rank <= 3)
        rr += 1 / rank if rank else 0
        prec += sum(t in expected for t in got) / len(got) if got else 0
```

**Four numbers, each answering a different question about the same results.** hit@1 was already 1.0 on this easy dataset, so it can't show improvement. Precision can: it asks how much of what we send is on-topic.

## Run it

**Step 1**

```powershell
python embedding_pipeline.py
```

**Expect:** `Wrote N chunks to ...embedded_chunks.json`. Open the file and show `topic` and `category` on a chunk. The FAISS index rebuilds on next use because the source is newer.

**Step 2**

```powershell
python retrieval_quality.py improved
```

**Expect:** One `rank=... | query | [topics]` line per case, then a summary dict with `hit@1`, `hit@3`, `mrr`, `precision`, `avg_chunks`.

**Step 3**

```powershell
python retrieval_quality.py compare baseline improved
```

**Expect:** Five lines with deltas. Precision up by about +0.48, avg_chunks down by about 2.

**Step 4**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on port 8000.

**Step 5**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/search" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Mountain with skiing","category":"nature"}').results
```

**Expect:** Only `category: nature` chunks, each with `topic`, `similarity` and `score`. The server log shows `filters={'category': 'nature'}`.

**Step 6**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Where can I go skiing?"}').results
```

**Expect:** An answer about Mount Hermon, `source: rag`, and fewer `retrieved_chunks` than the requested 4.

### Break it on purpose

#### 1 · A typo in the filter

Send `/rag` with `"category":"cities"` instead of `city`. You get **200** with `source: no_context` and the "I don't have enough information" answer. `SearchRequest` accepts any string up to 50 characters, `matches_filters` matches nothing, and the user can't tell a typo from a real knowledge gap. Validate the value at the edge so the client gets a 422.

```text
# schemas.py
from typing import Literal
Category = Literal["city", "nature", "history", "culture",
                   "technology", "society", "industry"]

class SearchRequest(BaseModel):
    ...
    category: Category | None = Field(default=None, description="Optional metadata filter")
```

#### 2 · Put the Day 5 threshold back

Stop uvicorn, run `$env:RETRIEVAL_THRESHOLD="0.55"`, start it again from the same terminal and ask "Where can I go skiing?". The answer is now the refusal with `source: no_context`: the best score after topic-prefixed embeddings is about 0.45, under the old gate. This is the regression the README found in live testing. Run `Remove-Item Env:RETRIEVAL_THRESHOLD` and restart to go back to 0.40.

> Changing how you embed changes the score distribution, so every threshold tuned on the old scores has to be re-checked. A labelled set turns that from a surprise in production into a line in a report.

## Cheat sheet

- **Retrieval quality**: How relevant the chunks sent to the LLM are. It caps the quality of the answer.
- **Metadata**: Structured fields stored next to each chunk, here `topic` and `category`, used for filtering and ranking.
- **Contextual embedding**: Embedding a chunk with added context (`"topic: text"`) so the vector keeps the subject the text alone lost.
- **Re-ranking**: Reordering search candidates with extra signals after the vector search. Here: keyword overlap and topic boost.
- **Adaptive top-k**: Returning as many chunks as are close to the best one, up to `top_k`, instead of always `top_k`.
- **Metadata filter**: Restricting results to chunks whose fields match, e.g. `category=nature`. Case-insensitive; all given fields must match.
- **hit@k**: Share of queries where a correct chunk appears in the top k results.
- **MRR**: Mean reciprocal rank: the average of 1/rank of the first correct result. 1.0 means always first.
- **Precision**: Share of returned chunks that are on-topic. It's the metric that moved here, 0.433 → 0.912.
- **Baseline**: The metrics recorded before a change, saved to `quality_baseline.json`, so you compare against numbers you saved.
- **Threshold recalibration**: Re-tuning a score cutoff after the scoring changed. The LLM gate moved from 0.55 to 0.40.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why did precision jump while hit@1 went slightly down?</summary><p>The cutoff and topic boost send far fewer off-topic chunks, so precision rose. The one hit@1 miss is a vague query with a strict <code>category=city</code> filter that now returns nothing instead of weak context.</p></details>
<details><summary>Why embed "topic: text" but keep the original text in the chunk?</summary><p>The prefix gives the vector the subject a chunk may have lost after splitting. The stored text is what the LLM reads and what gets cited, so it shouldn't change.</p></details>
<details><summary>How does faiss_search apply a metadata filter?</summary><p>FAISS has no filter, so with filters it fetches the whole index (<code>store.index.ntotal</code>), keeps only chunks where <code>matches_filters</code> is true, then re-ranks.</p></details>
<details><summary>A user asks one clear question with top_k=4 and gets 1 chunk. Is that a bug?</summary><p>No. <code>relative_cutoff</code> keeps only chunks within 0.12 of the best score. <code>top_k</code> is now an upper bound.</p></details>
<details><summary>Why was RETRIEVAL_THRESHOLD lowered from 0.55 to 0.40?</summary><p>Topic-prefixed embeddings changed the score range. "Where can I go skiing?" scored about 0.45 and was refused. Relevant queries score 0.45–0.97 and out-of-domain ones at most 0.31, so 0.40 sits in the gap.</p></details>
</div>

**Next:** Day 10 – Think in Steps

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
