---
title: "Day 11: Give It Tools"
description: "From an assistant that can only read documents and write text, to one that can choose a tool, run it and answer from the result. The model decides which tool; plain Python code does the running."
series: "ai-engineering"
order: 13
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "tool registry", "function calling", "safe eval"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day11`](https://github.com/hakmimi/AIEngineering/tree/main/Day11). Layers touched: L2 LLM, L3 Orchestration.

## Goals

- **G1. Define tools as name + description + validated input + Python function.**  
  You can: open `TOOLS` in `tools.py` and explain the three tools and their input models.
- **G2. Separate reasoning (choosing a tool) from execution (running it).**  
  You can: show a request where `decided_by` is `rule` and one where it is `llm`, and say who did what.
- **G3. Make tool calls safe and observable.**  
  You can: show a `tool_error` for `10/0` and read the `tool_decision` and `tool_call` log lines.
- **G4. Know where a tool layer can still break.**  
  You can: crash the calculator on camera with a crafted expression and explain the missing guard.

## System map

A third entry point joins `/rag` and `/rag/multistep`. It adds a decision layer in front of three tools; knowledge questions still flow into the Day 9 RAG path.

> Query → Router → Decision (rules \| LLM) → Tool → Tool result → LLM phrases answer (search_docs / none → normal RAG)

<div class="ae-map" role="img" aria-label="The client calls POST /ask/tools. The rule router still answers greetings. The decision layer tries rule_decision for pure arithmetic, else llm_decision asks the LLM with a strict schema to pick search_docs, calculate, list_topics or none. search_docs and none go to the existing RAG path. calculate and list_topics run through execute_tool, which validates arguments with Pydantic and returns a ToolResult. A second LLM call phrases the answer from the tool result only. The response, including a tool object, returns to the client."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 542" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · ROUTES.PY</text><text class="lane" x="508" y="18">L3 · TOOL_AGENT.PY</text><text class="lane" x="752" y="18">L3 · TOOLS.PY</text><text class="lane" x="996" y="18">L2 · PROMPTS + LLM</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,216 C230,216 230,167 261,167" marker-end="url(#mka)"></path><path class="edge-old" d="M354,202 L354,220" marker-end="url(#mkm)"></path><path class="edge" d="M444,167 C474,167 474,163 505,163" marker-end="url(#mka)"></path><path class="edge" d="M598,205 L598,224" marker-end="url(#mka)"></path><path class="edge" d="M688,163 C718,163 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M688,269 C718,269 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M688,269 C718,269 718,360 749,360" marker-end="url(#mka)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge" d="M932,76 C962,76 962,269 993,269" marker-end="url(#mka)"></path><path class="edge" d="M1086,205 L1086,224" marker-end="url(#mka)"></path><path class="edge" d="M1176,269 C1206,269 1206,216 1237,216" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,246 V424 H110 V250" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="186"></rect><text class="nt t" text-anchor="middle" x="110" y="210">Client</text><text class="ns s" text-anchor="middle" x="110" y="228">PowerShell · /docs</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="132"></rect><text class="nt t" text-anchor="middle" x="354" y="164">POST /ask/tools</text><text class="ns s" text-anchor="middle" x="354" y="184">run_with_tools()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="146">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="224"></rect><text class="nt t" text-anchor="middle" x="354" y="248">Rule router</text><text class="ns s" text-anchor="middle" x="354" y="266">smalltalk → no API call</text><text class="ns s" text-anchor="middle" x="354" y="282">(Day 6)</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="121"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="153">rule_decision()</text><text class="ns s" text-anchor="middle" x="598" y="172">pure arithmetic</text><text class="ns s" text-anchor="middle" x="598" y="187">→ calculate, no LLM</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="134">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="227"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="259">llm_decision()</text><text class="ns s" text-anchor="middle" x="598" y="278">strict schema · tool enum</text><text class="ns s" text-anchor="middle" x="598" y="293">failure → search_docs</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="240">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="66">execute_tool()</text><text class="ns s" text-anchor="middle" x="842" y="85">validate · run · log</text><text class="ns s" text-anchor="middle" x="842" y="100">returns ToolResult</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="172">calculate</text><text class="ns s" text-anchor="middle" x="842" y="191">AST safe_eval</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="231"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="263">list_topics</text><text class="ns s" text-anchor="middle" x="842" y="282">categories.json</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="244">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="322"></rect><text class="nt t" text-anchor="middle" x="842" y="346">search_docs / none</text><text class="ns s" text-anchor="middle" x="842" y="365">→ get_rag_answer</text><text class="ns s" text-anchor="middle" x="842" y="380">(Day 9 path)</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="121"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="153">prompts.py</text><text class="ns s" text-anchor="middle" x="1086" y="172">TOOL_CHOICE_PROMPT</text><text class="ns s" text-anchor="middle" x="1086" y="187">TOOL_ANSWER_PROMPT</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="134">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="227"></rect><text class="nt t" text-anchor="middle" x="1086" y="259">phrase the answer</text><text class="ns s" text-anchor="middle" x="1086" y="278">get_answer() from the</text><text class="ns s" text-anchor="middle" x="1086" y="293">tool result only</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="240">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="186"></rect><text class="nt t" text-anchor="middle" x="1330" y="210">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="228">decision + phrasing</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="174"></rect><text class="el" text-anchor="middle" x="230" y="186">POST</text><rect class="elbg" height="15" rx="3" width="59" x="602" y="204"></rect><text class="el" text-anchor="start" x="604" y="214">no match</text><rect class="elbg" height="15" rx="3" width="72" x="926" y="156"></rect><text class="el" text-anchor="middle" x="962" y="166">ToolResult</text><rect class="elbg" height="15" rx="3" width="91" x="674" y="417"></rect><text class="el" text-anchor="middle" x="720" y="428">answer + tool</text><text class="lane" style="fill:var(--ghost)" x="20" y="472">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="214" x="20" y="482"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="127" y="509">Day 12 · memory / state</text></g><g class="node-ghost"><rect height="44" rx="8" width="182" x="254" y="482"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="345" y="509">Day 13 · evaluation</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Documents in, text out

- Every question went to retrieval, even `12*(3+4)`
- The model would have to do arithmetic itself, and could get it wrong
- "What topics do you have?" had no good answer: it's not in any chunk
- The system could talk about data but couldn't act on it

### After this episode: Choose, run, answer

- `POST /ask/tools` with three tools: `search_docs`, `calculate`, `list_topics`
- `rule_decision` catches pure arithmetic with zero decision calls; `llm_decision` picks the rest from a strict enum
- `execute_tool` validates inputs with Pydantic, returns `ToolResult(ok, output, error)` and logs every call
- The response carries a `tool` object: name, arguments, output, `decided_by`

> **Why it matters:** tool use is what turns a chatbot into an agent. The key design choice is who does what: the LLM picks a tool and fills its arguments, and deterministic code executes it. That split is what makes tool calls testable, and it's the same shape every agent framework uses.

## Code walkthrough

Four snippets from `Day11`. Two show the contract and the executor, two show the decision layer.

### tools.py · a tool is a contract

```python
class CalculateInput(BaseModel):
    expression: str = Field(..., min_length=1, max_length=100)
