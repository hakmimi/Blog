---
title: "Day 30: Data With Hidden Truth"
description: "The decision agent gets its world: six payment providers, country and category risk tables, and 1,000 synthetic transactions with a hidden answer key. A loader serves the agent only what it is allowed to see."
series: "ai-engineering"
order: 32
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "numpy", "pandas", "seeded simulation", "data loader"]
readingTime: "8 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day30`](https://github.com/hakmimi/AIEngineering/tree/main/Day30). Layers touched: L1 Data.

## Goals

- **G1. Design reference data that makes routing a real trade-off.**  
  You can: explain why `zeta_budget` is cheapest but rarely the right answer.
- **G2. Generate realistic, reproducible transactions with hidden ground truth.**  
  You can: regenerate with seed 42 and show the same file hash and the same summary.
- **G3. Separate what the agent may see from what only the evaluator may see.**  
  You can: show `iter_transactions()` returning a `Transaction` without the four hidden columns.
- **G4. Put all file access behind a loader with typed errors.**  
  You can: delete the CSV and read the `DataStoreError` hint out loud.

## System map

Today the map grows on the data side. The generator writes three files; the loader reads them and strips the answer key. The Day 29 contract is the last gate before anything reaches the agent.

> Synthetic data → Data files (CSV/JSON) → Data loader → Decision agent context

<div class="ae-map" role="img" aria-label="scripts/generate_data.py calls simulation.py, which holds the six providers, the risk tables and generate_transactions with a seed. It writes providers.json, risk_tables.json and transactions.csv into data/. data_loader.py reads them with caching and typed errors; iter_transactions drops the four hidden columns and builds Day 29 Transaction objects. tests/test_data.py checks the generator and the loaders. The decision agent that will use this arrives on Day 31."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:897px" viewbox="0 0 1196 422" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">GENERATOR</text><text class="lane" x="264" y="18">L1 · DATA/</text><text class="lane" x="508" y="18">L1 · DATA_LOADER.PY</text><text class="lane" x="752" y="18">L4 · SCHEMAS.PY</text><text class="lane" x="996" y="18">CONSUMERS</text><path class="edge" d="M110,148 L110,168" marker-end="url(#mka)"></path><path class="edge" d="M200,212 C230,212 230,68 261,68" marker-end="url(#mka)"></path><path class="edge" d="M200,212 C230,212 230,160 261,160" marker-end="url(#mka)"></path><path class="edge" d="M200,212 C230,212 230,258 261,258" marker-end="url(#mka)"></path><path class="edge" d="M444,68 C474,68 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M444,160 C474,160 474,122 505,122" marker-end="url(#mka)"></path><path class="edge" d="M444,258 C474,258 474,220 505,220" marker-end="url(#mka)"></path><path class="edge" d="M688,220 C718,220 718,167 749,167" marker-end="url(#mka)"></path><path class="edge" d="M932,167 C962,167 962,126 993,126" marker-end="url(#mka)"></path><path class="edge-old" d="M932,167 C962,167 962,212 993,212" marker-end="url(#mkm)"></path><g class="node-new"><rect height="69" rx="8" width="180" x="20" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="112">generate_data.py</text><text class="ns s" text-anchor="middle" x="110" y="130">n rows · seed · summary</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="92">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="170"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="202">simulation.py</text><text class="ns s" text-anchor="middle" x="110" y="222">6 providers · risk tables</text><text class="ns s" text-anchor="middle" x="110" y="236">generate_transactions()</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="184">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="66">providers.json</text><text class="ns s" text-anchor="middle" x="354" y="85">fees · limits · max_risk</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="47">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="125"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="157">risk_tables.json</text><text class="ns s" text-anchor="middle" x="354" y="176">country + category risk</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="138">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="216"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="248">transactions.csv</text><text class="ns s" text-anchor="middle" x="354" y="267">1,000 rows</text><text class="ns s" text-anchor="middle" x="354" y="282">+ 4 hidden truth columns</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="229">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="508" y="80"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="112">load_providers()</text><text class="ns s" text-anchor="middle" x="598" y="130">cached · validated</text><text class="ns s" text-anchor="middle" x="598" y="146">DataStoreError + hint</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="92">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="508" y="186"></rect><text class="nt t" text-anchor="middle" x="598" y="218">iter_transactions()</text><text class="ns s" text-anchor="middle" x="598" y="236">hidden columns dropped</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="198">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="129"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="153">Transaction</text><text class="ns s" text-anchor="middle" x="842" y="172">Day 29 contract</text><text class="ns s" text-anchor="middle" x="842" y="187">extra=forbid</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="996" y="91"></rect><text class="nt t" text-anchor="middle" x="1086" y="123">tests/test_data.py</text><text class="ns s" text-anchor="middle" x="1086" y="142">21 tests · 56 in total</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="104">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="996" y="182"></rect><text class="nt t" text-anchor="middle" x="1086" y="206">Day 29 API</text><text class="ns s" text-anchor="middle" x="1086" y="225">/health · /events/validate</text></g><rect class="elbg" height="15" rx="3" width="53" x="204" y="218"></rect><text class="el" text-anchor="middle" x="230" y="229">seed 42</text><rect class="elbg" height="15" rx="3" width="78" x="435" y="222"></rect><text class="el" text-anchor="middle" x="474" y="233">drop hidden</text><text class="lane" style="fill:var(--ghost)" x="20" y="352">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="362"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="389">Day 31 · baseline decision engine</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="300" y="362"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="430" y="389">Day 32 · LLM on top of the rules</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Contracts with nothing to check

