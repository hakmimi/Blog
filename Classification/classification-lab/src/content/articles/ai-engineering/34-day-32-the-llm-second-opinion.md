---
title: "Day 32: The LLM Second Opinion"
description: "The rules engine keeps the decision; an LLM reviews it, explains it in business language, and may flag it for a human. Code enforces that the model can only make a decision safer, never riskier."
series: "ai-engineering"
order: 34
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "openai structured output", "control rules", "grounding"]
readingTime: "11 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day32`](https://github.com/hakmimi/AIEngineering/tree/main/Day32). Layers touched: L2 LLM, L3 Orchestration, L4 System.

## Goals

- **G1. Add an LLM review after the baseline decision, with a strict JSON contract.**  
  You can: show a live `/decision/ai` response with `llm_status`, the review fields and usage.
- **G2. Enforce in code what the LLM may change.**  
  You can: explain the one allowed change, route → manual_review, and why decline can't be softened.
- **G3. Validate model output before trusting it, including invented numbers.**  
  You can: show a review rejected by the grounding check and replaced by the template.
- **G4. Degrade safely when the model is down.**  
  You can: run with a bad key and show the same decision with `llm_status: unavailable`.

## System map

The Day 31 engine is now one grey box. After it comes the new part: a review prompt, one structured LLM call, a validation gate and the control rules that decide what the review is allowed to change.

> Transaction → Baseline decision → LLM review (explain / agree? / concerns / escalate?) → Control rules → Final decision

<div class="ae-map" role="img" aria-label="The client posts to POST /decision/ai. decide_ai runs the Day 31 baseline, renders the review prompt from the transaction, decision, risk components, candidates and rejections, and calls the OpenAI Responses API through llm.py with a strict JSON schema. _validate checks length, concerns and grounding of numbers. _apply_control_rules keeps the baseline action unless the LLM escalates a routed payment to manual_review. If the LLM is unavailable or its output is rejected, the template explanation is used. The response returns the final and baseline decisions, the review, status, notes, usage and latency."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 466" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">RULES (DAY 31)</text><text class="lane" x="508" y="18">L2 · PROMPTS + LLM</text><text class="lane" x="752" y="18">EXTERNAL</text><text class="lane" x="996" y="18">L3 · AI_DECISION.PY</text><path class="edge" d="M200,178 C230,178 230,129 261,129" marker-end="url(#mka)"></path><path class="edge-old" d="M354,164 L354,182" marker-end="url(#mkm)"></path><path class="edge" d="M444,224 C474,224 474,125 505,125" marker-end="url(#mka)"></path><path class="edge" d="M598,167 L598,186" marker-end="url(#mka)"></path><path class="edge" d="M688,231 C718,231 718,178 749,178" marker-end="url(#mka)"></path><path class="edge" d="M932,178 C962,178 962,76 993,76" marker-end="url(#mka)"></path><path class="edge" d="M1086,118 L1086,137" marker-end="url(#mka)"></path><path class="edge-old" d="M1086,224 L1086,243" marker-end="url(#mkm)"></path><path class="edge-back" d="M1086,224 V348 H110 V212" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="148"></rect><text class="nt t" text-anchor="middle" x="110" y="172">Client</text><text class="ns s" text-anchor="middle" x="110" y="190">PowerShell · compare_ai.py</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="94"></rect><text class="nt t" text-anchor="middle" x="354" y="126">POST /decision/ai</text><text class="ns s" text-anchor="middle" x="354" y="146">Transaction gate · 422</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="108">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="186"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="210">decide_baseline()</text><text class="ns s" text-anchor="middle" x="354" y="228">risk · rules · eligibility</text><text class="ns s" text-anchor="middle" x="354" y="244">score · reason codes</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="83"></rect><text class="nt t" text-anchor="middle" x="598" y="115">render_review_prompt</text><text class="ns s" text-anchor="middle" x="598" y="134">no tx id · decision · risk</text><text class="ns s" text-anchor="middle" x="598" y="149">top 3 candidates</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="96">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="189"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="221">get_structured()</text><text class="ns s" text-anchor="middle" x="598" y="240">strict JSON schema</text><text class="ns s" text-anchor="middle" x="598" y="255">retry · usage tracking</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="202">NEW</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="752" y="140"></rect><text class="nt t" text-anchor="middle" x="842" y="164">OpenAI Responses API</text><text class="ns s" text-anchor="middle" x="842" y="183">gpt-4.1-mini · temperature</text><text class="ns s" text-anchor="middle" x="842" y="198">0</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="66">_validate()</text><text class="ns s" text-anchor="middle" x="1086" y="85">≤600 chars · ≤3 concerns</text><text class="ns s" text-anchor="middle" x="1086" y="100">no invented numbers</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="140"></rect><text class="nt t" text-anchor="middle" x="1086" y="172">_apply_control_rules</text><text class="ns s" text-anchor="middle" x="1086" y="191">route → manual_review only</text><text class="ns s" text-anchor="middle" x="1086" y="206">AI_ESCALATION</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="153">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="996" y="246"></rect><text class="nt t" text-anchor="middle" x="1086" y="270">template fallback</text><text class="ns s" text-anchor="middle" x="1086" y="289">unavailable ·</text><text class="ns s" text-anchor="middle" x="1086" y="304">rejected_output</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="136"></rect><text class="el" text-anchor="middle" x="230" y="148">JSON</text><rect class="elbg" height="15" rx="3" width="91" x="673" y="188"></rect><text class="el" text-anchor="middle" x="718" y="198">review prompt</text><rect class="elbg" height="15" rx="3" width="34" x="946" y="110"></rect><text class="el" text-anchor="middle" x="962" y="121">JSON</text><rect class="elbg" height="15" rx="3" width="283" x="456" y="341"></rect><text class="el" text-anchor="middle" x="598" y="352">{ decision, baseline_decision, llm, usage }</text><text class="lane" style="fill:var(--ghost)" x="20" y="396">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="254" x="20" y="406"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="147" y="433">Day 33 · tools for the agent</text></g><g class="node-ghost"><rect height="44" rx="8" width="214" x="294" y="406"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="401" y="433">Day 34 · decision graph</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Correct, but terse