...
@dataclass
class ToolResult:
    ok: bool
    output: object = None
    error: str | None = None


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable[[BaseModel], object]
```

**Every tool has a typed input and a uniform result.** The input model rejects bad arguments before the function runs. `ToolResult` means callers never have to guess whether a tool raised or returned.

### tools.py · the executor

```python
def execute_tool(name: str, arguments: dict) -> ToolResult:
    """Validate arguments, run the tool, log the call. Never raises."""
    started = time.perf_counter()
    tool = TOOLS.get(name)
    try:
        if tool is None:
            raise KeyError(f"unknown tool '{name}'")
        result = ToolResult(True, tool.fn(tool.input_model(**arguments)))
    except ValidationError as exc:
        result = ToolResult(False, error=f"invalid arguments: {exc.errors()[0]['msg']}")
    except (KeyError, ValueError) as exc:
        result = ToolResult(False, error=str(exc).strip("'\""))
```

**Validate, run, wrap, log: the same four steps for every tool.** The docstring promises it never raises. It only catches `KeyError` and `ValueError`, so any other exception type from a tool escapes. Remember that for the break-it.

### tools.py · a calculator without eval

```python
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
                raise ValueError("exponent too large")
            return _BIN_OPS[type(node.op)](left, right)
...
    cleaned = expression.replace("^", "**").replace("×", "*").replace("÷", "/").replace(",", "")
    try:
        result = ev(ast.parse(cleaned.strip(), mode="eval"))
    except ZeroDivisionError as exc:
        raise ValueError("division by zero") from exc
    ...
    return round(float(result), 10)
