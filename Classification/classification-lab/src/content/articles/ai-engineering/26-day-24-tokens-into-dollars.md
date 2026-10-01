---
title: "Day 24: Tokens Into Dollars"
description: "From \"it's probably cheap\" to a cost figure on every response, built from the provider's own token counts. Then we measure four cost settings on the 22-case eval and find the biggest saving wasn't where we expected."
series: "ai-engineering"
order: 26
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "token usage", "cost per request", "context cap"]
readingTime: "9 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day24`](https://github.com/hakmimi/AIEngineering/tree/main/Day24). Layers touched: L2 LLM, L4 System.

## Goals

- **G1. Read token usage from the provider's response instead of guessing.**  
  You can: point at `usage.input_tokens` / `output_tokens` in `llm.py` and `prompt_tokens` in `embeddings.py`.
- **G2. Turn tokens into an estimated cost per request, across every call it makes.**  
  You can: show the `usage` block on a `/rag/graph` response and explain why a follow-up question costs two LLM calls.
- **G3. Cap context size without cutting chunks in half.**  
  You can: walk `build_context` and say what `MAX_CONTEXT_TOKENS=400` keeps and drops.
- **G4. Measure what each optimisation does to cost and quality together.**  
  You can: read the A–D table from `cost_report` and say why the schema removal beat the context cap.

## System map

The request path is unchanged. Two things are new: every model call now reports its tokens to a per-request tracker, and the context is capped before it goes into the prompt.

> Query → Retrieval → Prompt assembly (token-capped) → LLM → usage recorded → cost logged + returned → Response

