---
title: "Day 31: Rules Before Models"
description: "Before any LLM touches a payment, a deterministic engine decides: risk score, hard eligibility rules, provider scoring and a fixed decision order with reason codes. It becomes the decision of record and the benchmark the AI version has to beat."
series: "ai-engineering"
order: 33
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "rules engine", "risk scoring", "reason codes"]
readingTime: "9 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day31`](https://github.com/hakmimi/AIEngineering/tree/main/Day31). Layers touched: L1 Data, L3 Orchestration, L4 System.

## Goals

- **G1. Compute a transparent, table-based risk score.**  
  You can: read the five risk components of a live decision and add them up on screen.
- **G2. Apply hard eligibility constraints and explain every rejection.**  
  You can: show `rejected_providers` with causes like `method_not_supported` and `amount_above_limit`.
- **G3. Rank eligible providers and choose with a fixed, explainable decision order.**  
  You can: trigger route, manual review, decline and no-eligible-provider live.
- **G4. Measure the baseline against the hidden truth.**  
  You can: run `compare_baseline` and explain the 0.87 Spearman and the 25 % fraud capture.

## System map

The empty middle of the Day 29 map is filled in, with no LLM anywhere. Risk comes first, then the hard rules, then eligibility and scoring. Every branch writes a reason code, and the template turns codes into a sentence.

> Transaction → Risk → Hard rules (decline / review) → Eligibility → Score providers → Select → Decision + reason codes

