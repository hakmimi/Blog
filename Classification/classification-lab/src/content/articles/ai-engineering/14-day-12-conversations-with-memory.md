---
title: "Day 12: Conversations With Memory"
description: "From an assistant that forgets everything between requests, to one that keeps a bounded history per session, so \"And its beaches?\" knows what \"its\" means. Memory helps the system understand the question, but facts still come only from retrieved context."
series: "ai-engineering"
order: 14
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "session memory", "query rewrite", "json persistence"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day12`](https://github.com/hakmimi/AIEngineering/tree/main/Day12). Layers touched: L1 Data, L3 Orchestration.

## Goals

- **G1. Store short-term conversation state per session, bounded in size.**  
  You can: show `data/sessions.json` and explain `MEMORY_MAX_TURNS`, `MEMORY_MAX_SESSIONS` and LRU eviction.
- **G2. Resolve follow-up questions before retrieval.**  
  You can: ask "And its beaches?" and point at `session.standalone_question` in the response.
- **G3. Inject history into the prompt without letting it become a fact source.**  
  You can: read `CONVERSATION_BLOCK` aloud and say why it goes before the context.
- **G4. Expose and control session state through the API.**  
  You can: read and delete a session with `GET` and `DELETE /session/{id}` and show a 422 for a bad `session_id`.

## System map

A new `/chat` path wraps the Day 9 RAG pipeline with memory on both sides: history is loaded and used before retrieval, and the new turn is saved after the answer.

> Query → Memory (load history) → rewrite follow-up → Retrieval → LLM (+history) → Response → Memory (save turn)

<div class="ae-map" role="img" aria-label="The client calls POST /chat with a session_id and query. chat.py validates the session_id, loads formatted history from the MemoryStore, and if the question looks like a follow-up, asks the LLM to rewrite it as a standalone question. get_rag_answer retrieves with the standalone question and builds a prompt with the conversation block before the context. After the answer, the turn is saved to the MemoryStore, which writes data/sessions.json atomically. GET and DELETE /session/{id} read and clear a session. The response returns to the client with a session object."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 386" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · ROUTES.PY</text><text class="lane" x="508" y="18">L3 · CHAT.PY</text><text class="lane" x="752" y="18">L1 · MEMORY.PY</text><text class="lane" x="996" y="18">L2 · RAG + PROMPTS</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,138 C230,138 230,85 261,85" marker-end="url(#mka)"></path><path class="edge" d="M444,85 C474,85 474,76 505,76" marker-end="url(#mka)"></path><path class="edge" d="M444,184 C596,184 596,84 749,84" marker-end="url(#mka)"></path><path class="edge" d="M688,76 C718,76 718,84 749,84" marker-end="url(#mka)"></path><path class="edge" d="M598,118 L598,137" marker-end="url(#mka)"></path><path class="edge" d="M842,126 L842,144" marker-end="url(#mka)"></path><path class="edge" d="M688,76 C840,76 840,85 993,85" marker-end="url(#mka)"></path><path class="edge" d="M1086,149 L1086,130" marker-end="url(#mka)"></path><path class="edge" d="M1176,85 C1206,85 1206,138 1237,138" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,168 V268 H110 V172" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="108"></rect><text class="nt t" text-anchor="middle" x="110" y="132">Client</text><text class="ns s" text-anchor="middle" x="110" y="150">session_id + query</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="50"></rect><text class="nt t" text-anchor="middle" x="354" y="82">POST /chat</text><text class="ns s" text-anchor="middle" x="354" y="102">ChatRequest</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="64">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="142"></rect><text class="nt t" text-anchor="middle" x="354" y="174">GET/DELETE /session</text><text class="ns s" text-anchor="middle" x="354" y="192">read or clear history</text><text class="ns s" text-anchor="middle" x="354" y="208">validated session_id</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="154">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="66">chat()</text><text class="ns s" text-anchor="middle" x="598" y="85">load → rewrite → RAG</text><text class="ns s" text-anchor="middle" x="598" y="100">→ save turn</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="47">NEW</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="508" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="172">rewrite_question(</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="190">)</text><text class="ns s" text-anchor="middle" x="598" y="209">only if history + short</text><text class="ns s" text-anchor="middle" x="598" y="224">or a reference word</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="42"></rect><text class="nt t" text-anchor="middle" x="842" y="74">MemoryStore</text><text class="ns s" text-anchor="middle" x="842" y="92">last 6 turns · 500 sessions</text><text class="ns s" text-anchor="middle" x="842" y="108">LRU · thread lock</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="54">NEW</text></g><g class="node-new"><rect height="87" rx="8" width="180" x="752" y="148"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="180">data/sessions.jso</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="198">n</text><text class="ns s" text-anchor="middle" x="842" y="216">temp file + os.replace</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="160">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="43"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="75">get_rag_answer()</text><text class="ns s" text-anchor="middle" x="1086" y="94">history threaded through</text><text class="ns s" text-anchor="middle" x="1086" y="109">(Day 9 retrieval)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="56">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="149"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="181">prompts.py</text><text class="ns s" text-anchor="middle" x="1086" y="200">CONVERSATION_BLOCK</text><text class="ns s" text-anchor="middle" x="1086" y="215">REWRITE_PROMPT</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="162">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="108"></rect><text class="nt t" text-anchor="middle" x="1330" y="132">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="150">rewrite + answer</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="94"></rect><text class="el" text-anchor="middle" x="230" y="106">POST</text><rect class="elbg" height="15" rx="3" width="46" x="1183" y="94"></rect><text class="el" text-anchor="middle" x="1206" y="106">prompt</text><rect class="elbg" height="15" rx="3" width="110" x="665" y="261"></rect><text class="el" text-anchor="middle" x="720" y="272">answer + session</text><text class="lane" style="fill:var(--ghost)" x="20" y="316">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="238" x="20" y="326"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="139" y="353">Day 13 · evaluation system</text></g><g class="node-ghost"><rect height="44" rx="8" width="222" x="278" y="326"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="389" y="353">Day 19 · SQLite sessions</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Every request starts from zero

- `/rag` sees one question and nothing else
- "And its beaches?" goes to retrieval with no subject, so it finds nothing useful
- There is no concept of a user session in the API
- Nothing about a conversation survives a server restart

### After this episode: Short-term memory, with limits

- `POST /chat` keeps history per `session_id`; `GET` and `DELETE /session/{id}` expose it
- `needs_rewrite` + `rewrite_question` turn follow-ups into standalone questions, and fail safe to the original
- `render_rag_prompt(..., history)` puts the conversation **before** `<context>`, labelled as not a fact source
- `MemoryStore` keeps 6 turns per session, 500 sessions max, and saves atomically to `data/sessions.json`

> **Why it matters:** every real assistant is multi-turn, and state is where assistants go wrong: unbounded prompts, one user's history leaking into another's, or old answers treated as facts. Building memory by hand shows which choices matter: what to store, how much, where it goes in the prompt, and who can read it.

## Code walkthrough

Four snippets from `Day12`: how memory is stored, how a follow-up is detected, and where history goes in the prompt.

### memory.py · bounded, LRU, atomic

```python
    def add_turn(self, session_id: str, question: str, answer: str) -> int:
        now = time.time()
        with self._lock:
            messages = self._sessions.pop(session_id, [])          # pop + reinsert = mark as most recent
            messages += [{"role": "user", "content": question, "ts": now},
                         {"role": "assistant", "content": answer, "ts": now}]
            self._sessions[session_id] = messages[-2 * self.max_turns:]
            while len(self._sessions) > self.max_sessions:
                evicted, _ = self._sessions.popitem(last=False)
                logger.info("memory_session_evicted session=%s", evicted)
            self._save()
