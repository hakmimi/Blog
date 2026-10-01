---
title: "Day 3: Search by Meaning"
description: "Until now the model only knew what it was trained on. Today we build the data layer: split documents into chunks, turn each chunk into an embedding vector, and find the closest chunks to a question with cosine similarity, all behind a /search endpoint."
series: "ai-engineering"
order: 4
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "embeddings", "cosine similarity", "chunking"]
readingTime: "7 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day3`](https://github.com/hakmimi/AIEngineering/tree/main/Day3). Layers touched: L1 Data, L2 LLM, L3 Orchestration, L4 System.

## Goals

- **G1. Explain what an embedding is and generate one.**  
  You can: run `tests/test_embeddings.py` and show a list of 1536 floats for one sentence.
- **G2. Measure similarity between texts with cosine similarity.**  
  You can: run `tests/test_similarity.py` and explain why the two Jerusalem sentences score highest.
- **G3. Chunk documents and store their vectors once, offline.**  
  You can: run `embedding_pipeline.py` and open one record in `data/embedded_chunks.json`.
- **G4. Expose top-k retrieval through the API.**  
  You can: call `/search` with a query that shares no keywords with the answer and still get the right chunk first.

## System map

Two flows today. The top one runs once, offline: documents to chunks to vectors on disk. The bottom one runs per request: query to vector to ranked chunks. There is no LLM answer yet; that's Day 4.

> Once: docs → chunks → vectors on disk · Per query: query → vector → cosine → top-k

<div class="ae-map" role="img" aria-label="Offline, embedding_pipeline.py reads data/docs.json, splits each text into 30-word chunks, embeds each chunk with OpenAI text-embedding-3-small and writes data/embedded_chunks.json. Online, a client posts a query to /search; get_relevant_chunks embeds the query, compares it with every stored vector using cosine similarity, sorts by score and returns the top_k chunks."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 353" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">INPUTS</text><text class="lane" x="264" y="18">L1 · L4 ENTRY</text><text class="lane" x="508" y="18">L2 · EMBEDDINGS.PY</text><text class="lane" x="752" y="18">STORE · EXTERNAL</text><text class="lane" x="996" y="18">L3 · RETRIEVAL.PY</text><path class="edge" d="M200,80 C230,80 230,68 261,68" marker-end="url(#mka)"></path><path class="edge" d="M200,167 C230,167 230,167 261,167" marker-end="url(#mka)"></path><path class="edge" d="M444,68 C474,68 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M444,167 C474,167 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M688,122 C718,122 718,174 749,174" marker-end="url(#mka)"></path><path class="edge" d="M688,122 C718,122 718,80 749,80" marker-end="url(#mka)"></path><path class="edge" d="M932,80 C962,80 962,76 993,76" marker-end="url(#mka)"></path><path class="edge" d="M932,174 C962,174 962,76 993,76" marker-end="url(#mka)"></path><path class="edge" d="M1086,118 L1086,137" marker-end="url(#mka)"></path><path class="edge-back" d="M1086,209 V235 H110 V200" marker-end="url(#mkg)"></path><g class="node-new"><rect height="69" rx="8" width="180" x="20" y="46"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="78">data/docs.json</text><text class="ns s" text-anchor="middle" x="110" y="96">small text dataset</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="58">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="136"></rect><text class="nt t" text-anchor="middle" x="110" y="160">Client</text><text class="ns s" text-anchor="middle" x="110" y="180">/docs · test_app.py</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="66">chunk_text()</text><text class="ns s" text-anchor="middle" x="354" y="85">30 words per chunk</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="125"></rect><text class="nt t" text-anchor="middle" x="354" y="157">POST /search</text><text class="ns s" text-anchor="middle" x="354" y="176">query · top_k=4</text><text class="ns s" text-anchor="middle" x="354" y="191">also /health, /docs-count</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="138">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="87"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="119">get_embedding()</text><text class="ns s" text-anchor="middle" x="598" y="138">text → list[float]</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="100">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="38"></rect><text class="nt t" text-anchor="middle" x="842" y="70">embedded_chunks.json</text><text class="ns s" text-anchor="middle" x="842" y="89">doc_id · chunk_id · text</text><text class="ns s" text-anchor="middle" x="842" y="104">embedded_text</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="51">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="752" y="144"></rect><text class="nt t" text-anchor="middle" x="842" y="168">OpenAI Embeddings</text><text class="ns s" text-anchor="middle" x="842" y="187">text-embedding-3-small</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="34"></rect><text class="nt t" text-anchor="middle" x="1086" y="66">cosine_similarity()</text><text class="ns s" text-anchor="middle" x="1086" y="85">similarity.py</text><text class="ns s" text-anchor="middle" x="1086" y="100">dot / (|a| · |b|)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="47">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="140"></rect><text class="nt t" text-anchor="middle" x="1086" y="172">sort + top_k</text><text class="ns s" text-anchor="middle" x="1086" y="191">get_relevant_chunks()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="153">NEW</text></g><rect class="elbg" height="15" rx="3" width="40" x="210" y="150"></rect><text class="el" text-anchor="middle" x="230" y="161">query</text><rect class="elbg" height="15" rx="3" width="46" x="451" y="78"></rect><text class="el" text-anchor="middle" x="474" y="89">chunks</text><rect class="elbg" height="15" rx="3" width="40" x="454" y="127"></rect><text class="el" text-anchor="middle" x="474" y="138">query</text><rect class="elbg" height="15" rx="3" width="59" x="689" y="84"></rect><text class="el" text-anchor="middle" x="718" y="95">pipeline</text><rect class="elbg" height="15" rx="3" width="78" x="923" y="61"></rect><text class="el" text-anchor="middle" x="962" y="72">all vectors</text><rect class="elbg" height="15" rx="3" width="85" x="920" y="108"></rect><text class="el" text-anchor="middle" x="962" y="119">query vector</text><rect class="elbg" height="15" rx="3" width="123" x="536" y="228"></rect><text class="el" text-anchor="middle" x="598" y="239">{ results: [...] }</text><text class="lane" style="fill:var(--ghost)" x="20" y="283">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="230" x="20" y="293"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="135" y="320">Day 4 · RAG: chunks → LLM</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="270" y="293"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="400" y="320">Day 4+ · production hardening</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: The model knows only its training

