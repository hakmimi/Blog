---
title: "Day 29: Design Before Code"
description: "Month 2 starts a new project: a payment-routing decision agent. This episode writes the design and the data contracts first, so every later day has a clear target and a test to pass."
series: "ai-engineering"
order: 31
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "design doc", "pydantic contracts", "fastapi skeleton"]
readingTime: "9 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day29`](https://github.com/hakmimi/AIEngineering/tree/main/Day29). Layers touched: L1 Data, L4 System.

## Goals

- **G1. Frame a business problem an agent can own: what it decides, and what counts as success.**  
  You can: explain route / manual review / decline and the success criteria from `DESIGN.md` in one minute.
- **G2. Split the work between deterministic code and the LLM before writing any logic.**  
  You can: read the ownership table and say why fees and eligibility never go to the model.
- **G3. Turn the needed information into a strict input model and a strict output model.**  
  You can: show `Transaction` rejecting an unknown field, a lower-case country and a 200-day-old 'new' customer.
- **G4. Ship a runnable skeleton with tests before the first decision exists.**  
  You can: run `/health`, `/events/validate` and `python -m pytest` live.

## System map

Month 2 gets a fresh map. Today only the input side is real: the request passes through the request-id middleware and the `Transaction` gate, then gets echoed back. The `Decision` contract exists but nothing produces it yet.

> Business event → API → Transaction contract → (Decision Agent, coming) → Decision contract

<div class="ae-map" role="img" aria-label="A client or the five sample events send JSON to main.py. The request-id middleware tags the request. The Transaction model in schemas.py validates it, reading MAX_AMOUNT from config.py, and bad input returns 422. POST /events/validate logs the event as JSON and echoes the normalised transaction back. The Decision model and DESIGN.md describe the output and the flow that later days will build."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 451" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">INPUT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L4 · SCHEMAS.PY</text><text class="lane" x="752" y="18">L4 · MAIN.PY</text><text class="lane" x="996" y="18">CONTRACTS + PLAN</text><path class="edge" d="M200,125 C230,125 230,125 261,125" marker-end="url(#mka)"></path><path class="edge" d="M200,212 C230,212 230,125 261,125" marker-end="url(#mka)"></path><path class="edge" d="M444,125 C474,125 474,159 505,159" marker-end="url(#mka)"></path><path class="edge-old" d="M598,95 L598,114" marker-end="url(#mkm)"></path><path class="edge" d="M598,201 L598,220" marker-end="url(#mka)"></path><path class="edge" d="M688,159 C718,159 718,122 749,122" marker-end="url(#mka)"></path><path class="edge-old" d="M842,156 L842,175" marker-end="url(#mkm)"></path><path class="edge-ghost" d="M932,122 C962,122 962,118 993,118" marker-end="url(#mkx)"></path><path class="edge-back" d="M842,156 V333 H110 V158" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="94"></rect><text class="nt t" text-anchor="middle" x="110" y="118">Client</text><text class="ns s" text-anchor="middle" x="110" y="138">/docs · PowerShell</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="20" y="178"></rect><text class="nt t" text-anchor="middle" x="110" y="210">sample_events.json</text><text class="ns s" text-anchor="middle" x="110" y="228">5 events, 5 paths</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="190">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="87"></rect><text class="nt t" text-anchor="middle" x="354" y="111">request-id middleware</text><text class="ns s" text-anchor="middle" x="354" y="130">X-Request-ID header</text><text class="ns s" text-anchor="middle" x="354" y="145">reused from Month 1</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="185"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="217">GET /health</text><text class="ns s" text-anchor="middle" x="354" y="236">liveness</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="198">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="508" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="58">config.py</text><text class="ns s" text-anchor="middle" x="598" y="77">MAX_AMOUNT · settings</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="117"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="149">Transaction</text><text class="ns s" text-anchor="middle" x="598" y="168">closed enums · extra=forbid</text><text class="ns s" text-anchor="middle" x="598" y="183">cross-field rules</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="130">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="223"></rect><text class="nt t" text-anchor="middle" x="598" y="255">422 error</text><text class="ns s" text-anchor="middle" x="598" y="274">bad events never reach</text><text class="ns s" text-anchor="middle" x="598" y="289">logic</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="236">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="752" y="87"></rect><text class="nt t" text-anchor="middle" x="842" y="119">POST /events/validate</text><text class="ns s" text-anchor="middle" x="842" y="138">echo normalised event</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="100">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="178"></rect><text class="nt t" text-anchor="middle" x="842" y="202">log_event → JSON</text><text class="ns s" text-anchor="middle" x="842" y="221">event_validated + request</text><text class="ns s" text-anchor="middle" x="842" y="236">id</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="996" y="68"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="100">Decision</text><text class="ns s" text-anchor="middle" x="1086" y="119">route · manual_review ·</text><text class="ns s" text-anchor="middle" x="1086" y="134">decline</text><text class="ns s" text-anchor="middle" x="1086" y="149">reason codes · risk 0–1</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="81">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="189"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="221">docs/DESIGN.md</text><text class="ns s" text-anchor="middle" x="1086" y="240">problem · flow · API plan</text><text class="ns s" text-anchor="middle" x="1086" y="255">code vs LLM table</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="202">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="108"></rect><text class="el" text-anchor="middle" x="230" y="119">JSON</text><rect class="elbg" height="15" rx="3" width="46" x="939" y="102"></rect><text class="el" text-anchor="middle" x="962" y="114">Day 31</text><rect class="elbg" height="15" rx="3" width="149" x="402" y="326"></rect><text class="el" text-anchor="middle" x="476" y="337">{ valid, transaction }</text><text class="lane" style="fill:var(--ghost)" x="20" y="381">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="391"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="418">Day 30 · synthetic business data</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="300" y="391"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="430" y="418">Day 31 · baseline rules engine</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: A finished assistant, no new problem

