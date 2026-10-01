---
title: "Day 1: Your First Endpoint"
description: "From a Python script that talks to a model in the terminal to a real web service that anyone can send a question to. It's the smallest complete AI system: request in, model call, JSON out."
series: "ai-engineering"
order: 1
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "fastapi", "pydantic", "openai"]
readingTime: "7 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day1`](https://github.com/hakmimi/AIEngineering/tree/main/Day1). Layers touched: L2 LLM, L4 System.

## Goals

- **G1. Stand up a FastAPI service with a health check and a first POST endpoint.**  
  You can: run `uvicorn`, open `/docs`, and hit `/health` and `/ask` live.
- **G2. Call an LLM from Python and understand what controls the output.**  
  You can: explain what the model, prompt and temperature each change.
- **G3. Keep API logic and model logic in separate layers.**  
  You can: say why `main.py` never talks to OpenAI directly.
- **G4. Make the system observable and safe against bad input.**  
  You can: show a 422 from Pydantic and read the timing logs of an LLM call.

## System map

Put this on screen right after the hook and come back to it at the end. In later episodes the same map grows: new parts get highlighted, and today's parts turn grey.

> Client → API → Python function → LLM → Response

<div class="ae-map" role="img" aria-label="Client sends JSON to the Pydantic gate, then the /askllm route, then get_answer in llm.py, then the OpenAI Responses API. The answer returns to the client. The route logs to the terminal; bad input returns 422; get_answer reads the key from .env."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 368" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L4 · MAIN.PY</text><text class="lane" x="752" y="18">L2 · LLM.PY</text><text class="lane" x="996" y="18">EXTERNAL</text><path class="edge" d="M200,129 C230,129 230,76 261,76" marker-end="url(#mka)"></path><path class="edge-old" d="M354,118 L354,137" marker-end="url(#mkm)"></path><path class="edge" d="M444,76 C474,76 474,76 505,76" marker-end="url(#mka)"></path><path class="edge-old" d="M598,118 L598,137" marker-end="url(#mkm)"></path><path class="edge" d="M688,76 C718,76 718,178 749,178" marker-end="url(#mka)"></path><path class="edge-old" d="M842,114 L842,133" marker-end="url(#mkm)"></path><path class="edge" d="M932,178 C962,178 962,129 993,129" marker-end="url(#mka)"></path><path class="edge-back" d="M1086,167 V250 H110 V162" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="98"></rect><text class="nt t" text-anchor="middle" x="110" y="122">Client</text><text class="ns s" text-anchor="middle" x="110" y="142">/docs · PowerShell</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="34"></rect><text class="nt t" text-anchor="middle" x="354" y="66">Pydantic gate</text><text class="ns s" text-anchor="middle" x="354" y="85">AdvancedRequest</text><text class="ns s" text-anchor="middle" x="354" y="100">question: 2–500 chars</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="140"></rect><text class="nt t" text-anchor="middle" x="354" y="172">422 error</text><text class="ns s" text-anchor="middle" x="354" y="191">bad input never reaches the</text><text class="ns s" text-anchor="middle" x="354" y="206">LLM</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="34"></rect><text class="nt t" text-anchor="middle" x="598" y="66">POST /askllm</text><text class="ns s" text-anchor="middle" x="598" y="85">also /health, /ask</text><text class="ns s" text-anchor="middle" x="598" y="100">try / except</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="140"></rect><text class="nt t" text-anchor="middle" x="598" y="172">logging → terminal</text><text class="ns s" text-anchor="middle" x="598" y="191">question · duration ·</text><text class="ns s" text-anchor="middle" x="598" y="206">errors</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="153">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="38"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="62">.env</text><text class="ns s" text-anchor="middle" x="842" y="81">OPENAI_API_KEY</text><text class="ns s" text-anchor="middle" x="842" y="96">(git-ignored)</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="136"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="168">get_answer()</text><text class="ns s" text-anchor="middle" x="842" y="187">builds prompt · parses</text><text class="ns s" text-anchor="middle" x="842" y="202">reply</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="149">NEW</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="996" y="91"></rect><text class="nt t" text-anchor="middle" x="1086" y="115">OpenAI Responses API</text><text class="ns s" text-anchor="middle" x="1086" y="134">gpt-4.1-mini · temperature</text><text class="ns s" text-anchor="middle" x="1086" y="149">0</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="86"></rect><text class="el" text-anchor="middle" x="230" y="96">JSON</text><rect class="elbg" height="15" rx="3" width="46" x="939" y="136"></rect><text class="el" text-anchor="middle" x="962" y="148">prompt</text><rect class="elbg" height="15" rx="3" width="104" x="546" y="243"></rect><text class="el" text-anchor="middle" x="598" y="254">{ "answer": … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="298">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="222" x="20" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="131" y="335">Day 2 · prompt templates</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="262" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="392" y="335">Day 3 · embeddings &amp; retrieval</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: A script only you can run

- `test_llm.py` calls the model and prints to your terminal
- No input rules: any string goes straight to the model
- When it fails, you get a stack trace
- Nothing records what happened

### After this episode: A service anyone can call

- HTTP endpoints with auto-generated docs at `/docs`
- Pydantic rejects bad input before it costs a token
- Model errors are caught and the app stays up
- Every call logs the question and its duration

> **Why it matters:** every later episode, from RAG to agents, is a new box added somewhere on this map. If the request/response skeleton is clear, the rest of the series has somewhere to go.

## Code walkthrough

Four snippets from `Day1/app`. Show the highlighted lines on screen and say the point in bold.

### main.py · the skeleton

```python
app = FastAPI()

@app.get("/health")
def get_health_status():
    return {'Status':'ok'}
```

**A route is just a Python function with an address.** The decorator maps an HTTP method and path to the function. Whatever you return becomes JSON. FastAPI builds `/docs` from these decorators, so the docs are never out of date.

### main.py · the contract

```python
class AdvancedRequest(BaseModel):
    question : str  = Field(
        min_length=2,
        max_length=500,
        description= "The users question"
    )
```

**The schema is a gate, not paperwork.** Compare it with `AskRequest`, which accepts any string. With limits in place, an empty or 10,000-character question is rejected with a 422 before you spend a single token.

### llm2.py · the simplest model call

```python
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_answer(question : str) -> str:
    response = client.responses.create(
         model = 'gpt-4.1-mini',
         input = question
    )
    return response.output_text
```

**Show this version first. It's three moving parts: key, model, input.** `llm.py` has already grown past this: it asks for JSON, adds `temperature=0`, and classifies the question. Mention it as a preview of Day 2 rather than explaining it all here.

### main.py · the wiring

```python
@app.post("/askllm")
def ask_llm(request : AdvancedRequest):
    logging.info(f"Received question: {request.question}")
    try:
        start_time = time.time()
        answer = get_answer(request.question)
        durartion = time.time()- start_time
        logging.info(f'... {answer[:80]} ')
        return {'answer' : answer}
    except Exception as e:
        logging.error(f'Error during LLM call {e}')
        return({"error":"Something went wrong!"})
```

**The route doesn't know how the model works, and that's the point.** It validates, times, logs and delegates. Keep the highlighted `answer[:80]` in mind: it's the setup for the break-it segment.

## Run it

**Step 1**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/docs`.

**Step 2**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

**Expect:** `Status: ok`

**Step 3**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"What is AI engineering?"}'
```

**Expect:** Your question echoed back with `"This is static answer!"`. The pipe works with no model involved.

**Step 4**

```powershell
python test_llm.py
```

**Expect:** A real answer in the terminal. Then change the question wording once and run it again.

**Step 5**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/askllm" -Method Post `
  -ContentType "application/json" `
  -Body '{"question":"What is AI engineering?"}'
```

**Expect:** Watch the terminal logs as well as the response. See the break-it box below for what actually happens with the current code.

### Break it on purpose

#### 1 · Bad input: `{"question":"a"}`

Send a one-character question to `/askllm`. Pydantic returns **422** with a readable reason, and the logs show that the model was never called. Point at the 422 box on the map.

#### 2 · The real bug hiding in this repo

`llm.py` now returns a **dict** (`answer`, `confidence`, `type`), but `main.py` still treats the result as a string: `answer[:80]`. Slicing a dict raises an error, the `except` catches it, and the caller gets `{"error":"Something went wrong!"}` **with status 200 OK**. The model call succeeded and you paid for it, but the user sees a failure and a monitoring tool sees success. Show the log line, read the error, and fix it live.

```text
# fix 1: log the text, not the dict
logging.info(f"... {result['answer'][:80]}")

# fix 2: failures should look like failures
from fastapi import HTTPException
...
except Exception as e:
    logging.exception("LLM call failed")
    raise HTTPException(status_code=502, detail="LLM call failed")
```

> The lesson is contracts between layers: when one layer changes its return type, the layer that calls it breaks quietly. That's a natural bridge to structured outputs on Day 2 and response contracts on Day 2b.

## Cheat sheet

- **Endpoint**: An address plus an HTTP method (`POST /askllm`) that runs one function.
- **FastAPI**: A Python web framework that turns type-hinted functions into a documented HTTP API.
- **uvicorn**: The server process that listens on a port and hands requests to FastAPI. `--reload` restarts it when you save a file.
- **Pydantic model**: A class that describes and validates the shape of data. When validation fails, FastAPI returns 422 automatically.
- **422 vs 500 vs 502**: 422: your input was wrong. 500: our code crashed. 502: a service we depend on (the LLM) failed.
- **Prompt**: The full text sent to the model: instructions plus the user's input.
- **Token**: The unit a model reads and bills by, roughly ¾ of a word in English.
- **Temperature**: How much randomness goes into picking the next token. 0 is close to repeatable; higher values vary more.
- **Separation of concerns**: Each file has one job, so you can test, swap or debug it alone. Here, `main.py` handles HTTP and `llm.py` handles the model.
- **.env**: A local file of secrets, loaded by `python-dotenv` and excluded from git by `.gitignore`.
- **Logging level**: `INFO` records normal events and `ERROR` records failures. The format string adds the timestamp.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>What exactly is sent to the model when someone calls /askllm?</summary><p>Only <code>request.question</code>, the validated string, wrapped in the prompt that <code>get_answer()</code> builds. The rest of the HTTP request never reaches the model.</p></details>
<details><summary>Why build the static /ask endpoint before connecting the LLM?</summary><p>It proves the HTTP layer works in isolation. If something breaks later, you know it's in the model layer, and you didn't spend tokens while debugging routing.</p></details>
<details><summary>A user sends an empty question. What happens, and where?</summary><p>Pydantic's <code>min_length=2</code> rejects it inside FastAPI. The client gets a 422, <code>ask_llm()</code> never runs, and no tokens are used.</p></details>
<details><summary>Why is returning {"error": ...} with status 200 a problem?</summary><p>Clients, retries and monitoring all read the status code. A 200 tells them everything worked, so failures stay invisible. Use a 4xx or 5xx status that matches the cause.</p></details>
<details><summary>If you switched from OpenAI to another provider, which files change?</summary><p>Only <code>llm.py</code>. <code>main.py</code> calls <code>get_answer()</code> and doesn't care who answers. That's the payoff of separating the layers.</p></details>
</div>

**Next:** Day 2 – Prompts Under Control

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