```

**Parse the expression and allow only numbers and operators.** No names, calls or attributes, so `__import__('os')` is rejected. The exponent guard looks only at the right side of each power, and `float()` assumes a real result. Both assumptions fail in the demo.

### tool_agent.py · who decides

```python
TOOL_CHOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": [*TOOLS, "none"]},
        ...
def llm_decision(question: str) -> ToolDecision:
    try:
        choice = get_structured(render_tool_choice_prompt(question), TOOL_CHOICE_SCHEMA, "tool_choice")
    except ExternalServiceError:
        logger.warning("tool_choice_failed - defaulting to search_docs")
        return ToolDecision("search_docs", {"query": question}, "fallback")
...
def decide(question: str) -> ToolDecision:
    return rule_decision(question) or llm_decision(question)
```

**The model can only choose from a list you control.** The enum is built from the registry, so adding a tool updates the schema. Rules run first because they're free, and if the LLM call fails the safe default is a plain document search.

## Run it

Run from `Day11` in PowerShell. Keep the server log visible: `tool_decision ... by=rule|llm` is the line that tells the story.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `95 passed`, including 36 new tests in `test_tools.py`.

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on port 8000; `/docs` shows `POST /ask/tools`.

**Step 3**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask/tools" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"12*(3+4)"}').results.tool
```

**Expect:** `name: calculate`, `decided_by: rule`, `output: 84`. The log shows no `tool_choice` LLM call.

**Step 4**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask/tools" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"What is 15% of 240?"}').results
```

**Expect:** `source: tool`, an answer with 36, and `tool.decided_by: llm` with an expression like `0.15*240`.

**Step 5**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask/tools" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"List the nature topics"}').results.tool
```

**Expect:** `name: list_topics`, `arguments.category: nature`, and a sorted list of topics.

**Step 6**

```text
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask/tools" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"What is 10/0?"}').results
```

**Expect:** `source: tool_error`, `tool.error: division by zero`, and a polite answer saying it couldn't compute it. Status 200, nothing crashed.

### Break it on purpose

#### 1 · A result that isn't a real number

Send `{"query":"(0-8)^0.5"}`. The rule picks `calculate` with no LLM call. Python computes `(-8)0.5` as a complex**number, `float(result)` raises `TypeError`, and `execute_tool` only catches `KeyError` and `ValueError`. The client gets**500\*\* `Internal server error` from the global handler. `(10^100)^100` does the same with `OverflowError`: the big int can't become a float. The "never raises" promise is broken by the tool itself.

```text
# tools.py, end of safe_eval
try:
    result = ev(ast.parse(cleaned.strip(), mode="eval"))
except (ZeroDivisionError, OverflowError) as exc:
    raise ValueError("result out of range") from exc
...
if isinstance(result, complex):
    raise ValueError("result is not a real number")

# and in execute_tool, a last line of defence
except Exception as exc:
    logger.exception("tool_crashed name=%s", name)
    result = ToolResult(False, error="tool failed")
```

