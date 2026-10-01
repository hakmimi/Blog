---
title: "Day 19: Memory That Persists"
description: "From a graph that forgets you after every request to one that loads your history before routing, rewrites follow-ups, and saves the turn afterwards in SQLite. It also keeps a few durable facts about you, and treats all of it as context, never as a source of facts."
series: "ai-engineering"
order: 21
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "langgraph", "sqlite", "short/long-term memory"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day19`](https://github.com/hakmimi/AIEngineering/tree/main/Day19). Layers touched: L1 Data, L3 Orchestration.

## Goals

- **G1. Tell short-term memory from long-term memory.**  
  You can: show recent turns in `history` and `name: Dana` in `user_facts` in one response.
- **G2. Place memory in the graph: read before routing, write after answering.**  
  You can: read the trace `load_memory → contextualize → … → finish → save_memory`.
- **G3. Persist memory across restarts with SQLite.**  
  You can: restart uvicorn and show `GET /session/me` still returns the turns.
- **G4. Keep memory from becoming a source of made-up facts.**  
  You can: point at the "not a fact source" labels in the prompt and explain why error answers aren't saved.

## System map

Memory wraps the graph from Day 18: two new nodes before routing and a join plus a save node at the end. Routing, retrieval and the LLM call are dashed because they now use the rewritten question and the memory blocks.

> Query → Load Memory → Contextualize → Route → Retrieve / Tool → LLM → Save Memory → Response

<div class="ae-map" role="img" aria-label="The client posts to /rag/graph with an optional session_id. With a session, load_memory reads recent turns and user facts from the SQLite store, and contextualize rewrites a follow-up into a standalone question only when there is history and the question looks context-dependent. Routing, tools and retrieval use that standalone question, and call_llm adds the user facts and conversation to the prompt, labelled as not a fact source. Every terminal path joins at finish, then save_memory stores the turn (except error answers) and any facts extracted by regex rules. The answer returns with a session object. Without a session_id the memory nodes are skipped."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 368" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L3 · MEMORY IN</text><text class="lane" x="508" y="18">L3 · WORK</text><text class="lane" x="752" y="18">L3 · MEMORY OUT</text><text class="lane" x="996" y="18">L1 · MEMORY.PY</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,129 C230,129 230,76 261,76" marker-end="url(#mka)"></path><path class="edge" d="M354,118 L354,137" marker-end="url(#mka)"></path><path class="edge" d="M444,76 C718,76 718,84 993,84" marker-end="url(#mka)"></path><path class="edge" d="M444,182 C474,182 474,76 505,76" marker-end="url(#mka)"></path><path class="edge-old" d="M598,110 L598,130" marker-end="url(#mkm)"></path><path class="edge" d="M688,174 C718,174 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge" d="M932,182 C962,182 962,84 993,84" marker-end="url(#mka)"></path><path class="edge" d="M932,182 C962,182 962,182 993,182" marker-end="url(#mka)"></path><path class="edge-old" d="M688,174 C962,174 962,129 1237,129" marker-end="url(#mkm)"></path><path class="edge-back" d="M1330,160 V250 H110 V170" marker-end="url(#mkg)"></path><g class="node-external"><rect height="76" rx="8" width="180" x="20" y="91"></rect><text class="nt t" text-anchor="middle" x="110" y="115">Client</text><text class="ns s" text-anchor="middle" x="110" y="134">POST /rag/graph</text><text class="ns s" text-anchor="middle" x="110" y="149">+ optional session_id</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="66">load_memory</text><text class="ns s" text-anchor="middle" x="354" y="85">history + user_facts</text><text class="ns s" text-anchor="middle" x="354" y="100">store fails → go on</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="172">contextualize</text><text class="ns s" text-anchor="middle" x="354" y="191">rewrite follow-up</text><text class="ns s" text-anchor="middle" x="354" y="206">only when needed</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="153">NEW</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="508" y="42"></rect><text class="nt t" text-anchor="middle" x="598" y="74">route · tools · RAG</text><text class="ns s" text-anchor="middle" x="598" y="92">all use _q(state)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="54">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="132"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="164">call_llm</text><text class="ns s" text-anchor="middle" x="598" y="184">prompt + facts + history</text><text class="ns s" text-anchor="middle" x="598" y="198">"not a fact source"</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="146">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">finish</text><text class="ns s" text-anchor="middle" x="842" y="85">join for every</text><text class="ns s" text-anchor="middle" x="842" y="100">terminal path</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="172">save_memory</text><text class="ns s" text-anchor="middle" x="842" y="191">turn + facts</text><text class="ns s" text-anchor="middle" x="842" y="206">skip error answers</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="42"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="74">SqliteMemoryStore</text><text class="ns s" text-anchor="middle" x="1086" y="92">messages · facts · sessions</text><text class="ns s" text-anchor="middle" x="1086" y="108">data/memory.db</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="54">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="148"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="180">extract_facts()</text><text class="ns s" text-anchor="middle" x="1086" y="198">regex: name, interest</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="160">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="98"></rect><text class="nt t" text-anchor="middle" x="1330" y="122">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="142">rewrite · embed · answer</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="86"></rect><text class="el" text-anchor="middle" x="230" y="96">JSON</text><rect class="elbg" height="15" rx="3" width="34" x="702" y="63"></rect><text class="el" text-anchor="middle" x="718" y="74">read</text><rect class="elbg" height="15" rx="3" width="130" x="410" y="112"></rect><text class="el" text-anchor="middle" x="474" y="123">standalone question</text><rect class="elbg" height="15" rx="3" width="40" x="942" y="116"></rect><text class="el" text-anchor="middle" x="962" y="127">write</text><rect class="elbg" height="15" rx="3" width="270" x="585" y="243"></rect><text class="el" text-anchor="middle" x="720" y="254">{ …, session: {used_memory, user_facts} }</text><text class="lane" style="fill:var(--ghost)" x="20" y="298">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="174" x="20" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="107" y="335">Day 20 · LLM judge</text></g><g class="node-ghost"><rect height="44" rx="8" width="230" x="214" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="329" y="335">Day 21 · week 3 packaging</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: The graph forgets you

- `/rag/graph` treated every request as the first
- "And its beaches?" was searched as it is, with no idea what "its" means
- Memory existed only on `/chat`, in a JSON file with one lock
- Nothing remembered durable facts like the user's name

### After this episode: Memory inside the workflow

- `session_id` turns on `load_memory`, `contextualize` and `save_memory`
- Follow-ups are rewritten, and routing and retrieval use the rewritten question
- SQLite keeps turns and facts across restarts, with transactions and LRU eviction
- Error answers are never saved, so a bad moment doesn't poison later turns

> **Why it matters:** an assistant that forgets the last message can't hold a conversation, and one that trusts everything it remembers will repeat its own mistakes. The design choices here, what to store, where to read and write, and how much to inject, matter more than the storage engine.

## Code walkthrough

Four snippets from `Day19`. Two nodes, the store, and the rule that becomes today's bug.

### graph.py · read before routing

```python
@timed("contextualize")
def contextualize(state: RagState) -> dict:
    """Follow-up ("And its beaches?") -> standalone question. Only spends an LLM call when it can matter."""
    question, history = state["question"], state.get("history", "")
    if not history or rule_route(question, 4).name == SKIP or not needs_rewrite(question, history):
        return {}
    standalone = rewrite_question(question, history)
    logger.info("memory_rewrite original=%r standalone=%r", question, standalone)
    return {"standalone_question": standalone}