- Month 1 ended with a packaged RAG assistant (Day 28)
- No payment domain, no data, no definition of a good decision
- Nothing says which steps an LLM is allowed to own
- No API for business events

### After this episode: A problem with contracts

- `docs/DESIGN.md`: problem, outputs, agent flow, API plan by day, success criteria
- `Transaction` rejects unknown fields, bad countries, naive or future timestamps
- `Decision` forces reason codes and a provider only when routing
- `/health` and `/events/validate` run, with 35 offline tests

> **Why it matters:** the next 27 days add tools, an LLM, a graph, evaluation and deployment around this project. Each of those is judged against the two contracts written today. If the input and output are vague, no test and no evaluation later can be trusted.

## Code walkthrough

Four snippets from `Day29`. The whole episode is about contracts, so every snippet is a rule the data must obey.

### schemas.py · the input contract

```python
class Transaction(BaseModel):
    """A business event the agent must decide on."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    transaction_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    timestamp: datetime
    amount: float = Field(..., gt=0, description="In `currency`, major units")
    currency: Currency
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 of the customer, upper case")
    merchant_category: MerchantCategory
    customer_type: CustomerType
    payment_method: PaymentMethod
    customer_age_days: int = Field(..., ge=0, le=36500, description="Days since the customer account was created")
    prior_chargebacks: int = Field(default=0, ge=0, le=100)
```

**Every field the agent needs is typed, bounded, and nothing else gets in.** `extra="forbid"` means an `is_admin` field or a hidden label is rejected. `Currency`, `MerchantCategory` and the others are closed enums, so `JPY` or `crypto` fail at the door.

### schemas.py · rules across fields

```python
@field_validator("timestamp")
@classmethod
def timestamp_is_aware_and_not_future(cls, value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must include a timezone (e.g. 2026-01-05T10:30:00Z)")
    if value > datetime.now(timezone.utc) + timedelta(minutes=5):      # 5 min of clock skew is tolerated
        raise ValueError("timestamp is in the future")
    return value

@model_validator(mode="after")
def new_customers_cannot_be_old(self) -> "Transaction":
    if self.customer_type is CustomerType.NEW and self.customer_age_days > 90:
        raise ValueError("a 'new' customer cannot have an account older than 90 days")
    return self
```

**Some errors only show up when you look at two fields together.** A timestamp without a timezone is ambiguous in a payments system. A 'new' customer with a 200-day-old account is a data-quality problem. Both become a 422 here, before any decision logic exists.

### schemas.py · the output contract

```python
class Decision(BaseModel):
    """The agent's answer. `reason_codes` are the audit-grade explanation; `explanation` is optional prose."""
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    action: Action
    selected_provider: str | None = None
    reason_codes: list[ReasonCode] = Field(min_length=1)
    risk_score: float = Field(ge=0, le=1)
    expected_cost: float | None = Field(default=None, ge=0, description="Fee in the transaction currency")
    expected_approval_probability: float | None = Field(default=None, ge=0, le=1)
    explanation: str | None = None

    @model_validator(mode="after")
    def provider_matches_action(self) -> "Decision":
        if self.action is Action.ROUTE and not self.selected_provider:
            raise ValueError("action 'route' requires selected_provider")
        if self.action is not Action.ROUTE and self.selected_provider:
            raise ValueError("only action 'route' may carry a selected_provider")
        return self
```

**The output schema makes an unexplained decision impossible.** At least one reason code, from a closed enum. A provider only when the action is `route`. Later, when the LLM joins, it writes prose around these codes and never replaces them.

### main.py · the skeleton route

```python
@app.post("/events/validate")
def validate_event(transaction: Transaction) -> dict:
    """Accept a transaction and echo it back normalised - proves the input contract before any decision logic exists."""
    log_event(logger, "event_validated", transaction_id=transaction.transaction_id, amount=transaction.amount,
              currency=transaction.currency.value, country=transaction.country)
    return {"valid": True, "transaction": transaction.model_dump(mode="json")}
```

**Echo the cleaned input back before you decide anything.** This route proves the contract end to end: the client sees exactly what the agent will see, with the amount rounded and whitespace stripped. The `log_event` line carries the request id from the middleware.

## Run it

Run from `Day29` in PowerShell. Build the transaction as a hashtable once, then change one field at a time.

**Step 1**

```powershell
uvicorn main:app --reload
```

