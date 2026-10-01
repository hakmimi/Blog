---
title: "Day 14: One System, One Story"
description: "From thirteen days of separate endpoints and scripts to one assistant behind one POST /ask , with memory, rule-picked tools and RAG in a single flow. The episode ends with a clean folder, an architecture doc, a full-system eval and a 60-second explanation you can give in an interview."
series: "ai-engineering"
order: 16
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "assistant.py", "scripts/", "architecture.md"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day14`](https://github.com/hakmimi/AIEngineering/tree/main/Day14). Layers touched: L3 Orchestration, L4 System.

## Goals

- **G1. Compose the tested modules into one entry point instead of writing new logic.**  
  You can: walk through `assistant.ask()` and say which module does each step.
- **G2. Separate runtime code from measurement tools.**  
  You can: show the `scripts/` folder and run a script with `python -m scripts.evaluate`.
- **G3. Evaluate the complete system, not just the RAG path.**  
  You can: run `evaluate run mine assistant` and read accuracy, hallucination and latency aloud.
- **G4. Explain the whole flow in about a minute.**  
  You can: deliver the 60-second explanation from the README without notes.

## System map

This is the whole first system on one screen. Only three boxes are new or changed today: the `/ask` route, `assistant.ask()` and the extra rule in `rule_decision()`. Everything grey is Days 1–13, reused as is.

> Query → Decision → Retrieval → Memory → Tools → LLM → Response

<div class="ae-map" role="img" aria-label="The client posts session_id and query to POST /ask, and the evaluation script calls assistant.ask directly. assistant.ask runs the rule router, then rule_decision. Obvious arithmetic or list-topics requests go to tools.py, and the LLM phrases the tool result. Everything else goes to chat(), which loads memory, rewrites follow-ups and runs retrieval with the score gate before the LLM. The answer returns to the client and the turn is saved to memory."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 420" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CALLERS</text><text class="lane" x="264" y="18">L4 · ROUTES.PY</text><text class="lane" x="508" y="18">L3 · ASSISTANT.PY</text><text class="lane" x="752" y="18">L3 · DECISION</text><text class="lane" x="996" y="18">L1 · MODULES</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,102 C230,102 230,106 261,106" marker-end="url(#mka)"></path><path class="edge" d="M200,196 C352,196 352,106 505,106" marker-end="url(#mka)"></path><path class="edge" d="M444,106 C474,106 474,106 505,106" marker-end="url(#mka)"></path><path class="edge-old" d="M598,148 L598,167" marker-end="url(#mkm)"></path><path class="edge" d="M688,106 C718,106 718,114 749,114" marker-end="url(#mka)"></path><path class="edge" d="M688,106 C718,106 718,208 749,208" marker-end="url(#mka)"></path><path class="edge" d="M932,114 C962,114 962,64 993,64" marker-end="url(#mka)"></path><path class="edge-old" d="M932,208 C962,208 962,155 993,155" marker-end="url(#mkm)"></path><path class="edge-old" d="M932,208 C962,208 962,246 993,246" marker-end="url(#mkm)"></path><path class="edge-old" d="M1176,64 C1206,64 1206,155 1237,155" marker-end="url(#mkm)"></path><path class="edge-old" d="M1176,155 C1206,155 1206,155 1237,155" marker-end="url(#mkm)"></path><path class="edge-back" d="M1330,186 V302 H110 V136" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="72"></rect><text class="nt t" text-anchor="middle" x="110" y="96">Client</text><text class="ns s" text-anchor="middle" x="110" y="114">/docs · PowerShell</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="20" y="154"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="186">scripts.evaluate</text><text class="ns s" text-anchor="middle" x="110" y="206">run … assistant</text><text class="ns s" text-anchor="middle" x="110" y="220">stability a b</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="168">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="64"></rect><text class="nt t" text-anchor="middle" x="354" y="96">POST /ask</text><text class="ns s" text-anchor="middle" x="354" y="115">auth · rate limit</text><text class="ns s" text-anchor="middle" x="354" y="130">ChatRequest</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="77">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="170"></rect><text class="nt t" text-anchor="middle" x="354" y="194">other endpoints</text><text class="ns s" text-anchor="middle" x="354" y="213">/rag · /chat · /ask/tools</text><text class="ns s" text-anchor="middle" x="354" y="228">Days 4–13 (unchanged)</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="64"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="96">assistant.ask()</text><text class="ns s" text-anchor="middle" x="598" y="115">tool or chat?</text><text class="ns s" text-anchor="middle" x="598" y="130">one entry point</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="77">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="508" y="170"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="194">route_query()</text><text class="ns s" text-anchor="middle" x="598" y="213">greeting · too short</text><text class="ns s" text-anchor="middle" x="598" y="228">0 API calls</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="72"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="104">rule_decision()</text><text class="ns s" text-anchor="middle" x="842" y="122">arithmetic</text><text class="ns s" text-anchor="middle" x="842" y="138">+ "list &lt;category&gt; topics"</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="84">CHANGED</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="178"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="202">chat()</text><text class="ns s" text-anchor="middle" x="842" y="220">memory · follow-up rewrite</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="996" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="58">tools.py</text><text class="ns s" text-anchor="middle" x="1086" y="77">calculate · list_topics</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="996" y="117"></rect><text class="nt t" text-anchor="middle" x="1086" y="141">retrieval + gate</text><text class="ns s" text-anchor="middle" x="1086" y="160">FAISS · siblings</text><text class="ns s" text-anchor="middle" x="1086" y="175">refuse before the LLM</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="996" y="215"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="239">memory.py</text><text class="ns s" text-anchor="middle" x="1086" y="258">per-session turns</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="124"></rect><text class="nt t" text-anchor="middle" x="1330" y="148">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="168">embeddings · answers</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="87"></rect><text class="el" text-anchor="middle" x="230" y="98">JSON</text><rect class="elbg" height="15" rx="3" width="59" x="323" y="134"></rect><text class="el" text-anchor="middle" x="352" y="145">22 cases</text><rect class="elbg" height="15" rx="3" width="91" x="1161" y="93"></rect><text class="el" text-anchor="middle" x="1206" y="104">phrase result</text><rect class="elbg" height="15" rx="3" width="98" x="671" y="295"></rect><text class="el" text-anchor="middle" x="720" y="306">{ results: … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="350">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="230" x="20" y="360"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="135" y="387">Day 15 · LangGraph basics</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="270" y="360"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="400" y="387">Day 16 · routing in the graph</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Many parts, no front door

- Memory lived on `/chat`, tools on `/ask/tools`, plain RAG on `/rag`
- Measurement scripts sat next to runtime code in the top folder
- `evaluate.py` could only score `rag` or `multistep`, not the full system
- A "list the history topics" request cost an extra decision LLM call

### After this episode: One assistant you can explain

- `POST /ask` runs memory, rule-picked tools and RAG in one call
- Dev tools live in `scripts/` and run as `python -m scripts.<name>`
- The eval scores the `assistant` system: accuracy 1.00, hallucination 0.00
- `docs/ARCHITECTURE.md` holds the flow, module map, decision log and limits

> **Why it matters:** a project you can't explain end to end is a pile of experiments. Consolidating now gives the next phase a stable baseline: on Day 15 the same flow gets rebuilt as a graph, and you need to know exactly what it does first.

## Code walkthrough

Four snippets from `Day14`. The first one is the whole new orchestration layer; the rest show how little changed around it.

### assistant.py · the front door

```python
def ask(session_id: str, question: str, top_k: int = 4) -> dict:
    validate_session_id(session_id)
    question = (question or "").strip()
    route = route_query(question, top_k)

    decision = rule_decision(question) if route.name not in (SKIP, CLARIFY) else None
    if decision:
        logger.info("assistant path=tool tool=%s session=%s", decision.tool, session_id)
        result = run_with_tools(question, top_k)
        result["session"] = {"id": session_id, "used_memory": False}
        if result.get("answer"):
            memory.add_turn(session_id, question, str(result["answer"]))
        return result

    logger.info("assistant path=chat route=%s session=%s", route.name, session_id)
    return chat(session_id, question, top_k)