- `Transaction` and `Decision` exist, but there are no payments
- No providers, no fees, no risk tables
- Nothing to evaluate a decision against
- Five hand-written sample events only

### After this episode: A world with an answer key

- 6 providers with different fees, limits, countries and risk tolerance
- 1,000 seeded transactions in `data/transactions.csv`
- Hidden `simulated_risk_score`, `is_fraud`, `historical_provider`, `approved_outcome`
- `data_loader.py` hides storage and strips the hidden columns; 56 tests pass

> **Why it matters:** every evaluation from Day 31 on compares the agent's choices with the hidden truth in this file. If the agent could see that truth, every score would be a lie. If the data weren't seeded, no two runs could be compared.

## Code walkthrough

Four snippets from `Day30`. The first two build the world, the last two decide who is allowed to look at it.

### simulation.py · the provider contract

```python
class Provider(BaseModel):
    provider_id: str
    name: str
    supported_countries: list[str] | None = Field(description="ISO codes; null = worldwide")
    supported_currencies: list[Currency]
    supported_methods: list[PaymentMethod]
    fee_percent: float = Field(ge=0, le=20, description="Percent of the amount")
    fee_fixed: float = Field(ge=0, description="Fixed fee per transaction (transaction currency units)")
    base_approval_rate: float = Field(ge=0, le=1)
    max_amount: float = Field(gt=0)
    uptime: float = Field(ge=0, le=1, description="Share of time the provider is available")
    max_risk: float = Field(ge=0, le=1, description="Highest risk score the provider accepts")
    avg_latency_ms: int = Field(gt=0)
```

**Each provider is a set of constraints the rules engine will enforce.** `None` countries means worldwide. `max_risk` is the provider's risk tolerance, so a risky payment can be ineligible even when country, currency and method all fit. Day 31's eligibility rules read these fields one by one.

### simulation.py · the hidden truth

```python
# Hidden truth: latent risk grows with country/category risk, new customers, unusually large amounts, chargebacks.
amount_ratio = np.log(np.maximum(amount / median, 1e-3))
logit = (-3.0 + 3.2 * country_risk + 2.4 * cat_risk + 0.9 * (customer == "new") - 0.6 * (customer == "vip")
         + 0.35 * np.maximum(amount_ratio, 0) + 0.7 * chargebacks + rng.normal(0, 0.35, n))
true_risk = np.round(_sigmoid(logit), 4)
fraud = rng.random(n) < 0.35 * true_risk**2                                      # riskier => far more actual fraud (~1-3% overall)
```

**The answer key is a formula plus noise, and the noise matters.** Risk rises with country, category, newness, unusual amounts and chargebacks. The noise term means no rules engine can match it exactly. Fraud grows with the square of risk, so it stays rare, about 1 %.

### simulation.py · outcomes at a historical provider

```python
historical, approved = [], []
for row, r in zip(df.itertuples(index=False), true_risk, strict=True):
    candidates = [p for p in PROVIDERS if can_carry(p, row.country, row.currency, row.payment_method, row.amount)] or [PROVIDERS[3]]
    provider = candidates[int(rng.integers(0, len(candidates)))]
    p_ok = provider.base_approval_rate * (1 - 0.40 * r)
    historical.append(provider.provider_id)
    approved.append(bool(rng.random() < p_ok and not row.is_fraud))
df["historical_provider"], df["approved_outcome"] = historical, approved
```

**Every row gets a past provider and an outcome, like a real payments log.** The historical provider is picked at random among those that could carry the payment, with `delta_global` as the fallback. A fraudulent payment is never counted as approved.

### data_loader.py · what the agent may see

```python
HIDDEN_COLUMNS = ["simulated_risk_score", "is_fraud", "historical_provider", "approved_outcome"]
...
def iter_transactions(limit: int | None = None) -> Iterator[Transaction]:
    """Validated Transaction objects WITHOUT the hidden columns - exactly what the agent is allowed to see."""
    df = load_transactions()
    for row in df.head(limit).drop(columns=HIDDEN_COLUMNS).to_dict(orient="records"):
        yield Transaction(**row)
```

