---
title: "Day 2: Prompts Under Control"
description: "From one hard-coded prompt to a small decision pipeline: classify the question, pick a prompt template and a temperature, send a system and a user message, and return a typed response. The model is still the same, but now the system decides how it gets called."
series: "ai-engineering"
order: 2
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "prompt templates", "system role", "temperature"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day2`](https://github.com/hakmimi/AIEngineering/tree/main/Day2). Layers touched: L2 LLM, L3 Orchestration, L4 System.

## Goals

- **G1. Split the prompt into a system message and a user message.**  
  You can: show `SYSTEM_PROMPT` and the `input=[...]` list with both roles, and say what each one controls.
- **G2. Build reusable prompt templates instead of writing a prompt per call.**  
  You can: open `PROMPT_VARIATIONS`, explain the `{{ }}` escaping, and call `build_prompt()` with two styles.
- **G3. Add rule-based decision logic before the model call.**  
  You can: run `python llm.py` and read the log lines: classified type, chosen style, chosen temperature.
- **G4. Return a typed response contract from the API.**  
  You can: call `/llm/regular` and point at every field of `LLMResponse` in the JSON that comes back.

## System map

Same loop as Day 1, with a decision layer inside `get_answer()`. Dashed boxes are Day 1 parts we changed; filled boxes are new today.

> Client → Pydantic → /llm/regular → classify → style + temperature → system + user prompt → LLM → LLMResponse

<div class="ae-map" role="img" aria-label="Client sends a question to the UserRequest model, then POST /llm/regular. get_answer classifies the question with keywords, picks a prompt style and temperature, builds the user prompt from a template and adds the system prompt, then calls the OpenAI Responses API. The result goes back through the LLMResponse contract to the client. Failures return HTTP 500."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 481" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L4 · MAIN.PY</text><text class="lane" x="752" y="18">L3 · LLM.PY DECISIONS</text><text class="lane" x="996" y="18">L2 · LLM.PY PROMPTS</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,174 C230,174 230,114 261,114" marker-end="url(#mka)"></path><path class="edge" d="M444,114 C474,114 474,129 505,129" marker-end="url(#mka)"></path><path class="edge-old" d="M598,164 L598,182" marker-end="url(#mkm)"></path><path class="edge" d="M688,129 C718,129 718,122 749,122" marker-end="url(#mka)"></path><path class="edge" d="M842,171 L842,190" marker-end="url(#mka)"></path><path class="edge" d="M932,235 C962,235 962,68 993,68" marker-end="url(#mka)"></path><path class="edge" d="M1086,103 L1086,122" marker-end="url(#mka)"></path><path class="edge" d="M1086,231 L1086,212" marker-end="url(#mka)"></path><path class="edge" d="M1176,167 C1206,167 1206,174 1237,174" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,212 V341 H354 V280" marker-end="url(#mkg)"></path><path class="edge-back" d="M354,277 V363 H110 V208" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="144"></rect><text class="nt t" text-anchor="middle" x="110" y="168">Client</text><text class="ns s" text-anchor="middle" x="110" y="187">/docs · PowerShell</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="72"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="104">UserRequest</text><text class="ns s" text-anchor="middle" x="354" y="123">question 2–500 chars</text><text class="ns s" text-anchor="middle" x="354" y="138">type (accepted, unused)</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="85">CHANGED</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="264" y="178"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="210">LLMResponse</text><text class="ns s" text-anchor="middle" x="354" y="229">answer · source ·</text><text class="ns s" text-anchor="middle" x="354" y="244">confidence</text><text class="ns s" text-anchor="middle" x="354" y="259">type · temprature</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="191">NEW</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="508" y="94"></rect><text class="nt t" text-anchor="middle" x="598" y="126">POST /llm/regular</text><text class="ns s" text-anchor="middle" x="598" y="146">response_model=LLMResponse</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="108">CHANGED</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="186"></rect><text class="nt t" text-anchor="middle" x="598" y="218">HTTPException 500</text><text class="ns s" text-anchor="middle" x="598" y="236">no more error-with-200</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="198">NEW</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="752" y="72"></rect><text class="nt t" text-anchor="middle" x="842" y="104">classify_question()</text><text class="ns s" text-anchor="middle" x="842" y="123">keywords → summary /</text><text class="ns s" text-anchor="middle" x="842" y="138">explanation /</text><text class="ns s" text-anchor="middle" x="842" y="153">classification</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="85">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="193"></rect><text class="nt t" text-anchor="middle" x="842" y="225">choose_prompt_style()</text><text class="ns s" text-anchor="middle" x="842" y="244">strict · teacher · simple</text><text class="ns s" text-anchor="middle" x="842" y="259">+ TEMPERATURE_BY_STYLE</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="206">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="66">build_prompt()</text><text class="ns s" text-anchor="middle" x="1086" y="85">PROMPT_VARIATIONS template</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="47">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="125"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="157">get_answer()</text><text class="ns s" text-anchor="middle" x="1086" y="176">system + user roles</text><text class="ns s" text-anchor="middle" x="1086" y="191">parses JSON</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="138">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="231"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="263">SYSTEM_PROMPT</text><text class="ns s" text-anchor="middle" x="1086" y="282">rules: JSON only, no</text><text class="ns s" text-anchor="middle" x="1086" y="297">guessing</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="244">NEW</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="1240" y="136"></rect><text class="nt t" text-anchor="middle" x="1330" y="160">OpenAI Responses API</text><text class="ns s" text-anchor="middle" x="1330" y="180">gpt-4.1-mini</text><text class="ns s" text-anchor="middle" x="1330" y="194">temperature 0 / 0.3 / 0.5</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="127"></rect><text class="el" text-anchor="middle" x="230" y="138">JSON</text><rect class="elbg" height="15" rx="3" width="59" x="689" y="108"></rect><text class="el" text-anchor="middle" x="718" y="119">question</text><rect class="elbg" height="15" rx="3" width="40" x="942" y="135"></rect><text class="el" text-anchor="middle" x="962" y="146">style</text><rect class="elbg" height="15" rx="3" width="72" x="1170" y="154"></rect><text class="el" text-anchor="middle" x="1206" y="165">2 messages</text><rect class="elbg" height="15" rx="3" width="66" x="809" y="334"></rect><text class="el" text-anchor="middle" x="842" y="345">JSON text</text><rect class="elbg" height="15" rx="3" width="72" x="196" y="356"></rect><text class="el" text-anchor="middle" x="232" y="367">typed JSON</text><text class="lane" style="fill:var(--ghost)" x="20" y="411">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="421"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="448">Day 2b · support ticket triage</text></g><g class="node-ghost"><rect height="44" rx="8" width="246" x="300" y="421"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="423" y="448">Day 3 · embeddings &amp; search</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: One prompt for everything

- `get_answer()` builds a single f-string prompt for every question
- Temperature is fixed at 0, whatever the question
- No system message: rules and question are mixed in one string
- `main.py` returns a loose dict, and errors come back as 200 OK

### After this episode: The system decides how to ask

- `classify_question()` tags the question before any model call
- Each type maps to a prompt style and a temperature
- `SYSTEM_PROMPT` sets the rules, the template carries the question
- `LLMResponse` defines the output, and failures raise a 500

> **Why it matters:** the model is one component inside the system. Once the code chooses the prompt and the temperature, you can change behaviour without touching the model, and you can explain every answer from the logs.

## Code walkthrough

Four snippets from `Day2/app`. Show the highlighted lines and land the bold sentence.

### llm.py · the two roles

```python
response = client.responses.create(
    model = 'gpt-4.1-mini',
    temperature=model_temprature,
    input = [
        {"role":"system",
         "content":SYSTEM_PROMPT},
        {"role" : "user",
         "content" : user_prompt}
    ]
)
```

**The rules and the question travel in separate messages.** Day 1 sent one string. Now `SYSTEM_PROMPT` holds the rules for every call, and the user message holds the filled template. Temperature is no longer a constant; it comes from the chosen style.

### llm.py · a template

```python
    "strict": """
Answer the question in a concise and reliable way.

Rules:
- Do not guess.
- If unsure, say "I am not sure".
- Keep the answer under 5 sentences.

Return ONLY valid JSON:
{{

  "answer": "...",
  "confidence": 0.0
}}


Question:
{question}
""",
```

**Double braces are literal JSON, single braces are the slot.** `build_prompt()` calls `template.format(question=question)`. Without the doubled braces, `format()` would try to fill the JSON example and crash with a KeyError.

### llm.py · rules before the model

```python
def classify_question(question: str) -> str:
    q = question.lower()

    summary_keywords = ["summarize", "summary", "short version", "brief"]
    explanation_keywords = ["explain", "why", "how", "what is", "what are"]
    ...
    if any(keyword in q for keyword in explanation_keywords):
        return "explanation"
