---
title: "Day 4: Your First RAG"
description: "Day 3 could find the right chunks but couldn't answer. Today we connect retrieval to the LLM: retrieve, inject the chunks into the prompt, answer from them, and fall back to the plain model when nothing relevant is found."
series: "ai-engineering"
order: 5
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "rag", "context injection", "fallback"]
readingTime: "7 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day4`](https://github.com/hakmimi/AIEngineering/tree/main/Day4). Layers touched: L1 Data, L2 LLM, L3 Orchestration, L4 System.

## Goals

- **G1. Explain the RAG flow: retrieve, inject context, generate.**  
  You can: trace one `/rag` request through `get_rag_answer()` and name each step on the map.
- **G2. Build a prompt that carries retrieved context.**  
  You can: show `build_context()` and `rag_prompt`, and point at the rule that says use ONLY the context.
- **G3. Decide when retrieval is good enough with a score threshold.**  
  You can: read `BEST SCORE` in the logs and say why 0.55 sends one question to RAG and another to fallback.
- **G4. Make the response show where the answer came from.**  
  You can: compare `source: embeddings` with `source: llm_fallback` and the `retrieved_chunks` list in each.

## System map

Day 3's retrieval is now grey. The new column in the middle is the RAG orchestrator, and the LLM comes back on the right. Two paths leave the score check: with context, or the fallback without it.

> Query → Retrieve → best score ≥ 0.55? → Inject context → LLM → Answer (else: LLM without context)

<div class="ae-map" role="img" aria-label="A client posts a query to /rag. get_rag_answer calls get_relevant_chunks from Day 3, which embeds the query and ranks stored chunks. If the best score is at least 0.55, build_context joins the chunk texts into a rag_prompt and get_answer calls the OpenAI Responses API. If not, the question goes to get_answer with no context and the response is marked llm_fallback. The answer, confidence and retrieved chunks return to the client. /search from Day 3 still exists."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 451" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L3 · RAG.PY</text><text class="lane" x="752" y="18">L1 · L3 RETRIEVAL</text><text class="lane" x="996" y="18">L2 · PROMPT + LLM.PY</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,170 C230,170 230,129 261,129" marker-end="url(#mka)"></path><path class="edge-old" d="M200,170 C230,170 230,216 261,216" marker-end="url(#mkm)"></path><path class="edge" d="M444,129 C474,129 474,170 505,170" marker-end="url(#mka)"></path><path class="edge" d="M688,170 C718,170 718,166 749,166" marker-end="url(#mka)"></path><path class="edge-old" d="M842,216 L842,235" marker-end="url(#mkm)"></path><path class="edge-old" d="M842,95 L842,114" marker-end="url(#mkm)"></path><path class="edge" d="M932,166 C962,166 962,125 993,125" marker-end="url(#mka)"></path><path class="edge" d="M932,272 C962,272 962,224 993,224" marker-end="url(#mka)"></path><path class="edge" d="M1086,167 L1086,186" marker-end="url(#mka)"></path><path class="edge" d="M1176,224 C1206,224 1206,170 1237,170" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,201 V333 H110 V204" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="140"></rect><text class="nt t" text-anchor="middle" x="110" y="164">Client</text><text class="ns s" text-anchor="middle" x="110" y="183">/docs · test_app.py</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="94"></rect><text class="nt t" text-anchor="middle" x="354" y="126">POST /rag</text><text class="ns s" text-anchor="middle" x="354" y="146">SearchRequest: query, top_k</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="108">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="264" y="186"></rect><text class="nt t" text-anchor="middle" x="354" y="210">POST /search</text><text class="ns s" text-anchor="middle" x="354" y="228">Day 3 retrieval only</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="136"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="168">get_rag_answer()</text><text class="ns s" text-anchor="middle" x="598" y="187">the RAG pipeline</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="149">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="34"></rect><text class="nt t" text-anchor="middle" x="842" y="58">embedded_chunks.json</text><text class="ns s" text-anchor="middle" x="842" y="77">built on Day 3</text></g><g class="node-changed"><rect height="99" rx="8" width="180" x="752" y="117"></rect><text class="nt t" text-anchor="middle" x="842" y="149">get_relevant_chunks()</text><text class="ns s" text-anchor="middle" x="842" y="168">embed query · cosine ·</text><text class="ns s" text-anchor="middle" x="842" y="183">top-k</text><text class="ns s" text-anchor="middle" x="842" y="198">+ timing log</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="130">CHANGED</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="238"></rect><text class="nt t" text-anchor="middle" x="842" y="270">best score &lt; 0.55?</text><text class="ns s" text-anchor="middle" x="842" y="289">yes → fallback, no context</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="251">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="83"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="115">build_context()</text><text class="ns s" text-anchor="middle" x="1086" y="134">chunk texts → context</text><text class="ns s" text-anchor="middle" x="1086" y="149">→ rag_prompt</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="96">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="189"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="221">get_answer()</text><text class="ns s" text-anchor="middle" x="1086" y="240">JSON: answer, confidence</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="202">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="140"></rect><text class="nt t" text-anchor="middle" x="1330" y="164">OpenAI</text><text class="ns s" text-anchor="middle" x="1330" y="183">embeddings · gpt-4.1-mini</text></g><rect class="elbg" height="15" rx="3" width="40" x="210" y="133"></rect><text class="el" text-anchor="middle" x="230" y="144">query</text><rect class="elbg" height="15" rx="3" width="85" x="676" y="152"></rect><text class="el" text-anchor="middle" x="718" y="162">query, top_k</text><rect class="elbg" height="15" rx="3" width="46" x="939" y="129"></rect><text class="el" text-anchor="middle" x="962" y="140">≥ 0.55</text><rect class="elbg" height="15" rx="3" width="59" x="933" y="231"></rect><text class="el" text-anchor="middle" x="962" y="242">fallback</text><rect class="elbg" height="15" rx="3" width="72" x="1090" y="166"></rect><text class="el" text-anchor="start" x="1092" y="176">rag_prompt</text><rect class="elbg" height="15" rx="3" width="162" x="639" y="326"></rect><text class="el" text-anchor="middle" x="720" y="337">answer · source · chunks</text><text class="lane" style="fill:var(--ghost)" x="20" y="381">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="391"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="418">Day 4+ · production hardening</text></g><g class="node-ghost"><rect height="44" rx="8" width="214" x="300" y="391"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="407" y="418">Day 5 · RAG reliability</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Two halves that don't meet