```

**Compose, don't duplicate: the function decides tool or chat, and that's all.** Memory, rewriting, retrieval and prompting all happen inside `chat()`, which was tested on Day 12. Tool turns are saved to memory too, so a later follow-up can see them.

### tool_agent.py · a second free rule

```python
_LIST_INTENT = re.compile(r"^\s*(list|show|which|what)\b.{0,40}\b(topics|places|categories|subjects)\b", re.I)
_CATEGORIES = ("city", "nature", "history", "culture", "technology", "society", "industry")

def rule_decision(question: str) -> ToolDecision | None:
    ...
    if _LIST_INTENT.match(question):
        category = next((c for c in _CATEGORIES if re.search(rf"\b{c}\b", question, re.I)), None)
        return ToolDecision("list_topics", {"category": category}, "rule")
    return None
```

**Rules first, because the obvious cases shouldn't cost an LLM call.** "List the nature topics" now goes straight to `list_topics` with `category="nature"`. Keep an eye on how wide that regex is. It comes back in the break-it segment.

### routes.py · the new endpoint

```python
@router.post("/ask", dependencies=protected)
def ask_endpoint(request: ChatRequest) -> dict:
    """Day 14: the complete assistant - memory + rule-based tools + RAG in one call."""
    return {"results": ask(request.session_id, request.query, request.top_k)}
```

**The route is three lines because the logic lives elsewhere.** Same `protected` dependencies as every other paid endpoint: API key and rate limit. `ChatRequest` already validates `session_id` and `query`.

### scripts/evaluate.py · scoring the full system

```python
if name == "assistant":  # the complete system, each question in a throwaway session
    import uuid

    from assistant import ask
    return lambda q: ask(f"eval-{uuid.uuid4().hex[:8]}", q, 4)
...
def stability(a: str, b: str) -> None:
    ...
    same = sum(x["answer"] == y["answer"] for x, y in zip(ra, rb))
    verdict = sum(x["passed"] == y["passed"] for x, y in zip(ra, rb))
