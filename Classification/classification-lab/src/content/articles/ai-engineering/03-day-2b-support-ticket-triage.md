---
title: "Day 2b: Support Ticket Triage"
description: "Day 2 answered general questions. Day 2b points the same pipeline at a real job: an airline support ticket comes in, and the API returns a category, a priority and a suggested reply for the agent."
series: "ai-engineering"
order: 3
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "ticket classifier", "output contract", "gpt-4.1-nano"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day2b`](https://github.com/hakmimi/AIEngineering/tree/main/Day2b). Layers touched: L2 LLM, L3 Orchestration, L4 System.

## Goals

- **G1. Turn a generic Q&A pipeline into a use case with business fields.**  
  You can: send a ticket to `/llm/regular` and read `category`, `priority` and `suggested_reply` in the response.
- **G2. Write domain rules that route tickets before the model sees them.**  
  You can: walk through `classify_ticket()` and show that the order of the checks decides the category.
- **G3. Put bounds on the model's output with Pydantic.**  
  You can: point at `ge=0, le=1` and `max_length=500` in `LLMResponse` and say what happens when the model breaks them.
- **G4. Keep the pipeline shape from Day 2 and only swap the content.**  
  You can: show that `build_prompt`, `TEMPERATURE_BY_STYLE` and the two-role call are unchanged in structure.

## System map

Same shape as Day 2. Almost every box is dashed: the pipeline stays, the content becomes airline support. Only the ticket classifier is new.

> Ticket → Pydantic → /llm/regular → classify_ticket → style + temperature → airline prompts → gpt-4.1-nano → category · priority · reply

<div class="ae-map" role="img" aria-label="A client sends a ticket to the UserRequest model and POST /llm/regular. get_answer classifies the ticket as billing, account, technical or general, maps it to a prompt style and temperature, fills an airline-support template and adds the airline system prompt, then calls gpt-4.1-nano. The reply goes through the LLMResponse contract with category, priority, suggested_reply, temperature and confidence. Any failure returns HTTP 500."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 496" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L4 · MAIN.PY</text><text class="lane" x="752" y="18">L3 · LLM.PY RULES</text><text class="lane" x="996" y="18">L2 · LLM.PY PROMPTS</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,182 C230,182 230,122 261,122" marker-end="url(#mka)"></path><path class="edge" d="M444,122 C474,122 474,140 505,140" marker-end="url(#mka)"></path><path class="edge-old" d="M598,175 L598,194" marker-end="url(#mkm)"></path><path class="edge" d="M688,140 C718,140 718,122 749,122" marker-end="url(#mka)"></path><path class="edge" d="M842,164 L842,182" marker-end="url(#mka)"></path><path class="edge" d="M932,235 C962,235 962,76 993,76" marker-end="url(#mka)"></path><path class="edge" d="M1086,118 L1086,137" marker-end="url(#mka)"></path><path class="edge" d="M1086,246 L1086,227" marker-end="url(#mka)"></path><path class="edge" d="M1176,182 C1206,182 1206,182 1237,182" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,220 V356 H354 V280" marker-end="url(#mkg)"></path><path class="edge-back" d="M354,277 V378 H110 V216" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="152"></rect><text class="nt t" text-anchor="middle" x="110" y="176">Support agent</text><text class="ns s" text-anchor="middle" x="110" y="194">/docs · PowerShell</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="264" y="87"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="119">UserRequest</text><text class="ns s" text-anchor="middle" x="354" y="138">ticket: 5–500 chars</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="100">CHANGED</text></g><g class="node-changed"><rect height="99" rx="8" width="180" x="264" y="178"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="210">LLMResponse</text><text class="ns s" text-anchor="middle" x="354" y="229">category · priority</text><text class="ns s" text-anchor="middle" x="354" y="244">suggested_reply ≤ 500</text><text class="ns s" text-anchor="middle" x="354" y="259">confidence 0–1</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="191">CHANGED</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="508" y="106"></rect><text class="nt t" text-anchor="middle" x="598" y="138">POST /llm/regular</text><text class="ns s" text-anchor="middle" x="598" y="157">call_llm()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="119">CHANGED</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="508" y="197"></rect><text class="nt t" text-anchor="middle" x="598" y="221">HTTPException 500</text><text class="ns s" text-anchor="middle" x="598" y="240">"LLM request failed"</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="112">classify_ticket()</text><text class="ns s" text-anchor="middle" x="842" y="130">billing · account</text><text class="ns s" text-anchor="middle" x="842" y="146">technical · general</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="92">NEW</text></g><g class="node-changed"><rect height="99" rx="8" width="180" x="752" y="186"></rect><text class="nt t" text-anchor="middle" x="842" y="218">choose_prompt_style()</text><text class="ns s" text-anchor="middle" x="842" y="236">billing → strict</text><text class="ns s" text-anchor="middle" x="842" y="252">account, technical →</text><text class="ns s" text-anchor="middle" x="842" y="266">teacher</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="198">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="34"></rect><text class="nt t" text-anchor="middle" x="1086" y="66">PROMPT_VARIATIONS</text><text class="ns s" text-anchor="middle" x="1086" y="85">ask for suggested_reply,</text><text class="ns s" text-anchor="middle" x="1086" y="100">confidence, priority</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="47">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="172">get_answer()</text><text class="ns s" text-anchor="middle" x="1086" y="191">system + user roles</text><text class="ns s" text-anchor="middle" x="1086" y="206">JSON parse fallback</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="153">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="246"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="278">SYSTEM_PROMPT</text><text class="ns s" text-anchor="middle" x="1086" y="297">commercial airline</text><text class="ns s" text-anchor="middle" x="1086" y="312">assistant</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="259">CHANGED</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="1240" y="144"></rect><text class="nt t" text-anchor="middle" x="1330" y="168">OpenAI Responses API</text><text class="ns s" text-anchor="middle" x="1330" y="187">gpt-4.1-nano</text><text class="ns s" text-anchor="middle" x="1330" y="202">temperature 0 / 0.3 / 0.5</text></g><rect class="elbg" height="15" rx="3" width="46" x="207" y="135"></rect><text class="el" text-anchor="middle" x="230" y="146">ticket</text><rect class="elbg" height="15" rx="3" width="59" x="846" y="162"></rect><text class="el" text-anchor="start" x="848" y="173">category</text><rect class="elbg" height="15" rx="3" width="66" x="809" y="349"></rect><text class="el" text-anchor="middle" x="842" y="360">JSON text</text><rect class="elbg" height="15" rx="3" width="91" x="186" y="371"></rect><text class="el" text-anchor="middle" x="232" y="382">triage result</text><text class="lane" style="fill:var(--ghost)" x="20" y="426">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="246" x="20" y="436"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="143" y="463">Day 3 · embeddings &amp; search</text></g><g class="node-ghost"><rect height="44" rx="8" width="238" x="286" y="436"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="405" y="463">Day 4 · first RAG pipeline</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: A general question answerer

- Input is a `question`, output is an `answer`
- `classify_question()` looks for words like `summarize` and `explain`
- `LLMResponse` fields have types but no limits
- `gpt-4.1-mini` answers anything, as a generic assistant

### After this episode: A ticket triage service

- Input is a `ticket`, output is `category`, `priority`, `suggested_reply`
- `classify_ticket()` sorts tickets into billing, account, technical or general
- `confidence` and `temprature` must be 0–1, the reply at most 500 chars
- An airline `SYSTEM_PROMPT` and the cheaper `gpt-4.1-nano`

> **Why it matters:** this is what an AI feature looks like inside a company: a narrow job, fields another system can store and sort by, and rules you can explain. The pipeline from Day 2 carried over almost unchanged, which proves the structure was right.

## Code walkthrough

Four snippets from `Day2b/App`. The structure is Day 2's; point at what changed.

### llm.py · domain rules

```python
def classify_ticket(ticket: str) -> str:
    t = ticket.lower()

    if any(w in t for w in ["refund", "charged", "invoice", "payment"]):
        return "billing"

    if any(w in t for w in ["login", "password", "account", "access"]):
        return "account"

    if any(w in t for w in ["bug", "error", "crash", "not working"]):
        return "technical"

    return "general"