...
TEMPERATURE_BY_STYLE = {
    "strict": 0,
    "simple": 0.3,
    "teacher": 0.5
}
```

**Cheap rules pick the prompt before a single token is spent.** Summary goes to strict at temperature 0, explanation goes to teacher at 0.5, everything else to simple. Keep the highlighted `in q` check in mind: it matches substrings, which is the first break-it.

### main.py · the response contract

```python
class LLMResponse(BaseModel):
    answer : str
    source : str
    confidence : float
    type : str
    temprature : float
...
@app.post("/llm/regular",response_model=LLMResponse)
def ask_llm(response :UserRequest):
    try:
        ...
        logging.info(f"return result {result["answer"]} ")
        return LLMResponse(answer=result["answer"], ...)
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="LLM request failed")
```

**Day 1's error-with-200 is gone: failures now look like failures.** `response_model` documents the output in `/docs` and validates it. The highlighted log line uses double quotes inside a double-quoted f-string, which only parses on Python 3.12+.

## Run it

Run from `Day2/app` in PowerShell. Keep the uvicorn terminal visible next to the request terminal so viewers see the decision logs.

**Step 1**

```powershell
python llm.py
```

**Expect:** Three questions. For each: `Question classified as ...`, `Using prompt style of ...`, `Model temprature which will be use is ...`, then a dict with `answer`, `confidence`, `type`, `temprature`.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`. Open `/docs` and show both schemas under POST `/llm/regular`.