def _q(state: RagState) -> str:
    return state.get("standalone_question") or state["question"]
```

**Rewrite once, early, and let every later step use the result.** No history, small talk, or a question that doesn't look like a follow-up: no LLM call. Otherwise the rewritten question goes into state, and `_q()` makes routing, tools and retrieval all use it.

### graph.py · write after answering

```python
@timed("save_memory")
def save_memory(state: RagState) -> dict:
    """Persist the turn and any durable facts the user stated. Never fails the request."""
    session_id = state["session_id"]
    try:
        for key, value in memory_module.extract_facts(state["question"]).items():
            memory_module.memory.remember(session_id, key, value)
        if state.get("answer") and state.get("source") != "fallback_error":   # don't remember error messages
            memory_module.memory.add_turn(session_id, state["question"], str(state["answer"]))
    except Exception:  # noqa: BLE001
        logger.exception("memory_save_failed session=%s", session_id)
    return {}
```

**Save on every path, but never save an error.** All terminal paths join at `finish`, so this is the only place that writes. It stores the original question, not the rewrite, so the history reads like the real conversation.

### memory.py · SQLite, one transaction

```python
def add_turn(self, session_id: str, question: str, answer: str) -> int:
    now = time.time()
    with closing(self._connect()) as db, db:      # `with db` = one transaction
        db.executemany("INSERT INTO messages(session_id, role, content, ts) VALUES (?,?,?,?)",
                       [(session_id, "user", question, now), (session_id, "assistant", answer, now)])
        ...
        db.execute("DELETE FROM messages WHERE session_id=? AND id NOT IN "
                   "(SELECT id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?)",
                   (session_id, session_id, 2 * self.max_turns))