- `decide_baseline()` makes every decision with reason codes
- Explanations are a fixed template sentence
- No second opinion on borderline payments
- No LLM, so no token cost and no latency

### After this episode: Explained, still controlled

- `POST /decision/ai` returns final and baseline decisions side by side
- The LLM explains, lists up to 3 concerns and may flag escalation
- Only route → manual_review can happen; reviews with invented numbers are discarded
- LLM failure falls back to the template; 112 tests pass with the LLM mocked

> **Why it matters:** this is the pattern the rest of the project depends on: the model adds language and judgment, while code keeps the authority. Every later node, tool and evaluation assumes the LLM can't make a payment riskier, and a test checks that for every combination of model answers.

## Code walkthrough

Four snippets from `Day32`: what the model sees, how it answers, how the answer is checked, and what it's allowed to change.

### prompts.py · the review prompt

```python
REVIEW_PROMPT = """You are a payments risk analyst reviewing an automated routing decision. The decision was made by a
rules engine and is FINAL unless you recommend escalation. Your job:
1. explanation: 2-3 plain-English sentences for a business user saying what was decided and why. Use ONLY the facts in
   the data below (reason codes, risk components, providers). Do not invent numbers, providers or policies.
2. agrees_with_baseline: do the facts support the decision?
3. concerns: up to 3 short concerns worth a human's attention (empty list if none).
4. escalate_to_review: true ONLY if the baseline decision was "route" AND you see a concrete risk signal in the data that the
   rules under-weighted. Never escalate a decision that is already manual_review or decline. Do not escalate just because the
   amount or country is unfamiliar, and do not try to change the provider.
5. confidence: 0-1, how sure you are about your assessment.
```

**The prompt tells the model its job is to explain a decision that's already made.** It asks for five things and says when escalation is allowed. The prompt is a request, though. The next two snippets are where the rules actually hold.

### llm.py · one structured call

```python
def _call_once(prompt: str, schema: dict, name: str) -> dict:
    client = get_client()
    try:
        response = client.responses.create(
            model=settings.llm_model, input=prompt, temperature=0,
            text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
        )
    except OpenAIError as exc:
        logger.error("llm_call_failed step=%s type=%s", name, type(exc).__name__)
        raise ExternalServiceError(retryable=is_retryable(exc)) from exc
    usage = getattr(response, "usage", None)
    if usage is not None:
        record_usage("llm", name, settings.llm_model, usage.input_tokens, usage.output_tokens)
    try:
        return json.loads(response.output_text)
    except json.JSONDecodeError as exc:
        raise ExternalServiceError("The AI service returned an invalid response", retryable=True) from exc
```