**Step 3**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/llm/regular" -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"Summarize what FastAPI is"}'
```

**Expect:** `type: summary`, `temprature: 0`, `source: llm`. The server log shows style `strict`.

**Step 4**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/llm/regular" -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"Explain APIs"}'
```

**Expect:** `type: explanation`, `temprature: 0.5`, a longer step-by-step answer from the teacher template.

**Step 5**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/llm/regular" -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"What is Python?","type":"summary"}'
```

**Expect:** `type: explanation`. The `type` you sent is accepted by `UserRequest` and then ignored, and `what is` matches the explanation keywords.

### Break it on purpose

#### 1 · `Show me Python lists` becomes an explanation

Send `{"question":"Show me Python lists"}`. The log says `Question classified as explanation` and the temperature is 0.5. Why: `"how" in q` is a substring check, and `show` contains `how`. Keyword rules need word boundaries.

```python
import re

def has_keyword(q: str, keywords: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(k)}\b", q) for k in keywords)

if has_keyword(q, explanation_keywords):
    return "explanation"
```

#### 2 · It works on my machine, not on a fresh one

`Day2/requirements.txt` lists `python-dotenv`, `openai`, `uvicorn` and `pydantic`, but not `fastapi`. In a new venv, `pip install -r ..\requirements.txt` then `uvicorn main:app` fails with **ModuleNotFoundError: No module named 'fastapi'**. On Python 3.11 or older you hit a second failure first: **SyntaxError: f-string: unmatched '['** on line 31, because of the nested double quotes.

```text
# requirements.txt
fastapi

# main.py line 31: use the other quote type inside the f-string
logging.info(f"return result {result['answer']} ")
```

> Every rule you add in front of the model is code you have to test. The keyword classifier is useful and cheap, and it still needs the same care as any other function. Next episode applies the same pattern to a real support-ticket flow.

## Cheat sheet

- **System prompt**: The message with role `system` that sets rules for every answer, such as JSON only and no guessing.
- **User prompt**: The message with role `user` that carries the actual request, here the filled template.
- **Prompt template**: A fixed prompt with a slot like `{question}` that code fills in, so wording stays stable across calls.
- **Brace escaping**: In a `str.format` template, `{{` and `}}` produce literal braces; single braces are slots.
- **Temperature**: Controls randomness when picking tokens. 0 gives repeatable answers; 0.5 allows more variety.
- **Rule-based classifier**: Plain `if` logic on keywords that labels input before any model call. Free and fast, but brittle.
- **Prompt style**: A named combination of template and temperature (`strict`, `teacher`, `simple`) chosen per question type.
- **response_model**: The FastAPI argument that validates and documents what an endpoint returns.
- **Output contract**: The agreed shape of a response (`LLMResponse`), so clients can rely on fields and types.
- **JSON parse fallback**: If `json.loads` fails, `get_answer()` returns the raw text with confidence 0.5 instead of crashing.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>What goes in the system message and what goes in the user message?</summary><p>The system message holds the rules that apply to every call (<code>SYSTEM_PROMPT</code>). The user message holds the filled template with this specific question.</p></details>
<details><summary>Why does the template write {{ and }} around the JSON example?</summary><p><code>build_prompt()</code> calls <code>template.format(question=...)</code>. Doubled braces become literal braces; single braces would be treated as slots and raise a KeyError.</p></details>
<details><summary>Which temperature does 'Summarize what FastAPI is' get, and why?</summary><p>0. <code>classify_question()</code> finds <code>summarize</code>, <code>choose_prompt_style()</code> maps summary to <code>strict</code>, and <code>TEMPERATURE_BY_STYLE['strict']</code> is 0.</p></details>
<details><summary>A client sends type: 'summary'. Does it change anything?</summary><p>No. <code>UserRequest</code> accepts the field, but <code>ask_llm()</code> only passes <code>question</code> to <code>get_answer()</code>, which classifies on its own.</p></details>
<details><summary>Why is raising HTTPException(500) better than Day 1's error dict?</summary><p>The status code now tells clients, retries and monitoring that the call failed. Day 1 returned an error message with 200 OK, which looked like success.</p></details>
</div>

**Next:** Day 2b – Support Ticket Triage

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