```

**Two limits: turns per session and sessions per server.** Popping and reinserting moves the session to the end of the `OrderedDict`, so the first item is always the least recently used. Without both limits, memory and prompts grow forever.

### chat.py · only rewrite when it's needed

```python
def needs_rewrite(question: str, history: str) -> bool:
    """Only spend an LLM call when there IS history and the question looks context-dependent."""
    if not history:
        return False
    return len(question.split()) <= _SHORT_FOLLOWUP_WORDS or bool(_REFERENCE.search(question))


def rewrite_question(question: str, history: str) -> str:
    try:
        rewritten = get_structured(render_rewrite_prompt(history, question), REWRITE_SCHEMA, "rewrite")["question"].strip()
        return rewritten or question
    except ExternalServiceError:
        logger.warning("rewrite_failed - using the original question")
        return question
```

**A cheap check decides whether to pay for a rewrite.** First turn: no history, no rewrite. Short questions or words like `it`, `there`, `what about` trigger one LLM call. If it fails, the original question goes through unchanged.

### chat.py · the whole flow

```python
    history = memory.format_for_prompt(session_id)
    ...
    standalone = question
    if route_query(question, top_k).name != SKIP and needs_rewrite(question, history):
        standalone = rewrite_question(question, history)
    ...
    result = get_rag_answer(standalone, top_k, None, history)
    result["question"] = question
    result["session"] = {"id": session_id, "turns_before": turns_before,
                         "standalone_question": standalone, "used_memory": bool(history)}
    if result.get("answer"):
        memory.add_turn(session_id, question, result["answer"])
```

**Retrieve with the rewritten question, remember the original one.** The standalone question is what retrieval needs. The user's own words are what belongs in the history. The response shows both, so you can debug a bad rewrite.

### prompts.py · memory is context for the question

```python
CONVERSATION_BLOCK = """Conversation so far (only to understand the question - facts must come from <context>):
{history}

"""
...
def render_rag_prompt(context: str, question: str, history: str = "") -> str:
    prompt = RAG_PROMPT.format(no_context=NO_CONTEXT_ANSWER, context=context, question=question)
    if not history:
        return prompt
    # Day 12: memory goes BEFORE the context block; it explains the question but is not a fact source.
    return CONVERSATION_BLOCK.format(history=history) + prompt