**Expect:** `Uvicorn running on http://127.0.0.1:8000`. Open `/docs`: only `/health` and `/events/validate` exist.

**Step 2**

```text
$tx = @{transaction_id="t-1"; timestamp="2026-01-05T09:12:00Z"; amount=85.5; currency="ILS"; country="IL"
  merchant_category="groceries"; customer_type="returning"; payment_method="card"
  customer_age_days=400; prior_chargebacks=0}
Invoke-RestMethod http://127.0.0.1:8000/events/validate -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
```

**Expect:** `valid: True` and the transaction echoed back. The uvicorn terminal shows a JSON `event_validated` log line with a `request_id`.

**Step 3**

```text
$tx.amount = 10.456; $tx.transaction_id = "  abc-1  "
Invoke-RestMethod http://127.0.0.1:8000/events/validate -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json)
```

**Expect:** The echo shows `amount: 10.46` and `transaction_id: abc-1`. Normalisation happens in the contract.

**Step 4**

```powershell
Get-Content data\sample_events.json -Raw | ConvertFrom-Json | ForEach-Object {
  (Invoke-RestMethod http://127.0.0.1:8000/events/validate -Method Post `
    -ContentType "application/json" -Body ($_ | ConvertTo-Json)).valid }
```

**Expect:** Five lines of `True`: grocery, big new-customer electronics, risky wallet, unsupported bank transfer, VIP travel.

**Step 5**

```powershell
python -m pytest
```

**Expect:** `35 passed`, all offline. The parametrised test alone covers 21 invalid field values.

### Break it on purpose

#### 1 · Sneak in an extra field

Add `$tx.is_admin = $true` and send it again. PowerShell throws a red error with status **422**, and the body names `is_admin` as `extra_forbidden`. The same rule will later stop the hidden truth columns of the synthetic data from leaking into the agent.

#### 2 · The real bug: a positive amount that becomes zero

Set `$tx.amount = 0.004` and send it. `Field(gt=0)` checks the raw value, which is positive, so it passes. Then `amount_within_limit` returns `round(value, 2)`, which is **0.0**. The echo shows `amount: 0.0` with `valid: True`, a zero-value payment the rest of the agent will happily score. Fees divide by the amount on Day 31, so this is worth fixing now. The lesson: when a validator changes a value, check the value it returns.

```python
@field_validator("amount")
@classmethod
def amount_within_limit(cls, value: float) -> float:
    if value > settings.max_amount:
        raise ValueError(f"amount exceeds the maximum of {settings.max_amount:,.0f}")
    rounded = round(value, 2)
    if rounded <= 0:
        raise ValueError("amount must be at least 0.01")
    return rounded
```

> A contract is only as strong as its last line. Validators run in order, and the one that normalises a value can undo the one that checked it. Add a test for `0.004` next to the existing `0` and `-5` cases.

## Cheat sheet

- **Decision agent**: A system that takes a business event and returns an action with reasons. Here: route, manual review or decline a payment.
- **Payment routing**: Choosing which payment provider (PSP) carries a transaction, trading approval probability against fees and risk.
- **PSP**: Payment service provider: the company that actually processes the card, wallet or bank transfer.
- **Chargeback**: A payment reversed by the customer's bank after a dispute. Prior chargebacks are a risk signal.
- **Closed enum**: A field that only accepts a fixed list of values (`StrEnum`). Anything else is a 422.
- **extra="forbid"**: Pydantic setting that rejects any field the model doesn't declare.
- **Cross-field validation**: A `model_validator` that checks fields together, like a 'new' customer with an old account.
- **Reason code**: A stable machine-readable explanation (`HIGH_RISK`, `CHEAPEST_ELIGIBLE`) attached to every decision.
- **Manual review**: Sending the case to a human. It's the safe fallback whenever the agent is unsure.
- **Hybrid agent**: Deterministic code makes the decision; the LLM explains it and may only push it toward more caution.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Which steps in the design belong to code, and which to the LLM?</summary><p>Code owns validation, risk, eligibility, cost and approval math, ranking and policy. The LLM only writes the explanation and gives an advisory second opinion.</p></details>
<details><summary>What does "the LLM may make a decision safer, never riskier" mean in practice?</summary><p>The LLM can recommend moving <code>route</code> to <code>manual_review</code>. It can never approve a review or decline, or pick a different provider.</p></details>
<details><summary>Why does Transaction use extra="forbid"?</summary><p>Unknown fields are either mistakes or attempts to smuggle data in, like <code>is_admin</code> or hidden labels. Rejecting them keeps the agent's view of a payment exact.</p></details>
<details><summary>Why must a Decision with action decline have no selected_provider?</summary><p>A provider only makes sense when the payment is routed. The model validator rejects the mismatch, so a contradictory decision can't exist.</p></details>
<details><summary>Why is 0.004 accepted as an amount, and what does the agent receive?</summary><p><code>gt=0</code> checks the raw value, which is positive. The field validator then rounds it to 0.0 and returns that, so the agent gets a zero amount.</p></details>
</div>

**Next:** Day 30 – Data With Hidden Truth

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