- Every answer comes from the model's general knowledge
- No documents, no data layer, nothing to search
- Similar meaning with different words can't be matched
- The API only talks to a chat model

### After this episode: The system can find our own data

- `data/docs.json` is chunked and embedded once by `embedding_pipeline.py`
- Each chunk is stored with its vector in `embedded_chunks.json`
- `get_relevant_chunks()` ranks chunks by cosine similarity
- `POST /search` returns the top-k chunks with their scores

> **Why it matters:** LLMs don't know your data. Before any RAG, agent or assistant can use your documents, something has to find the right piece of text for a question. This is that something, built by hand so you can see every step.

## Code walkthrough

Four snippets from `Day3`. Keep each one on screen long enough to read it; this is the most conceptual episode so far.

### embeddings.py · text to vector

```python
def get_embedding(text : str) -> list[float]:
    response = client.embeddings.create(model='text-embedding-3-small',
                                        input=text)
    return(response.data[0].embedding)
```

**One API call turns any text into a fixed-length list of numbers.** The same model must embed both the documents and the queries. Vectors from different models live in different spaces and can't be compared.

### similarity.py · the math

```python
def cosine_similarity(a: list[float], b :list[float]) -> float:
    dot_product = sum(x * y for x,y in zip(a,b))
    norm_a = math.sqrt(sum(x * x for x in a ))
    norm_b = math.sqrt(sum(y * y for y in b))
    return ( dot_product / (norm_a * norm_b))
```

**Cosine similarity compares direction, not length.** Dividing by both lengths removes size from the comparison. 1 means same direction, 0 means unrelated. Five lines of Python, no library, so nothing is magic.

### embedding_pipeline.py · build the index

```python
for i in range(0,len(docs)):
    text = docs[i].get('text')
    chunnked_text = chunk_text(text)
    ...
    for j in range(0,len(chunnked_text)):
        emb_text = get_embedding(chunnked_text[j])
        chunk_dict = {'doc_id' : docs[i].get('id'),                          
                      'chunk_id' : j,
                       'text': chunnked_text[j],
                       'embedded_text' : emb_text }
        embeddings_file.append(chunk_dict)
```

**Every stored chunk keeps its text, its source and its vector together.** `doc_id` and `chunk_id` let you trace any search result back to its document. That's the seed of citations in later days.

### retrieval.py + main.py · ranking and the endpoint

```python
def get_relevant_chunks(query: str,top_k: int=4):
    query_embedding = get_embedding(query)
    with open('data/embedded_chunks.json','r',encoding='utf-8') as f:
        ...
            score = cosine_similarity(query_embedding,chunk['embedded_text'])
        ...
        results = sorted(results,key = lambda x: x['score'] , reverse=True)
        return(results[:top_k])

class SearchRequest(BaseModel):
    query : str
    top_k : int = Field(default=4)
```