```

**The first match wins, so the order of the checks is a product decision.** A ticket that mentions both a refund and a login goes to billing. That's fine if billing is the most urgent queue. Say the order out loud so it's a choice, not an accident.

### llm.py · category to style

```python
def choose_prompt_style(category: str) -> str:
    if category=="billing":
        return "strict"
    if category=="technical":
        return "teacher"
    if category=="account":
        return "teacher"
    else:
        return "simple"
```

**Money questions get temperature 0.** Billing goes to the strict template at temperature 0 because a refund policy answer should not vary. Technical and account tickets get step-by-step guidance at 0.5.

### main.py · the bounded contract

```python
class LLMResponse(BaseModel):
    category : str = Field(description="Ticket category")
    priority : str = Field(description="Ticket priority",default="low")
    suggested_reply : str = Field(min_length=5,max_length=500,description= "The model's response")
    source : str = Field(default="LLM")
    temprature : float = Field(ge=0,le=1,default=0.5,description = "The model's temprature" )
    confidence : float = Field(ge=0,le=1,default=0.5,description = "The model's confidence")
```

**Types say what a field is. Bounds say what values are allowed.** If the model returns confidence 7 or a 900-character reply, Pydantic raises before anything reaches the client. Keep `max_length=500` in mind for the break-it.

### main.py · the endpoint

```python
@app.post("/llm/regular",response_model=LLMResponse)
def call_llm(request :UserRequest):
    try: 
        logging.info("Request has been recieved")
        result = get_answer(request = request.ticket)
        return LLMResponse(category = result['category'], ...)
    except Exception as e:
        logging.error("Error had happened {e}")
        raise HTTPException(status_code=500,detail="LLM request failed")