<div class="ae-map" role="img" aria-label="The client posts a transaction to POST /decision/baseline. risk.py computes a risk score from the risk tables. decision_engine.py applies the risk rules (decline at 0.70, review at 0.45, new customer over 1,000 USD), then checks each provider's eligibility with ineligible_reason and scores the eligible ones with score_provider, then selects the best with reason codes. explanations.py writes a template sentence. The response includes the decision, the risk breakdown, ranked candidates and rejected providers. compare_baseline.py runs the same engine over the 1,000 synthetic transactions and compares with the hidden truth."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 489" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · MAIN.PY</text><text class="lane" x="508" y="18">L3 · RISK.PY</text><text class="lane" x="752" y="18">L3 · DECISION_ENGINE.PY</text><text class="lane" x="996" y="18">OUTPUT</text><path class="edge" d="M200,144 C230,144 230,120 261,120" marker-end="url(#mka)"></path><path class="edge" d="M354,150 L354,170" marker-end="url(#mka)"></path><path class="edge" d="M444,231 C474,231 474,136 505,136" marker-end="url(#mka)"></path><path class="edge" d="M200,231 C352,231 352,136 505,136" marker-end="url(#mka)"></path><path class="edge-old" d="M598,208 L598,189" marker-end="url(#mkm)"></path><path class="edge" d="M688,136 C718,136 718,84 749,84" marker-end="url(#mka)"></path><path class="edge" d="M688,136 C718,136 718,197 749,197" marker-end="url(#mka)"></path><path class="edge" d="M842,239 L842,258" marker-end="url(#mka)"></path><path class="edge" d="M932,84 C962,84 962,136 993,136" marker-end="url(#mka)"></path><path class="edge" d="M932,303 C962,303 962,136 993,136" marker-end="url(#mka)"></path><path class="edge" d="M932,303 C962,303 962,235 993,235" marker-end="url(#mka)"></path><path class="edge-back" d="M1086,171 V371 H110 V178" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="114"></rect><text class="nt t" text-anchor="middle" x="110" y="138">Client</text><text class="ns s" text-anchor="middle" x="110" y="156">PowerShell · /docs</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="20" y="196"></rect><text class="nt t" text-anchor="middle" x="110" y="228">compare_baseline.py</text><text class="ns s" text-anchor="middle" x="110" y="248">1,000 rows vs hidden truth</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="210">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="264" y="90"></rect><text class="nt t" text-anchor="middle" x="354" y="114">Transaction gate</text><text class="ns s" text-anchor="middle" x="354" y="132">Day 29 contract · 422</text></g><g class="node-new"><rect height="117" rx="8" width="180" x="264" y="172"></rect><text class="nt t" text-anchor="middle" x="354" y="204">POST</text><text class="nt t" text-anchor="middle" x="354" y="222">/decision/baseline</text><text class="ns s" text-anchor="middle" x="354" y="242">decision + risk +</text><text class="ns s" text-anchor="middle" x="354" y="256">candidates</text><text class="ns s" text-anchor="middle" x="354" y="272">+ rejected providers</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="186">NEW</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="508" y="87"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="119">compute_risk()</text><text class="ns s" text-anchor="middle" x="598" y="138">0.45·country +</text><text class="ns s" text-anchor="middle" x="598" y="153">0.35·category</text><text class="ns s" text-anchor="middle" x="598" y="168">+ customer + amount + cb</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="100">NEW</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="508" y="208"></rect><text class="nt t" text-anchor="middle" x="598" y="240">data_loader</text><text class="ns s" text-anchor="middle" x="598" y="259">providers · risk tables</text><text class="ns s" text-anchor="middle" x="598" y="274">+ medians, FX rates</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="221">CHANGED</text></g><g class="node-new"><rect height="99" rx="8" width="180" x="752" y="34"></rect><text class="nt t" text-anchor="middle" x="842" y="66">risk rules</text><text class="ns s" text-anchor="middle" x="842" y="85">≥0.70 decline · ≥0.45</text><text class="ns s" text-anchor="middle" x="842" y="100">review</text><text class="ns s" text-anchor="middle" x="842" y="115">new + &gt;1,000 USD review</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="155"></rect><text class="nt t" text-anchor="middle" x="842" y="187">ineligible_reason()</text><text class="ns s" text-anchor="middle" x="842" y="206">country · currency · method</text><text class="ns s" text-anchor="middle" x="842" y="221">amount · max_risk</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="168">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="752" y="261"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="293">score_provider()</text><text class="ns s" text-anchor="middle" x="842" y="312">fee · approval · score</text><text class="ns s" text-anchor="middle" x="842" y="327">select + reason codes</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="274">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="102"></rect><text class="nt t" text-anchor="middle" x="1086" y="134">template_explanation</text><text class="ns s" text-anchor="middle" x="1086" y="153">reason codes → sentence</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="115">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="193"></rect><text class="nt t" text-anchor="middle" x="1086" y="225">decision_made log</text><text class="ns s" text-anchor="middle" x="1086" y="244">inputs · risk · action</text><text class="ns s" text-anchor="middle" x="1086" y="259">eligible · rejected</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="206">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="115"></rect><text class="el" text-anchor="middle" x="230" y="126">JSON</text><rect class="elbg" height="15" rx="3" width="78" x="313" y="167"></rect><text class="el" text-anchor="middle" x="352" y="178">same engine</text><rect class="elbg" height="15" rx="3" width="200" x="498" y="364"></rect><text class="el" text-anchor="middle" x="598" y="375">{ decision, risk, candidates }</text><text class="lane" style="fill:var(--ghost)" x="20" y="419">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="238" x="20" y="429"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="139" y="456">Day 32 · LLM review on top</text></g><g class="node-ghost"><rect height="44" rx="8" width="230" x="278" y="429"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="393" y="456">Day 33 · lookups as tools</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Data, but no decisions

- 1,000 transactions and 6 providers sit in `data/`
- `Decision` exists as a schema only
- No risk score the agent can compute itself
- No way to say whether a routing choice was good

### After this episode: A rules engine of record

- `compute_risk()` returns a score and all five components
- `decide_baseline()` applies a fixed order and writes reason codes on every branch
- `POST /decision/baseline` returns ranked candidates and rejected providers with causes
- `compare_baseline.py`: Spearman 0.87 with the hidden risk; 89 tests pass

> **Why it matters:** an LLM agent without a baseline has nothing to be compared with. From Day 32 on, every AI change is measured against this engine: does it catch more fraud, cost less, or just cost more tokens? Rules also answer the exact questions (limits, fees, eligibility) better than any model.

## Code walkthrough

Four snippets from `Day31`, in the order a payment flows through them.

### risk.py · the agent's own risk estimate

```python
def compute_risk(tx: Transaction) -> RiskAssessment:
    tables = load_risk_tables()
    country = tables["country_risk"].get(tx.country, UNKNOWN_COUNTRY_RISK)
    category = tables["category_risk"][tx.merchant_category.value]
    typical = tables["category_median_usd"][tx.merchant_category.value]
    doublings = max(math.log2(max(amount_in_usd(tx), 1e-6) / typical), 0.0)

    components = {
        "country": round(W_COUNTRY * country, 4),
        "category": round(W_CATEGORY * category, 4),
        "customer": CUSTOMER_ADJUSTMENT[tx.customer_type],
        "amount": round(min(AMOUNT_STEP * doublings, AMOUNT_CAP), 4),
        "chargebacks": round(min(CHARGEBACK_STEP * tx.prior_chargebacks, CHARGEBACK_CAP), 4),
    }
    score = round(min(max(sum(components.values()), 0.0), 1.0), 4)
```

**A score you can explain line by line beats a better score you can't.** Each component is returned, so the API response shows exactly where the risk came from. An unknown country gets 0.40, treated as risky rather than safe. Day 35 will send those cases to a human instead.

### decision_engine.py · hard constraints

```python
def ineligible_reason(provider: Provider, tx: Transaction, risk: float) -> str | None:
    """None = eligible. Otherwise a short machine-readable cause."""
    if provider.supported_countries is not None and tx.country not in provider.supported_countries:
        return "country_not_supported"
    if tx.currency not in provider.supported_currencies:
        return "currency_not_supported"
    if tx.payment_method not in provider.supported_methods:
        return "method_not_supported"
    if tx.amount > provider.max_amount:
        return "amount_above_limit"
    if risk > provider.max_risk:
        return "risk_above_tolerance"
    assert can_carry(provider, tx.country, tx.currency.value, tx.payment_method.value, tx.amount)   # both views agree
    return None
```

**Every rejection has a cause, and the two definitions of "can carry" can't drift apart.** The first four checks mirror `simulation.can_carry`. The fifth is new: the provider's own risk tolerance. The assertion fails loudly if the engine and the simulator ever disagree.

### decision_engine.py · scoring

```python
def score_provider(provider: Provider, tx: Transaction, risk: float) -> Candidate:
    cost = round(tx.amount * provider.fee_percent / 100 + provider.fee_fixed, 2)
    approval = round(provider.base_approval_rate * provider.uptime * (1 - RISK_PENALTY * risk), 4)
    score = approval * (1 - cost / tx.amount) - LATENCY_WEIGHT * provider.avg_latency_ms
    return Candidate(provider.provider_id, cost, approval, provider.avg_latency_ms, round(score, 5))
```

**The score is expected merchant value per attempt.** Approval probability times the share of the amount you keep after fees. Latency only breaks ties. The approval is the agent's estimate from base rate, uptime and risk, never the hidden outcome.

### decision_engine.py · the fixed order

```python
def decide_baseline(tx: Transaction) -> BaselineResult:
    risk = compute_risk(tx)

    # 1. risk rules ------------------------------------------------------------------------------------------------
    if risk.score >= settings.risk_decline:
        result = BaselineResult(_decision(tx, Action.DECLINE, [ReasonCode.HIGH_RISK, *risk.reason_codes], risk), risk, [], {})
    elif risk.score >= settings.risk_review:
        result = BaselineResult(_decision(tx, Action.MANUAL_REVIEW, [ReasonCode.MEDIUM_RISK, *risk.reason_codes], risk), risk, [], {})
    elif tx.customer_type is CustomerType.NEW and amount_in_usd(tx) > settings.new_customer_review_usd:
        result = BaselineResult(_decision(tx, Action.MANUAL_REVIEW, [ReasonCode.NEW_CUSTOMER_HIGH_AMOUNT, *risk.reason_codes], risk), risk, [], {})
```

**Risk rules run before cost, so a risky payment is never routed cheaply.** Decline, then review, then the new-customer rule, then eligibility, then selection. The thresholds come from `config.py`, so the break-it segment can move them with env vars.

## Run it

Run from `Day31` in PowerShell. Paste the `$tx` hashtable once, then change fields for each path.

**Step 1**

```powershell
python -m pytest
```

**Expect:** 89 tests pass (33 new in `test_baseline.py`).

**Step 2**

```powershell
uvicorn main:app --reload
$tx = @{transaction_id="t-1"; timestamp="2026-01-05T09:12:00Z"; amount=85.5; currency="ILS"; country="IL"
  merchant_category="groceries"; customer_type="returning"; payment_method="card"
  customer_age_days=400; prior_chargebacks=0}
Invoke-RestMethod http://127.0.0.1:8000/decision/baseline -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

**Expect:** `action: route`, `selected_provider: epsilon_local_il`, reasons `LOW_RISK`, `CHEAPEST_ELIGIBLE`, `HIGHEST_APPROVAL_RATE`, fee 1.72, approval 0.9235, risk 0.0625. `beta_bank` rejected for `method_not_supported`.

**Step 3**

```text
$tx.customer_type="new"; $tx.customer_age_days=10; $tx.amount=2500; $tx.currency="USD"
$tx.country="US"; $tx.merchant_category="electronics"
Invoke-RestMethod http://127.0.0.1:8000/decision/baseline -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

**Expect:** `manual_review` with `NEW_CUSTOMER_HIGH_AMOUNT`. Risk is only 0.38, so the new-customer rule is what fired.

**Step 4**

```text
$tx.country="NG"; $tx.merchant_category="gaming"; $tx.amount=85.5; $tx.customer_age_days=5
$tx.prior_chargebacks=2; $tx.payment_method="wallet"
Invoke-RestMethod http://127.0.0.1:8000/decision/baseline -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

**Expect:** `decline` with `HIGH_RISK` and `PRIOR_CHARGEBACKS`, risk 0.7048. The components show country 0.2475 and chargebacks 0.16.

**Step 5**

```text
$tx = @{transaction_id="t-2"; timestamp="2026-01-05T09:12:00Z"; amount=60000; currency="USD"; country="US"
  merchant_category="groceries"; customer_type="returning"; payment_method="bank_transfer"
  customer_age_days=400; prior_chargebacks=0}
Invoke-RestMethod http://127.0.0.1:8000/decision/baseline -Method Post `
  -ContentType "application/json" -Body ($tx | ConvertTo-Json) | ConvertTo-Json -Depth 5
```

**Expect:** `manual_review` with `NO_ELIGIBLE_PROVIDER`. `rejected_providers` lists all six with a cause, including `delta_global: amount_above_limit`.

**Step 6**

```powershell
python -m scripts.compare_baseline
```

**Expect:** 10 example decisions, then `spearman_baseline_vs_hidden_risk: 0.87`, route 0.944 / manual_review 0.056, `fraud_captured_by_decline_or_review: 0.25`, `alpha_pay: 618`.

### Break it on purpose

#### 1 · A review threshold that reviews everything

Stop uvicorn, set `$env:RISK_REVIEW="0.05"`, start it again and resend the Israeli grocery payment. It now goes to `manual_review` with `MEDIUM_RISK` at a risk of 0.0625. Settings are read once at startup, so a running server doesn't see the change. Remove the variable with `Remove-Item Env:RISK_REVIEW`.

#### 2 · A decline rule nobody reaches

The summary shows **0 declines** in 1,000 payments and only 3 of 12 frauds stopped. Run `$env:RISK_DECLINE="0.40"; python -m scripts.compare_baseline`: declines rise to 3.5 % and fraud capture to 0.333. Better catch rate, more good customers turned away. This is a threshold question, and Days 36–38 answer it with an evaluation set instead of by feel.

```text
# config.py - thresholds live in one place, overridable per environment
risk_decline: float = float(os.getenv("RISK_DECLINE", "0.70"))
risk_review: float = float(os.getenv("RISK_REVIEW", "0.45"))
new_customer_review_usd: float = float(os.getenv("NEW_CUSTOMER_REVIEW_USD", "1000"))
```

> Rules are exact, repeatable and cheap, and they are still only as good as their thresholds. Measure them against the truth before you add a model on top, or you won't know what the model is adding.

## Cheat sheet

- **Baseline**: The simplest reasonable system you build first, so every smarter version has something to beat.
- **Rules engine**: Code that makes decisions with explicit conditions and thresholds, no learning and no LLM.
- **Eligibility**: Whether a provider is allowed to carry a payment at all: country, currency, method, amount limit, risk tolerance.
- **Hard constraint**: A rule that must hold every time. It filters options; it is never traded against cost.
- **Expected fee**: `amount × fee% + fixed fee` for one provider, in the transaction currency.
- **Approval estimate**: `base_rate × uptime × (1 − 0.4 × risk)`: the agent's guess at how likely the provider approves this payment.
- **Decision threshold**: A cut-off on the risk score, like 0.70 for decline and 0.45 for review. Business policy expressed as a number.
- **Spearman correlation**: How well two scores rank items in the same order, from −1 to 1. 0.87 means the baseline's risk ranks payments much like the hidden truth.
- **Fraud capture**: The share of actual frauds that ended in decline or manual review instead of being routed.
- **Template explanation**: A sentence built from reason codes and numbers with no model involved. It becomes the LLM's fallback on Day 32.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why do the risk rules run before eligibility and scoring?</summary><p>So a risky payment is declined or reviewed before cost enters the picture. It can never be routed just because a cheap provider exists.</p></details>
<details><summary>What happens when no provider is eligible?</summary><p>The engine returns <code>manual_review</code> with <code>NO_ELIGIBLE_PROVIDER</code> and lists every rejected provider with its cause. It never crashes and never guesses.</p></details>
<details><summary>Why does ONLY_ELIGIBLE_PROVIDER exist?</summary><p>With one candidate, it is trivially both the cheapest and the best approved. Saying "cheapest" would be true but misleading.</p></details>
<details><summary>The baseline has Spearman 0.87 but catches only 25 % of fraud. How can both be true?</summary><p>The ranking is good, but fraud is rare and the review threshold of 0.45 sits above most fraudulent payments' scores. It's a threshold problem, not a ranking problem.</p></details>
<details><summary>What can rules do better than an LLM in this project?</summary><p>Anything with an exact answer that must be repeatable and auditable: constraint filtering, fee arithmetic, threshold decisions and reason codes.</p></details>
</div>

**Next:** Day 32 – The LLM Second Opinion

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