**Retrieval is brute force here: score every chunk, sort, slice.** Fine for a handful of documents; a vector database does this at scale later. The file is read on every request with a relative path, and `top_k` has no limits. Both come back in the break-it.

## Run it

Run everything from the `Day3` folder in PowerShell. The pipeline and the tests call the OpenAI embeddings API, so they need the key in `.env`.

**Step 1**

```powershell
python tests\test_embeddings.py
```

**Expect:** `<class 'list'>`, then `1536`, then the first ten floats.

**Step 2**

```powershell
python tests\test_similarity.py
```

**Expect:** Three scores. Text 1 vs text 2 (Jerusalem vs Old City) scores highest; pairs with the Tel Aviv startup sentence score lower.

**Step 3**

```powershell
python tests\test_chunking.py
```

**Expect:** A list of 5-word chunks from the three-line sample text.

**Step 4**

```powershell
python embedding_pipeline.py
```

**Expect:** No output; `data\embedded_chunks.json` is written. Open it and show one record with its `embedded_text` list.

**Step 5**

```powershell
uvicorn main:app --reload
# second terminal
Invoke-RestMethod http://127.0.0.1:8000/docs-count
```

**Expect:** `documents` equals the number of entries in `docs.json`.

**Step 6**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/search" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"young city with nightlife","top_k":4}' |
  ConvertTo-Json -Depth 4
```

**Expect:** Four results sorted by `score`, a Tel Aviv chunk first. The server log shows `Top K: 4` and `Retrieved chunks: 4`.

### Break it on purpose

#### 1 · `top_k: -1` returns almost everything

Send `{"query":"young city with nightlife","top_k":-1}`. `SearchRequest` accepts any int, and `results[:-1]` means all chunks except the last, so you get nearly the whole dataset. `top_k: 0` returns an empty list with 200 OK. Nothing crashed, and nothing is right.

```python
class SearchRequest(BaseModel):
    query : str = Field(min_length=1, max_length=1000)
    top_k : int = Field(default=4, ge=1, le=10)
```

#### 2 · The script that only works from one folder

`cd tests` and run `python test_retrieval.py`. The `sys.path` line fixes imports, but `open('data/embedded_chunks.json')` is relative to the current directory, so you get **FileNotFoundError**. Same for uvicorn started from another folder. Day 4+ fixes this with paths built from `__file__`.

```python
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
CHUNKS_PATH = BASE_DIR / "data" / "embedded_chunks.json"
```

> Retrieval can fail silently: a bad `top_k` or the wrong working folder returns 200 OK or crashes far from the cause. Validate inputs at the edge and build file paths from the code's location, not from where you happen to run it.

## Cheat sheet

- **Embedding**: A list of numbers that represents the meaning of a text, so similar texts get nearby vectors.
- **Vector**: An ordered list of numbers; here 1536 floats from `text-embedding-3-small`.
- **Cosine similarity**: The dot product of two vectors divided by their lengths. 1 is same direction, 0 is unrelated.
- **Semantic search**: Finding text by meaning instead of exact keywords, using embeddings.
- **Chunking**: Splitting documents into small pieces (here 30 words) so each vector describes one idea.
- **Chunk size**: How many words go into one chunk. Too big blurs meaning, too small loses context.
- **Embedding pipeline**: The offline job that chunks all documents, embeds them and saves the vectors once.
- **Top-k**: Keep only the k highest-scoring results after ranking.
- **Retrieval**: The step that finds the most relevant stored text for a query. The R in RAG.
- **Brute-force search**: Comparing the query with every stored vector. Simple and exact, slow at large scale.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why must documents and queries use the same embedding model?</summary><p>Each model defines its own vector space. A query vector from one model can't be compared with document vectors from another; the scores would be meaningless.</p></details>
<details><summary>Why embed chunks instead of whole documents?</summary><p>A whole document mixes many topics into one vector, so no topic matches strongly. Small chunks keep one idea per vector and return a focused piece of text.</p></details>
<details><summary>Which OpenAI calls happen during one /search request?</summary><p>One: <code>get_embedding(query)</code>. The chunk vectors were computed earlier by <code>embedding_pipeline.py</code> and are read from <code>embedded_chunks.json</code>.</p></details>
<details><summary>What does /search return for top_k = -1, and why?</summary><p>All chunks except the lowest-ranked one. <code>SearchRequest</code> has no bounds and <code>results[:-1]</code> is a valid Python slice.</p></details>
<details><summary>Why is the LLM not called anywhere in Day 3?</summary><p>Today is only about finding relevant text. Day 4 injects the retrieved chunks into a prompt so the model answers from them.</p></details>
</div>

**Next:** Day 4 – Your First RAG

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