```

**Look closely at the error log: there is no `f` before the string.** The log will print the literal text `{e}`, so the reason for a failure is lost. The 500 is right; the log is useless. That's the second half of the break-it.

## Run it

Run from `Day2b/App` in PowerShell, with the uvicorn logs visible.

**Step 1**

```powershell
python llm.py
```

**Expect:** Three sample tickets. `I have a problem in my account` is classified `account` (teacher, 0.5). The other two are `general` (simple, 0.3). Each prints a dict with `category`, `priority`, `suggested_reply`, `temprature`, `confidence`.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on port 8000. In `/docs`, show that the request field is now `ticket`.

**Step 3**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/llm/regular" -Method Post `
  -ContentType "application/json" `
  -Body '{"ticket":"I was charged twice for my flight and I want a refund"}'
```

**Expect:** `category: billing`, `temprature: 0`, a priority from the model, and a short `suggested_reply`.

**Step 4**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/llm/regular" -Method Post `
  -ContentType "application/json" `
  -Body '{"ticket":"I cannot login, the password reset is not working"}'
```

**Expect:** `category: account`, not technical, even though it says `not working`. The account check runs first.

**Step 5**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/llm/regular" -Method Post `
  -ContentType "application/json" `
  -Body '{"ticket":"hi"}'
```

**Expect:** **422**: `ticket` needs at least 5 characters. No model call.

### Break it on purpose

#### 1 · A good answer that becomes a 500

Send a technical ticket that invites a long answer, for example `The app shows an error and crashes every time I pick a seat, what should I do step by step?`. It routes to the teacher template, which asks for step-by-step guidance but sets no length limit. If `suggested_reply` goes over 500 characters, `LLMResponse(...)` raises a validation error inside the `try`, and the client gets **500 LLM request failed** for a call that worked and was paid for. The JSON-parse fallback has the same risk: it puts the raw model text into `suggested_reply`. Then look at the log: it says `Error had happened {e}`, because the f-prefix is missing.

```text
# main.py: log the real reason
logging.error(f"Error had happened {e}")

# llm.py: tell the model the limit the contract enforces
# (add to each template)
- Keep suggested_reply under 500 characters.
```

#### 2 · A log line with its labels swapped

Read the INFO line from `get_answer()`: `Request has been classified with temp of ... and prompt_style of 0.5`. The f-string puts `selected_prompt` (the whole template text) where the temperature should be, and the temperature where the style should be. Logs you can't trust are worse than no logs.

```text
logging.info(f"category={ticket_category} style={prompt_style} temp={ticket_temprature}")
```

> An output contract only helps if the prompt asks for the same limits. When they disagree, the model does its job and the API still fails. Keep the prompt, the contract and the logs in sync.

## Cheat sheet

- **Ticket triage**: Sorting incoming support requests by type and urgency so the right person handles them first.
- **Domain rules**: Business-specific checks, like refund means billing, written as plain code before the model call.
- **Rule order**: With first-match-wins rules, the order of the `if` checks decides the result when several match.
- **Suggested reply**: A draft answer for a human agent to review, not a message sent straight to the customer.
- **Priority**: How urgent a ticket is (Low, Medium, High), here chosen by the model inside the JSON.
- **Field constraints**: Pydantic limits like `ge`, `le`, `min_length`, `max_length` that reject values outside the allowed range.
- **Model size**: Smaller models like `gpt-4.1-nano` are cheaper and faster, and usually enough for narrow tasks.
- **Prompt/contract mismatch**: When the prompt allows output that the response model rejects, so valid model work turns into an error.
- **f-string**: A Python string starting with `f` where `{name}` is replaced by the value. Without the `f`, the braces print as text.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>A ticket says 'refund failed because the app shows an error'. Which category, and why?</summary><p><code>billing</code>. <code>classify_ticket()</code> checks billing words first, and <code>refund</code> matches before the technical check for <code>error</code> runs.</p></details>
<details><summary>Why does billing use the strict style at temperature 0?</summary><p>Money-related replies should be consistent and careful. The strict template says don't guess, keep it short, and temperature 0 makes the wording repeatable.</p></details>
<details><summary>What happens if the model returns confidence 1.5?</summary><p><code>LLMResponse</code> has <code>le=1</code>, so creating it raises a validation error inside the <code>try</code>. The client gets a 500 instead of a bad number.</p></details>
<details><summary>Why can a successful model call end in HTTP 500 here?</summary><p>The teacher template asks for step-by-step guidance with no length limit, but <code>suggested_reply</code> has <code>max_length=500</code>. A long reply fails validation after the call was paid for.</p></details>
<details><summary>What did you have to change to move from Q&amp;A to ticket triage?</summary><p>Content only: the classifier keywords, the category-to-style map, the templates, the system prompt and the response fields. The pipeline shape from Day 2 stayed.</p></details>
</div>

**Next:** Day 3 – Search by Meaning

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