```

**Every eval question gets a fresh session, so memory can't leak between cases.** `stability` answers a question people rarely measure: at temperature 0, how often is the answer word for word the same? Here 17 of 22, while the pass/fail verdict matched 22 of 22.

## Run it

Run from `Day14` in PowerShell. Keep the uvicorn terminal visible next to the responses so the `assistant path=` log lines show which branch ran.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `142 passed`, including the new `tests/test_assistant.py`. No API key needed.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`.

**Step 3**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post `
  -ContentType "application/json" `
  -Body '{"session_id":"me","query":"Tell me about Eilat"}').results
```

**Expect:** `source: rag`, a grounded answer, `session.used_memory: False`. The log shows `assistant path=chat`.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post `
  -ContentType "application/json" `
  -Body '{"session_id":"me","query":"And its beaches?"}').results.session
```

**Expect:** `used_memory: True` and a `standalone_question` that names Eilat.

**Step 5**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post `
  -ContentType "application/json" `
  -Body '{"session_id":"me","query":"List the history topics"}').results.tool
```

**Expect:** `name: list_topics`, `decided_by: rule`, and an `output` list with Akko, Caesarea, Masada and more.

**Step 6**

```powershell
python -m scripts.evaluate run mine assistant
python -m scripts.evaluate stability v3 v4
```

**Expect:** 22 PASS/FAIL lines and a summary with `"system": "assistant"`. Then `identical answers: 17/22 same pass/fail verdict: 22/22`.

### Break it on purpose

#### 1 · The list rule steals a real question

Ask `/ask` with **"What are the best places to visit in Eilat?"**. It starts with `what` and contains `places`, so `_LIST_INTENT` matches and the rule picks `list_topics` with no category. The user gets a list of every topic in the knowledge base, not an answer about Eilat, and the response says `decided_by: rule`. None of the 22 eval cases starts that way, which is why the eval stayed at 100 %. Tighten the rule so only requests about the list itself match, and add the Eilat question to the test that checks knowledge questions are left alone.

```text
# tool_agent.py: "list/show ... topics" or "which/what topics are|do ..." only
_LIST_INTENT = re.compile(
    r"^\s*(?:(?:list|show)\b.{0,40}\b(?:topics|places|categories|subjects)\b"
    r"|(?:which|what)\s+(?:topics|places|categories|subjects)\s+(?:are|do|does|can)\b)", re.I)

# tests/test_assistant.py
@pytest.mark.parametrize("q", [..., "What are the best places to visit in Eilat?"])
def test_rules_leave_knowledge_questions_alone(q): ...
```

#### 2 · A session id with a space

Send `{"session_id":"bad id","query":"Tell me about Eilat"}`. `validate_session_id` rejects it and the API returns **422** before any retrieval or model call. That's the isolation key protecting itself.

> Consolidation is where hidden assumptions show up. A rule that looked safe in isolation now sits in front of every question, and a small eval set didn't catch it. Each new shortcut in front of the main path needs its own negative tests.

## Cheat sheet

- **Consolidation**: Turning working pieces into one coherent project: one entry point, clear folders, docs and tests.
- **Entry point**: The single function or endpoint that every request goes through. Here, `assistant.ask()` behind `POST /ask`.
- **Orchestration**: The code that decides which component runs next. It should decide, not do the work itself.
- **Compose, don't duplicate**: Build the full system by calling tested modules, instead of copying their logic into a new file.
- **Rule-based decision**: A regex or check that picks a tool for free and the same way every time, before any LLM is asked.
- **python -m**: Runs a module by its package path (`scripts.evaluate`), so imports from the project root keep working.
- **Dead import**: An import nothing uses. `ruff --select F` finds these and other unused names.
- **Stability**: How often two runs of the same eval give identical answers. It tells you how much run-to-run noise to expect.
- **Decision log**: A table of design choices with the reason and the measured evidence, like "refuse before the LLM → hallucination 0 %".
- **Known limits**: An honest list of what the system doesn't handle yet, such as in-process memory and a small eval set.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>What does assistant.ask() decide, and what does it hand off?</summary><p>It only decides between the tool path and the chat path. Routing, memory, rewriting, retrieval and prompting are done by <code>route_query</code>, <code>chat()</code> and the modules behind it.</p></details>
<details><summary>Why do eval runs of the assistant use a new session id for every question?</summary><p>So one case's history can't change the next case's answer. Each question is scored alone, which keeps the results reproducible.</p></details>
<details><summary>"List the nature topics" costs how many LLM calls now, and why?</summary><p>One: the call that phrases the tool result. <code>rule_decision</code> picks <code>list_topics</code> with <code>category="nature"</code> itself, so there is no decision call.</p></details>
<details><summary>Accuracy stayed at 1.00 in two runs but only 17 of 22 answers were identical. Is that a problem?</summary><p>No. The wording varies a little even at temperature 0, but every verdict matched. It tells you to score content with checks, not by exact string matching.</p></details>
<details><summary>Why move evaluate.py and friends into scripts/?</summary><p>They measure the system but aren't part of it. Keeping them out of the runtime folder makes the production code easier to read and review.</p></details>
</div>

**Next:** Day 15 – Pipeline as a Graph

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