#### 2 · A 27-character denial of service (don't run it live)

The exponent guard checks only the **right** side of each `**`. So `(((9^99)^99)^99)^99` passes every check: each exponent is 99. Python builds an integer with hundreds of millions of bits and the request runs for minutes, holding the CPU. The rule layer routes it straight to the calculator, so it costs the attacker nothing. Explain it on screen with the code, or run the three-level version `((9^99)^99)^99` and point at `X-Process-Time-Ms`: a quarter of a second for one short string. Each extra level multiplies the work about a hundred times. The fix is to do power math in floats so it overflows fast, or to cap the size of the base as well.

```text
if isinstance(node.op, ast.Pow):
    if abs(right) > _MAX_EXPONENT:
        raise ValueError("exponent too large")
    left = float(left)  # float ** overflows in microseconds instead of building a huge int
```

> A tool is code that runs on input you don't control, even when a model sits in between. Treat every tool like a public endpoint: validate the input, bound the work, and catch everything at the boundary.

## Cheat sheet

- **Tool**: A function the assistant can call, described by a name, a one-line description, an input model and the Python function.
- **Function calling**: Letting the model choose a function and fill its arguments as structured output, while your code runs it.
- **Tool registry**: The `TOOLS` dict. The decision schema's enum is built from it, so the model can only pick registered tools.
- **Reasoning vs execution**: The LLM decides what to do; deterministic code does it. The model never runs anything itself.
- **Rule-first decision**: Cheap regex rules decide obvious cases before any LLM call. `12*(3+4)` never reaches the model.
- **ToolResult**: `ok`, `output`, `error`: one shape for every tool outcome, so callers don't handle exceptions.
- **AST**: Abstract syntax tree. `ast.parse` turns the expression into nodes, and `safe_eval` allows only numbers and arithmetic nodes.
- **Safe default**: What happens when the decision fails. Here: `search_docs`, the least surprising action.
- **Tool error**: A failed tool call returned as data (`source: tool_error`) and explained to the user. The server stays up.
- **Resource exhaustion**: An input that makes the server do huge amounts of work, like nested powers. Guards must bound the amount of work as well as the syntax.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>For "12*(3+4)", how many LLM calls are made, and by what?</summary><p>One. <code>rule_decision</code> picks <code>calculate</code> with no model call, Python computes 84, and <code>get_answer</code> phrases the answer. If the phrasing call fails, the raw result is returned instead.</p></details>
<details><summary>Why does the choice schema use an enum for the tool field?</summary><p>With <code>strict</code> structured output the model can only return a registered tool name or <code>none</code>. It can't invent a tool, and the enum stays in sync because it's built from <code>TOOLS</code>.</p></details>
<details><summary>What does the user see for "What is 10/0?", and why isn't it a 500?</summary><p><code>safe_eval</code> turns <code>ZeroDivisionError</code> into <code>ValueError</code>, <code>execute_tool</code> returns <code>ToolResult(ok=False, error="division by zero")</code>, and the answer prompt explains it couldn't compute it. Source is <code>tool_error</code> with status 200.</p></details>
<details><summary>Why does "(0-8)^0.5" return a 500?</summary><p>The result is a complex number, so <code>float(result)</code> raises <code>TypeError</code>. <code>execute_tool</code> only catches <code>KeyError</code> and <code>ValueError</code>, so the exception reaches the global handler.</p></details>
<details><summary>A knowledge question goes through /ask/tools. What's missing from its timings?</summary><p>The decision step. For <code>search_docs</code> or <code>none</code>, <code>run_with_tools</code> returns <code>get_rag_answer</code>'s result, which has its own timer, so the LLM tool-choice call isn't counted in <code>total_ms</code>.</p></details>
</div>

**Next:** Day 12 – Conversations With Memory

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