**The loader is the line between the evaluator and the agent.** `load_transactions()` returns everything, for analysis. `iter_transactions()` drops the answer key and builds validated `Transaction` objects. A test proves the hidden columns never come through.

## Run it

Run from `Day30` in PowerShell. The generator is deterministic, so the numbers on screen should match the README table.

**Step 1**

```powershell
python -m scripts.generate_data 1000 42
```

**Expect:** A JSON summary: `rows: 1000`, `fraud_rate: 0.012`, `approval_rate: 0.827`, `amount_median: 150.715`, NG at the top of `risk_by_country` (0.435). Then five sample rows including the hidden columns.

**Step 2**

```powershell
Get-Content data\transactions.csv -TotalCount 3
Get-Content data\providers.json -TotalCount 20
```

**Expect:** The CSV header with 14 columns, and the first provider, `alpha_pay`, with `supported_countries: null`.

**Step 3**

```powershell
python -c 'from data_loader import iter_transactions; print(next(iter_transactions()))'
```

**Expect:** `transaction_id='txn-42-00739'` with ten fields. No `simulated_risk_score`, no `is_fraud`.

**Step 4**

```text
(Get-FileHash data\transactions.csv).Hash
python -m scripts.generate_data 1000 42 | Out-Null
(Get-FileHash data\transactions.csv).Hash
```

**Expect:** The same hash twice. Seed 42 always builds the same world.

**Step 5**

```powershell
python -m pytest
```

**Expect:** `56 passed`: 35 from Day 29 plus 21 data tests (shape, seeds, valid rows, rates, loaders).

### Break it on purpose

#### 1 · Feed the answer key to the agent

Build a `Transaction` from a full CSV row, hidden columns included:
`python -c 'import data_loader as d; from schemas import Transaction; Transaction(d.load_transactions().iloc[0].to_dict())'`
Pydantic raises 4 validation errors\*\*, one `extra_forbidden` per hidden column. The Day 29 `extra="forbid"` rule is what makes a leak loud instead of silent.

#### 2 · Lose the data file

Rename `data\transactions.csv` and run the `iter_transactions` command again. You get `DataStoreError: transactions.csv not found - run python -m scripts.generate_data`. A typed error with the fix in the message, instead of a bare pandas traceback. Rename it back.

```python
def load_transactions() -> pd.DataFrame:
    try:
        return pd.read_csv(TRANSACTIONS_PATH)
    except FileNotFoundError as exc:
        raise DataStoreError("transactions.csv not found - run `python -m scripts.generate_data`") from exc
```

> Synthetic data is only useful if the agent can't peek at the answers. Hide the truth in one place, strip it in one place, and make the schema reject it if it ever slips through.

## Cheat sheet

- **Synthetic data**: Data generated by code to look like the real thing, with known rules behind it.
- **Ground truth**: The correct answer for each row. Here the hidden risk, fraud flag and approval outcome.
- **Seed**: The starting number for the random generator. Same seed, same data, every time.
- **Data leakage**: When the model or agent sees information it wouldn't have in real life, like the fraud label. Scores become meaningless.
- **Logit and sigmoid**: Add up weighted risk factors (the logit), then squash the sum into 0–1 with a sigmoid to get a probability.
- **Log-normal distribution**: A skewed distribution with many small values and a long tail of big ones. Payment amounts look like this.
- **Base approval rate**: How often a provider approves an ordinary payment before risk is taken into account.
- **Risk tolerance (max_risk)**: The highest risk score a provider accepts. Above it, the provider is not eligible.
- **Data loader**: The only module that reads data files. It validates, caches and hides the storage format from the agent.
- **lru_cache**: Python decorator that remembers a function's result. The reference tables are read from disk once.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Which four columns must the agent never see, and why do they exist at all?</summary><p><code>simulated_risk_score</code>, <code>is_fraud</code>, <code>historical_provider</code> and <code>approved_outcome</code>. They are the answer key used to evaluate the agent's own risk estimate and routing.</p></details>
<details><summary>What stops a hidden column from slipping into a decision?</summary><p><code>iter_transactions()</code> drops them, and <code>Transaction</code> has <code>extra="forbid"</code>, so a row that still carries them fails validation.</p></details>
<details><summary>Why CSV for transactions and JSON for providers?</summary><p>The 1,000-row flat table loads straight into pandas. Providers have nested lists (countries, currencies, methods), which fit JSON. The loader hides the choice from the agent.</p></details>
<details><summary>Why add noise to the hidden risk formula?</summary><p>Without it, a rules engine using the same factors could match the truth exactly. Noise makes the world messier than the agent's model, like real data.</p></details>
<details><summary>Name one assumption in this dataset you'd criticise.</summary><p>Any of: the world is generated by the same kind of model the agent uses, the risk numbers are plausible guesses, and there's no seasonality, velocity or device signal.</p></details>
</div>

**Next:** Day 31 – Rules Before Models

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