**One place talks to the model, and it only accepts schema-shaped JSON.** Strict JSON schema output, temperature 0, usage recorded per call. Provider errors become `ExternalServiceError`, which is what the fallback path catches.

### ai_decision.py · the validation gate

```python
def _validate(raw: dict, tx: Transaction, baseline: BaselineResult) -> tuple[LLMReview | None, list[str]]:
    """Accept the model's review only if it is usable and grounded; otherwise (None, why)."""
    explanation = (raw.get("explanation") or "").strip()
    if not explanation:
        return None, ["empty explanation"]
    if len(explanation) > settings.llm_max_explanation_chars:
        return None, [f"explanation longer than {settings.llm_max_explanation_chars} characters"]
    invented = ungrounded_numbers(explanation, source_text(tx, baseline))
    if invented:
        return None, [f"explanation contains numbers not in the data: {invented}"]
    concerns = [c.strip()[:MAX_CONCERN_CHARS] for c in raw.get("concerns", []) if c.strip()][:MAX_CONCERNS]
    return LLMReview(explanation, bool(raw["agrees_with_baseline"]), concerns, bool(raw["escalate_to_review"]),
                     float(raw["confidence"])), []
```

**A review must be usable and grounded, or it's thrown away.** Empty, too long, or containing numbers that aren't in the data the model was shown: the review is discarded and `llm_status` becomes `rejected_output`. Keep this line in mind for the break-it segment.

### ai_decision.py · the control rules

```python
def _apply_control_rules(baseline: Decision, review: LLMReview | None) -> tuple[Decision, list[str]]:
    """The only ways the LLM can influence the outcome. Everything else is ignored by construction."""
    if review is None:
        return baseline.model_copy(update={"explanation": template_explanation(baseline)}), []
    final = baseline.model_copy(update={"explanation": review.explanation})
    notes: list[str] = []
    if review.escalate_to_review:
        if baseline.action is Action.ROUTE:
            final = final.model_copy(update={
                "action": Action.MANUAL_REVIEW, "selected_provider": None, "expected_cost": None,
                "expected_approval_probability": None, "reason_codes": [ReasonCode.AI_ESCALATION, *baseline.reason_codes]})
            notes.append("escalated from route to manual_review by the AI reviewer")
        else:
            notes.append(f"ignored escalation flag: baseline is already {baseline.action.value}")
    return final, notes
```

**The LLM has exactly one lever, and it only points toward a human.** A routed payment can become `manual_review` with `AI_ESCALATION`, and its provider and cost are cleared. A review or decline stays as it is, whatever the model says. Disagreement alone changes nothing.

## Run it

Run from `Day32` in PowerShell with a real key in `.env`. Every `/decision/ai` call costs a fraction of a cent and takes about 2 seconds.

**Step 1**

```powershell
python -m pytest
```

**Expect:** 112 tests pass with the LLM mocked, no key needed.

**Step 2**

```powershell
uvicorn main:app --reload
$tx = @{transaction_id="t-1"; timestamp="2026-01-05T09:12:00Z"; amount=85.5; currency="ILS"; country="IL"
  merchant_category="groceries"; customer_type="returning"; payment_method="card"
  customer_age_days=400; prior_chargebacks=0}
Invoke-RestMethod http://127.0.0.1:8000/decision/ai -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

**Expect:** `llm_status: ok`, `changed_by_ai: False`, the decision still routes to `epsilon_local_il`, and `decision.explanation` is now the LLM's text. `usage` shows one LLM call; `latency_ms` is around 2,000.

**Step 3**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/decision/baseline -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

**Expect:** Same decision, template explanation, no `usage` and a few milliseconds. This is what the LLM costs you.

**Step 4**

```text
$tx.country="NG"; $tx.merchant_category="gaming"; $tx.customer_type="new"; $tx.customer_age_days=5
$tx.prior_chargebacks=2; $tx.payment_method="wallet"; $tx.currency="USD"
Invoke-RestMethod http://127.0.0.1:8000/decision/ai -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

**Expect:** `decline` in both `decision` and `baseline_decision`. If the model set `escalate_to_review`, `notes` says the flag was ignored.

**Step 5**

```powershell
python -m scripts.compare_ai
```

**Expect:** 10 rows (5 sample events + the 5 most borderline routed payments), then a summary. The README run had `llm_ok: 10`, `agreed: 10`, `decisions_changed: 0`, about $0.00045 and 2 s per decision.