```

**Parameterised queries, one transaction, bounded history.** The `?` placeholders are why the SQL-injection test passes. The DELETE keeps only the last `MEMORY_MAX_TURNS` turns, and a second loop evicts the least recently seen sessions with their facts.

### memory.py · long-term facts by rule

```python
_FACT_PATTERNS = [
    # (?i:...) makes only the trigger phrase case-insensitive, so a name must still start with a capital
    ("name", re.compile(r"\b(?i:my name is) ([A-Z][a-zA-Z'-]{1,30})")),
    ("name", re.compile(r"\b(?i:call me) ([A-Z][a-zA-Z'-]{1,30})")),
    ("interest", re.compile(r"\b(?i:i'm|i am) (?i:really |very )?(?i:interested in) ([A-Za-z][A-Za-z ,'-]{2,40}?)(?:[.!?]|$)")),
    ("interest", re.compile(r"\b(?i:i) (?i:love|like|enjoy) ([A-Za-z][A-Za-z ,'-]{2,40}?)(?:[.!?]|$)")),
]
```

**Rules are free and auditable, and they only know the words.** The name rule is careful: a name must start with a capital. The last interest rule accepts any three letters after "I like". Keep that in mind for the break-it segment.

## Run it

Run from `Day19` in PowerShell. Use one `session_id` for the whole demo and show the `session` object in each response.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `213 passed`, with 22 new tests in `tests/test_graph_memory.py`, each on an isolated SQLite file.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`. `data/memory.db` is created on start.

**Step 3**

```text
function Ask($q) { (Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" -Body (@{query=$q; session_id="me"} | ConvertTo-Json)).results }
(Ask "Hi, my name is Dana. Tell me about Eilat").session
```

**Expect:** `used_memory: False` on the first turn, and a `memory_fact_saved session=me key=name` log line.

**Step 4**

```text
(Ask "And its beaches?").session
(Ask "What about Masada?").answer
(Ask "How do visitors reach it?") | Select-Object answer, session
```

**Expect:** `standalone_question: What are the beaches like in Eilat?`, then a Masada answer, then "cable car or hiking paths" with `user_facts: name: Dana`.