- `/search` returns chunks but never answers the question
- The LLM code from Days 1–2 answers from general knowledge only
- Nobody decides whether the retrieved text is good enough
- The response can't say where an answer came from

### After this episode: Answers grounded in our data

- `POST /rag` runs retrieve → inject → generate in `get_rag_answer()`
- The prompt says: use ONLY the provided context
- A 0.55 score threshold chooses RAG or the fallback
- Every response carries `source` and the `retrieved_chunks` it used

> **Why it matters:** this is the architecture behind most AI assistants built on company data. From here on, when an answer is wrong you can ask a better question than "is the model bad?": was the retrieval wrong, the context badly formatted, or the prompt unclear?

## Code walkthrough

Four snippets from `Day4`. Most of today's code lives in `rag.py`.

### rag.py · context injection

```python
def build_context(chunks : list[float]) -> str:
    context = "" 
    for chunk in chunks:
        context += chunk['text'] + "\n\n"
    return context
...
        rag_prompt = f"""
        You are a helpful AI assistant.
        Use ONLY the provided context to answer the question.
       
        Context: {context}
        Question: {question}
        """
```

**Augmenting a prompt is string building, nothing more.** The chunk texts are joined and dropped into the prompt above the question. The ONLY rule is the difference between answering from our data and answering from memory. Note the type hint says `list[float]` but it receives a list of dicts.

### rag.py · the branch

```python
def get_rag_answer(question : str,top_k:int =3) -> dict:
    chunks = get_relevant_chunks(question,top_k)
    best_score = chunks[0]['score'] if len(chunks)>0  else 0
    ...
    if best_score < 0.55:
        logging.info(f'"Using Fallback logic, no chunks available')
        llm_response = get_answer(question)
        return({'question' : question,
            ...
            'retrieved_chunks' : [],
            'source': 'llm_fallback'
            })
```

**One number decides whether the model reads our data or guesses.** Chunks are sorted, so `chunks[0]` is the best one. Below 0.55 the question goes to the model with no context. The log says `no chunks available`, but chunks were found; they were just weak.

### llm.py · the call inside the call

```python
def get_answer(question : str) -> dict:
    prompt = f"""
        You are a helpful AI assistant.
        Answer the user's question and return the result in the following JSON format:
        {{
        "answer": "...",
        "confidence": number between 0 and 1,
        }}
        Question: {question}
        """
    ...
        return  {
                 "answer":data.get("answer"),
                 "confidence" :data.get("confidence"),
                 "score" : data.get('score')
                    }
```

**The whole RAG prompt arrives here as the question.** `get_rag_answer()` passes `rag_prompt` into `get_answer()`, which wraps it in another prompt. It works, but it's a prompt inside a prompt. And the JSON format never asks for `score`, so `score` in every response is `null`.

### main.py · the endpoint

```python
@app.post('/rag')
def get_rag_llm(request : SearchRequest) -> dict:
    logging.info(f"Search query: {request.query}")
    response = get_rag_answer(request.query,request.top_k)
    logging.info(f"Top K: {request.top_k}")
    logging.info(f"Retrieved chunks: {len(response.get('retrieved_chunks', []))}")
    
    return({'results':response})
```