### Break it on purpose

#### 1 · Bad key vs no key

Stop uvicorn, set `$env:OPENAI_API_KEY="sk-invalid"`, start it again and resend the grocery payment. OpenAI rejects the key, `llm.py` turns it into `ExternalServiceError`, and you get **200** with `llm_status: unavailable`, the template explanation and the same decision. Now remove the variable and rename `.env` so no key exists at all. `get_client()` raises `ConfigurationError`, which `decide_ai` doesn't catch, so the API returns **500** `OPENAI_API_KEY is not configured` and the baseline decision it already computed is lost. Decide which you want: fail loudly on misconfiguration, or fall back like any other LLM outage.

```text
# ai_decision.py - treat a missing key like any other LLM outage
from errors import ConfigurationError, ExternalServiceError
...
    except (ExternalServiceError, ConfigurationError):
        status, notes = "unavailable", ["LLM unavailable - deterministic explanation used"]
```

#### 2 · The real bug: honest rounding counts as invented

The grounding check only accepts exact values and exact percentage forms. The model sees `0.9235` and `0.0625`; a normal sentence says "about 92% approval, risk 0.06". Run:
`python -c 'from grounding import ungrounded_numbers as u; print(u(''Fee 1.72, about 92% approval, risk 0.06.'', ''1.72 0.9235 0.0625''))'`
It prints `['0.06', '92']`. On a live call that means `rejected_output` and the template, even though the model told the truth. The template itself writes "92%" and "0.06", so the check rejects the same rounding the code does. The README's 10 cases happened not to round; any model that does will lose its explanation. Day 33 fixes it by accepting ordinary rounding at the text's precision.

```text
# Day33/grounding.py - a number is fine if it rounds from a source value
def _derivable(token: str, source_values: list[float]) -> bool:
    value, places = float(token), _decimals(token)
    for s in source_values:
        for candidate in (s, s * 100, s / 100):
            if round(candidate, places) == round(value, places) or abs(candidate - value) < 1e-9:
                return True
    return False
```

> Guards need tests with realistic output, not only the happy example. A check that's too strict fails safe here, since the template takes over, but it quietly throws away the value you're paying the LLM for.

## Cheat sheet

- **Hybrid decision**: Rules make the decision of record; the LLM explains it and gives an advisory opinion.
- **Second opinion**: The LLM's `agrees_with_baseline`, `concerns` and `escalate_to_review`. Advisory: code decides what, if anything, changes.
- **Control rules**: Code that limits what the LLM output can change. Here only route → manual_review.
- **Escalation**: Moving a routed payment to a human reviewer. Reason code `AI_ESCALATION`.
- **Structured output**: Asking the model for JSON that must match a schema. With `strict: True` the API enforces the shape.
- **Grounding check**: Rejecting generated text whose numbers don't appear in the data the model was given.
- **llm_status**: `ok`, `unavailable` (the call failed) or `rejected_output` (the answer failed validation).
- **Graceful degradation**: When a dependency fails, the system keeps working with less: here, the same decision with the template text.
- **Cost per decision**: Tokens times price for the LLM call, tracked by `usage.py`. About $0.00045 in the README's run.
- **Monotonic safety**: A rule that the final action is never more permissive than the baseline's, tested for every model answer.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>The LLM says it disagrees but doesn't set escalate_to_review. What happens?</summary><p>Nothing changes. Disagreement alone is recorded in the review, but only the escalation flag on a routed payment can change the action.</p></details>
<details><summary>The baseline declines and the LLM sets escalate_to_review. What's the final action?</summary><p>Still <code>decline</code>. The control rules ignore the flag and add a note that the baseline is already decline.</p></details>
<details><summary>Why is the transaction id left out of the prompt?</summary><p>It adds nothing to the reasoning, costs tokens, and a test checks it isn't there. The model gets the facts, not identifiers.</p></details>
<details><summary>Why can't a rejected review escalate?</summary><p>A review that fails validation is discarded completely. Its flags are as untrusted as its text, so the decision stays with the baseline.</p></details>
<details><summary>The README run showed 10 of 10 agreements and zero changes. Is the LLM useless here?</summary><p>On those cases it added readable explanations but no challenge value. That's a finding: the evaluation set on Day 36 adds cases where a second opinion should matter, and Day 39 asks whether easy cases need the LLM at all.</p></details>
</div>

**Next:** Day 33 – Audited Tool Calls

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