**Step 5**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/session/me
```

**Expect:** `turns: 4` and the messages in order. Stop uvicorn, start it again, run this again: same result from SQLite.

**Step 6**

```powershell
Invoke-RestMethod -Method Delete http://127.0.0.1:8000/session/me
```

**Expect:** `deleted: True`. Messages and facts for `me` are gone.

### Break it on purpose

#### 1 · "Thanks, I like that!" becomes a fact

In a fresh session say **"I am interested in hiking."**, then **"Thanks, I like that!"**. The second message is small talk and gets a direct reply, but `save_memory` still runs `extract_facts` on it. The `I love|like|enjoy` rule matches "that", and `remember()` upserts, so `interest: hiking` is replaced by **`interest: that`**. The next answer's `user_facts` shows it, and it goes into every prompt for this session. "Would I like Eilat?" stores `interest: Eilat` the same way. Filter vague values and skip questions.

```text
# memory.py
_VAGUE = {"that", "this", "it", "them", "those", "these", "this answer"}

def extract_facts(text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    if (text or "").rstrip().endswith("?"):
        return facts                      # a question is not a statement about the user
    for key, pattern in _FACT_PATTERNS:
        match = pattern.search(text or "")
        if match and key not in facts and match.group(1).strip().lower() not in _VAGUE:
            facts[key] = match.group(1).strip()
    return facts
```

#### 2 · A session id that isn't one

Send `{"query":"Tell me about Eilat","session_id":"bad id"}`. `GraphRequest` accepts the length, but `validate_session_id` rejects the space and the API returns **422** before any node runs. The isolation key has to be clean, or users could end up sharing history.

> Memory is a write path into your prompts. Anything that gets stored will be shown to the model again and again, so the rules for what gets in need the same care as the rules for retrieval.

## Cheat sheet

- **Short-term memory**: The last few turns of this conversation, used to understand follow-ups.
- **Long-term memory**: Durable facts about the user, like a name or an interest, kept across conversations in the same session.
- **session_id**: The isolation key. Without it the memory nodes are skipped; with it, one user never sees another's history.
- **Contextualize**: Rewrite a follow-up into a standalone question, like "And its beaches?" → "What are the beaches like in Eilat?".
- **Standalone question**: A question that makes sense without the conversation. Routing and retrieval use it via `_q(state)`.
- **Join node**: A node where several paths meet. Here `finish`, so saving is attached in one place.
- **SQLite**: A file-based SQL database. Survives restarts and handles concurrent requests with short-lived connections.
- **Transaction**: A group of writes that all happen or none do. `with db:` gives one per `add_turn`.
- **LRU eviction**: When there are too many sessions, delete the least recently seen one, including its facts.
- **Memory poisoning**: Storing something wrong, like an error message or a fake fact, that then misleads every later turn.
- **Prompt budget**: `MEMORY_PROMPT_CHARS` caps how much history goes into the prompt; the newest messages are kept first.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why is memory loaded before routing and not just before the LLM call?</summary><p>Routing, tool selection and retrieval all need to understand the question. "How do visitors reach it?" can't be routed or searched well until "it" becomes Masada.</p></details>
<details><summary>Why aren't error answers saved?</summary><p>A saved "service unavailable" turn would sit in the history and could steer later answers. <code>save_memory</code> skips turns with <code>source: fallback_error</code>.</p></details>
<details><summary>What happens when the SQLite store throws during load_memory?</summary><p>The node logs <code>memory_load_failed</code> and returns empty history and facts. The request continues without memory.</p></details>
<details><summary>Why does the prompt label memory "not a fact source"?</summary><p>Answers must come from the retrieved context. Memory helps the model understand the question and personalise tone, but a claim that only appears in memory must not become an answer.</p></details>
<details><summary>A request comes without session_id. Which nodes run?</summary><p>The Day 18 graph: <code>receive_query</code>, routing, the work nodes and <code>finish</code>. <code>_after_receive</code> skips <code>load_memory</code>, and <code>_after_finish</code> goes to END without <code>save_memory</code>.</p></details>
</div>

**Next:** Day 20 – The LLM Judge

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