**The endpoint is thin because the pipeline is a function.** `/rag` reuses Day 3's `SearchRequest`, so `top_k` defaults to 4 here even though `get_rag_answer()` defaults to 3. The API default wins.

## Run it

Run from the `Day4` folder in PowerShell. Keep the uvicorn log visible: `BEST SCORE` and the branch message are the story.

**Step 1**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on port 8000. `/docs` now lists `/rag` next to `/search`.

**Step 2**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/search" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Why is Jerusalem so important?","top_k":4}' |
  ConvertTo-Json -Depth 4
```

**Expect:** Day 3 behaviour: four chunks and scores, no answer. Note the top score.

**Step 3**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Why is Jerusalem so important?","top_k":4}' |
  ConvertTo-Json -Depth 4
```

**Expect:** `source: embeddings`, an `answer` built from the chunks, and the same four chunks in `retrieved_chunks`. Log: `BEST SCORE` and `Using RAG based on 4 chunks`.

**Step 4**

```powershell
python tests\test_app.py
```

**Expect:** The same `/rag` call through `requests`, printed as a dict.

**Step 5**

```powershell
python tests\test_rag_directly.py
```

**Expect:** Calls `get_rag_answer("What is special about Lumaria?", top_k=2)` without the server and prints the answer and the chunks. Go to Break it.

### Break it on purpose

#### 1 · The fallback that makes things up

Lumaria is a made-up place. Unless your `docs.json` mentions it, the best score stays under 0.55 and the fallback sends the bare question to the model. The response says `source: llm_fallback`, `retrieved_chunks: []`, and an `answer` about a place our data knows nothing about. With the fallback, the system can't tell our facts from the model's guesses. Day 5 replaces this with an honest "not enough information" answer.

```text
# rag.py: refuse instead of guessing (Day 5 does this properly)
if best_score < 0.55:
    return {'question': question,
            'answer': "I don't have enough information to answer that.",
            'retrieved_chunks': [], 'source': 'no_context'}
```

#### 2 · A timer that never resets

Call `/rag` three times and read `Request took ... seconds` in the log: the number keeps growing. `start = time.time()` sits at module level in `retrieval.py`, so it runs once when the server imports the file. Every request reports time since startup, not its own duration.

```python
def get_relevant_chunks(query: str,top_k: int=4):
    start = time.time()   # per request
    ...
    logging.info(f"Request took {time.time() - start:.2f} seconds")
```

> RAG quality depends on the decisions around the model: the threshold, the fallback, and whether your measurements are right. A fallback that guesses and a timer that lies both look like working code.

## Cheat sheet

- **RAG**: Retrieval-Augmented Generation: find relevant text, add it to the prompt, and let the model answer from it.
- **Context injection**: Putting retrieved text into the prompt so the model reads it before answering.
- **Grounding**: Making an answer depend on provided sources instead of the model's memory.
- **Retrieval threshold**: The minimum similarity score (0.55 here) needed to trust the retrieved chunks.
- **Fallback**: What the system does when the main path can't run. Here: ask the model without context.
- **Hallucination**: A confident answer that isn't supported by any source.
- **top_k tuning**: Choosing how many chunks to inject. Too few misses facts, too many adds noise and cost.
- **source field**: A response field that says which path produced the answer: `embeddings` or `llm_fallback`.
- **Pipeline function**: One function (`get_rag_answer`) that runs every step, so the API layer stays thin.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Name the three steps of RAG and where each happens in the code.</summary><p>Retrieve: <code>get_relevant_chunks()</code> in <code>retrieval.py</code>. Augment: <code>build_context()</code> and <code>rag_prompt</code> in <code>rag.py</code>. Generate: <code>get_answer()</code> in <code>llm.py</code>.</p></details>
<details><summary>Why does the prompt say 'Use ONLY the provided context'?</summary><p>So the model answers from our data instead of its general knowledge, and the answer can be traced to the retrieved chunks.</p></details>
<details><summary>Why is chunks[0] the best chunk?</summary><p><code>get_relevant_chunks()</code> sorts results by score in descending order before slicing, so the first item has the highest similarity.</p></details>
<details><summary>What is risky about the llm_fallback path?</summary><p>It asks the model with no context, so for questions outside the data it answers from memory or invents an answer, and the user can't tell.</p></details>
<details><summary>Why does the response's score field always come back null?</summary><p><code>get_answer()</code> reads <code>data.get('score')</code>, but its JSON format only asks for <code>answer</code> and <code>confidence</code>. The model never returns a score.</p></details>
</div>

**Next:** Day 4+ – Hardening Your RAG

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