```

**History must not become a hallucination source.** A previous answer might have been wrong, or a user might claim something false. The label and the position tell the model to take facts only from `<context>`.

## Run it

Run from `Day12` in PowerShell. Use the same `session_id` for the whole conversation and show the response's `session` object each time.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `117 passed`, including 22 new memory tests.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on port 8000; `/docs` lists `/chat` and `/session/{session_id}`.

**Step 3**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method Post `
  -ContentType "application/json" `
  -Body '{"session_id":"demo","query":"Tell me about Eilat"}').results.session
```

**Expect:** `turns_before: 0`, `used_memory: False`, and `standalone_question` equal to the question. The answer is grounded as usual.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method Post `
  -ContentType "application/json" `
  -Body '{"session_id":"demo","query":"And its beaches?"}').results
```

**Expect:** `session.standalone_question` resolves "its" to Eilat, `used_memory: True`, and a grounded answer. The log shows `rewritten=True`.

**Step 5**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/session/demo | ConvertTo-Json -Depth 4
```

**Expect:** `turns: 2` and four messages with `role`, `content`, `ts`. Open `data/sessions.json` to show the same data on disk.

**Step 6**

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/session/demo -Method Delete
```

**Expect:** `deleted: True`. Call it again and get `deleted: False`.

### Break it on purpose

#### 1 · A malicious session_id

Send `/chat` with `"session_id":"../x"` or `"my session"`. `validate_session_id` rejects it with **422** and the message `session_id must be 1-64 characters: letters, digits, '_' or '-'`. Today sessions are keys in one JSON file, but Day 19 moves them to a database. An id that is safe as a key, a filename and a log field is a boundary worth keeping.

#### 2 · Reading someone else's conversation

In a second terminal, pretend to be another user and call `GET /session/demo`. You get the whole history. The only protection is the optional `X-API-Key`, which is shared by every client, and there's no link between a session and who created it. With guessable ids like `demo`, one user can read or delete another's conversation. Show the fix direction: generate ids on the server, and treat them like secrets.

```text
# routes.py - let the server create ids no one can guess
import secrets

@router.post("/session", dependencies=protected)
def new_session() -> dict:
    return {"session_id": secrets.token_urlsafe(16)}
```

> Memory is user data. Bounding it keeps prompts small, and scoping it keeps it private. The code does the first well; the second still depends on ids no one can guess.

## Cheat sheet

- **Session**: One conversation, identified by `session_id`, holding a list of `{role, content, ts}` messages.
- **Short-term memory**: Recent turns kept to understand the current question. Here: the last 6 turns per session.
- **Turn**: One user message plus the assistant's reply.
- **LRU eviction**: When there are more than `MEMORY_MAX_SESSIONS` sessions, drop the one used least recently.
- **Atomic write**: Write a temp file, then `os.replace` it over the real one, so a crash never leaves a half-written file.
- **Query rewriting (follow-up)**: Turning "And its beaches?" into a standalone question using the conversation, before retrieval.
- **Standalone question**: A question that makes sense with no history. Returned as `session.standalone_question`.
- **Prompt budget**: `MEMORY_PROMPT_CHARS` (1200): only the newest messages that fit are put in the prompt.
- **Memory as context only**: History helps interpret the question; answers must still come from retrieved `<context>`.
- **Session isolation**: One session's history never appears in another's prompt. Tested, but reading via `/session/{id}` is only as private as the id.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why isn't history alone enough to answer "And its beaches?"</summary><p>Retrieval embeds only the question. Without a subject it can't find Eilat's chunks. The rewrite produces a standalone question for retrieval; history in the prompt alone wouldn't fix the search.</p></details>
<details><summary>When does chat() spend an LLM call on a rewrite?</summary><p>Only when the session already has history, the question isn't smalltalk, and it's 6 words or fewer or contains a reference word like <code>it</code>, <code>there</code> or <code>what about</code>.</p></details>
<details><summary>Why are retrieved chunks and timings not stored in memory?</summary><p>They can be recomputed and would bloat both the file and the prompt. Memory stores only the conversation.</p></details>
<details><summary>Why does CONVERSATION_BLOCK say facts must come from &lt;context&gt;?</summary><p>Earlier answers or user claims might be wrong. Labelling history as 'only to understand the question' stops it from becoming a hallucination source.</p></details>
<details><summary>What stops sessions.json from growing forever?</summary><p>Each session keeps only the last <code>MEMORY_MAX_TURNS</code> turns, and at most <code>MEMORY_MAX_SESSIONS</code> sessions exist; the least recently used is evicted.</p></details>
</div>

**Next:** Day 13 – The Evaluation Loop

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