<div class="ae-map" role="img" aria-label="A client or the cost_report script calls run_graph, which starts a UsageTracker in a ContextVar. Retrieval calls embeddings.py and the RAG path builds a token-capped context in rag.py using settings from config.py, then llm.py calls OpenAI without repeating the JSON schema in the prompt. Both llm.py and embeddings.py read the usage field of each response and call record_usage, which logs it and adds it to the tracker. estimate_cost uses the PRICES table. The answer returns with a usage block of calls, tokens and estimated cost."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 368" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CALLERS</text><text class="lane" x="264" y="18">L3 · GRAPH.PY</text><text class="lane" x="508" y="18">L1 · CONTEXT</text><text class="lane" x="752" y="18">L2 · MODEL CALLS</text><text class="lane" x="996" y="18">EXTERNAL</text><text class="lane" x="1240" y="18">L4 · USAGE.PY</text><path class="edge" d="M200,84 C230,84 230,129 261,129" marker-end="url(#mka)"></path><path class="edge" d="M200,170 C230,170 230,129 261,129" marker-end="url(#mka)"></path><path class="edge" d="M444,129 C474,129 474,182 505,182" marker-end="url(#mka)"></path><path class="edge-old" d="M598,118 L598,137" marker-end="url(#mkm)"></path><path class="edge" d="M688,182 C718,182 718,174 749,174" marker-end="url(#mka)"></path><path class="edge" d="M444,129 C596,129 596,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M932,174 C962,174 962,129 993,129" marker-end="url(#mka)"></path><path class="edge" d="M932,76 C962,76 962,129 993,129" marker-end="url(#mka)"></path><path class="edge" d="M1176,129 C1206,129 1206,76 1237,76" marker-end="url(#mka)"></path><path class="edge" d="M1330,118 L1330,137" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,118 V250 H110 V117" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="53"></rect><text class="nt t" text-anchor="middle" x="110" y="77">Client</text><text class="ns s" text-anchor="middle" x="110" y="96">POST /rag/graph</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="20" y="136"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="168">cost_report.py</text><text class="ns s" text-anchor="middle" x="110" y="187">4 configs × 22 cases</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="149">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="264" y="87"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="119">run_graph()</text><text class="ns s" text-anchor="middle" x="354" y="138">start_tracking()</text><text class="ns s" text-anchor="middle" x="354" y="153">usage in response + log</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="100">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="66">config.py</text><text class="ns s" text-anchor="middle" x="598" y="85">MAX_CONTEXT_TOKENS=400</text><text class="ns s" text-anchor="middle" x="598" y="100">JSON_SCHEMA_IN_PROMPT=0</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="47">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="172">build_context()</text><text class="ns s" text-anchor="middle" x="598" y="191">whole chunks, best first</text><text class="ns s" text-anchor="middle" x="598" y="206">at least one</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="153">CHANGED</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="752" y="42"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="74">embeddings.py</text><text class="ns s" text-anchor="middle" x="842" y="92">usage.prompt_tokens</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="54">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="132"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="164">llm.py</text><text class="ns s" text-anchor="middle" x="842" y="184">usage.input/output_tokens</text><text class="ns s" text-anchor="middle" x="842" y="198">no schema in prompt</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="146">CHANGED</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="996" y="98"></rect><text class="nt t" text-anchor="middle" x="1086" y="122">OpenAI</text><text class="ns s" text-anchor="middle" x="1086" y="142">returns usage per call</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="66">UsageTracker</text><text class="ns s" text-anchor="middle" x="1330" y="85">ContextVar, one per request</text><text class="ns s" text-anchor="middle" x="1330" y="100">sums every call</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="172">PRICES table</text><text class="ns s" text-anchor="middle" x="1330" y="191">estimate_cost()</text><text class="ns s" text-anchor="middle" x="1330" y="206">PRICING_JSON override</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="153">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="89"></rect><text class="el" text-anchor="middle" x="230" y="100">JSON</text><rect class="elbg" height="15" rx="3" width="66" x="198" y="133"></rect><text class="el" text-anchor="middle" x="230" y="144">run_graph</text><rect class="elbg" height="15" rx="3" width="46" x="695" y="161"></rect><text class="el" text-anchor="middle" x="718" y="172">prompt</text><rect class="elbg" height="15" rx="3" width="66" x="564" y="86"></rect><text class="el" text-anchor="middle" x="596" y="96">retrieval</text><rect class="elbg" height="15" rx="3" width="85" x="1164" y="86"></rect><text class="el" text-anchor="middle" x="1206" y="96">record_usage</text><rect class="elbg" height="15" rx="3" width="174" x="633" y="243"></rect><text class="el" text-anchor="middle" x="720" y="254">answer + usage {tokens, $}</text><text class="lane" style="fill:var(--ghost)" x="20" y="298">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="182" x="20" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="111" y="335">Day 25 · guardrails</text></g><g class="node-ghost"><rect height="44" rx="8" width="246" x="222" y="308"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="345" y="335">Day 26 · offline test suite</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Cost was a guess

- No token counts anywhere: not in logs, not in responses
- `llm.py` pasted the full JSON schema into every prompt via `with_json_schema()`
- Context was capped by characters only (`MAX_CONTEXT_CHARS=6000`)
- No way to compare two settings on cost and accuracy at the same time

### After this episode: Every response carries its bill

- `llm_usage` / `embedding_usage` events from the provider's own `usage` field
- A `usage` block on every `/rag/graph` response: calls, tokens, `estimated_cost_usd`
- `MAX_CONTEXT_TOKENS=400` keeps whole chunks, best first; the schema is no longer repeated in prompts
- `scripts/cost_report.py`: 4 configs, −16 % cost at unchanged accuracy

> **Why it matters:** cost is a product metric like latency and accuracy. You can't set a budget, price a feature or spot a runaway loop if you don't know what one request costs, and every optimisation needs its quality check next to it.

## Code walkthrough

Five snippets from `Day24`: the price table, reading usage, the per-request tracker, wiring it into the graph, and the context cap.

### usage.py · price table and cost

```python
PRICES: dict[str, dict[str, float]] = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    **json.loads(os.getenv("PRICING_JSON", "{}")),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    """USD. Unknown model -> 0.0 (and a warning) rather than a crash: cost tracking must never break a request."""
    price = PRICES.get(model)
    if price is None:
        logger.warning("no_price_for_model model=%s", model)
        return 0.0
    return (input_tokens * price["input"] + output_tokens * price["output"]) / 1_000_000
```

**Prices are per million tokens, and they live in data, not in code.** The table is an estimate you can override with `PRICING_JSON`. Keep the highlighted `return 0.0` in mind: it's the break-it segment.

### llm.py · read what the provider billed

```python
        response = client.responses.create(
            model=settings.llm_model,
            input=with_json_schema(prompt, schema) if settings.json_schema_in_prompt else prompt,
            temperature=0,
            text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
        )
    ...
    usage = getattr(response, "usage", None)
    if usage is not None:                      # cost tracking must never break a request
        record_usage("llm", name, settings.llm_model, usage.input_tokens, usage.output_tokens)
    return response.output_text
```

**The schema is already enforced by `text.format`. Pasting it into the prompt too was paying twice.** `strict: True` makes the API follow the schema, so repeating it in the prompt added about 78 input tokens per call for nothing. The flag keeps the old behaviour available for the comparison.

### usage.py · one tracker per request

```python
_tracker: contextvars.ContextVar[UsageTracker | None] = contextvars.ContextVar("usage_tracker", default=None)
...
def record_usage(kind: str, step: str, model: str, input_tokens: int, output_tokens: int = 0) -> None:
    """Log the call (always) and add it to the current request's tracker (if any)."""
    cost = estimate_cost(model, input_tokens, output_tokens)
    log_event(logger, "llm_usage" if kind == "llm" else "embedding_usage", step=step, model=model,
              input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=round(cost, 8))
    tracker = _tracker.get()
    if tracker is not None:
        tracker.add(kind, step, model, input_tokens, output_tokens)
```

**Every call is logged; only calls inside a tracked request are summed.** It's the Day 23 request-id pattern again. A rewrite, a tool choice, an answer and an embedding all land in the same tracker, so multi-call paths show their real total.

### graph.py · wire the tracker into a request

```python
    tracker, token = start_tracking()           # sums the tokens/cost of every LLM + embedding call in this request
    try:
        final = rag_graph.invoke({"question": question, "top_k": top_k, "session_id": session_id, "trace": [], "timings": {}})
    finally:
        stop_tracking(token)
    usage = tracker.summary()
```

**Start before the graph, stop in `finally`, even when a node fails.** `stop_tracking` resets the ContextVar with its token, so the next request never inherits this one's calls. The same `usage` dict goes into `graph_done` and the response.

### rag.py · cap context in tokens, whole chunks only

```python
    budget = settings.max_context_tokens
    if budget:                                  # keep whole chunks, best first; never cut one in half
        kept, used = [], 0
        for line in lines:
            tokens = estimate_tokens(line)
            if kept and used + tokens > budget:
                break
            kept.append(line)
            used += tokens
        lines = kept
    return "\n".join(lines)[:settings.max_context_chars]
```

**The `kept and` means the best chunk always survives.** `estimate_tokens` is chars divided by 4, fine for a budget and never used for billing. On this data the cap barely changed cost, so 400 stays as a worst-case guardrail.

## Run it

Run from `Day24` in PowerShell. Pipe responses through `ConvertTo-Json -Depth 6` so the `usage` block is readable.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `256 passed` (14 new tests in `test_usage_cost.py`).

**Step 2**

```powershell
uvicorn main:app --reload
```

**Expect:** Server running. Keep the log window visible to see `llm_usage` and `embedding_usage` events.

**Step 3**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Where is Masada?"}' | ConvertTo-Json -Depth 6
```

**Expect:** `usage`: `llm_calls: 1`, `embedding_calls: 1`, a few hundred input tokens and an `estimated_cost_usd` around $0.0001.

**Step 4**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" -Body '{"query":"hello"}' | ConvertTo-Json -Depth 6
```

**Expect:** `llm_calls: 0`, `embedding_calls: 0`, `estimated_cost_usd: 0.0`. Greetings are free.

**Step 5**

```text
$b1 = '{"query":"Tell me about Masada","session_id":"cost"}'
$b2 = '{"query":"How do visitors reach it?","session_id":"cost"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post -ContentType "application/json" -Body $b1 | Out-Null
(Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post -ContentType "application/json" -Body $b2).results.usage
```

**Expect:** The follow-up shows `llm_calls: 2`: the rewrite plus the answer. Memory has a price, and now it shows.

**Step 6**

```powershell
python -m scripts.cost_report
```

**Expect:** Four lines, `A_baseline` to `D_cap_250`, with accuracy, tokens, cost and failures, then `cost vs baseline`. The README run showed −15.5 %, −16.2 % and −19.0 % with accuracy 1.000 throughout.

### Break it on purpose

#### 1 · A model with no price

Set `$env:LLM_MODEL="gpt-4.1"` and restart. Requests still work, but the log shows `no_price_for_model model=gpt-4.1` and the LLM part of `estimated_cost_usd` is 0. The tracker now says a more expensive model is cheaper. It's deliberate (tracking must never break a request), which is why the warning matters. Add the model's price from the provider's current list, restart, and the cost comes back.

```text
# PowerShell: add a price for the new model (values from your provider's price list)
$env:PRICING_JSON = '{"gpt-4.1": {"input": <input price>, "output": <output price>}}'
```

#### 2 · Squeeze the context too hard

Set `$env:MAX_CONTEXT_TOKENS="50"`, restart and ask `Compare Tel Aviv and Haifa`. `build_context` keeps only the first chunk, because the best chunk always survives and nothing else fits. Input tokens drop; check whether the answer still covers both cities. That's the quality side of every cost cut, and why the report runs accuracy next to cost.

> Measure cost and quality together, or you'll optimise the wrong thing. On this data the context cap saved almost nothing, while removing a duplicated schema saved 16 % for free. Numbers beat intuition again.

## Cheat sheet

- **Input tokens**: Tokens the model reads: instructions, context, history and the question. The biggest cost driver here.
- **Output tokens**: Tokens the model writes. Pricier per token, but answers here are about 40 tokens.
- **usage field**: The provider's token count on each response (`input_tokens`, `output_tokens`, or `prompt_tokens` for embeddings).
- **Price per 1M tokens**: How providers quote prices. Cost = tokens × price ÷ 1,000,000.
- **Per-request roll-up**: Summing every call made while serving one request, so multi-call paths show their true cost.
- **Token budget**: A cap on how many tokens a prompt section may use. Here `MAX_CONTEXT_TOKENS` for retrieved context.
- **Token estimate**: A cheap approximation (about 4 characters per token in English) used for budgets, never for billing.
- **Structured outputs**: The API enforces a JSON schema (`strict: True`), so the prompt doesn't need to repeat it.
- **Cost/quality trade-off**: Every saving is checked against accuracy on the same eval set before it's kept.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why read <code>response.usage</code> instead of counting tokens ourselves?</summary><p>The provider's count is what you're billed for. Our <code>estimate_tokens</code> (chars / 4) is only good enough for budgets.</p></details>
<details><summary>A follow-up question with a session costs more than the first question. Why?</summary><p><code>contextualize</code> makes an extra LLM call to rewrite the follow-up into a standalone question. The tracker sums both calls, so <code>llm_calls</code> is 2.</p></details>
<details><summary>Why did removing the schema from the prompt save more than capping the context?</summary><p>The schema was about 78 tokens on every call and added nothing, since <code>strict</code> structured outputs already enforce it. The retrieved context was already small on this data, so the cap rarely cut anything.</p></details>
<details><summary>What does <code>build_context</code> do if the best chunk alone is bigger than the budget?</summary><p>It keeps it anyway. The <code>kept and</code> condition only stops adding once at least one chunk is in, so there's always some context.</p></details>
<details><summary>An unknown model returns cost 0. Why not raise an error?</summary><p>Cost tracking must never break a user's request. The trade-off is a silent under-count, so the <code>no_price_for_model</code> warning has to be watched.</p></details>
</div>

**Next:** Day 25 – Guard Both Doors

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
