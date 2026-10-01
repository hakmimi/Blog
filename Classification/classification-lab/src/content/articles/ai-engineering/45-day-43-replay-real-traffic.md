---
title: "Day 43: Replay Real Traffic"
description: "Until now we judged the agent one test case at a time. Today we fire 100 realistic events at the running API, record route, decision, latency and cost for each one, and learn how it behaves as a service."
series: "ai-engineering"
order: 45
date: 2026-10-01
keywords: ["ai engineering", "payment routing agent", "httpx", "traffic mix", "latency p95", "cost"]
readingTime: "10 min read"
---

Part of the **payment routing agent** arc. Code for this day: [`Day43`](https://github.com/hakmimi/AIEngineering/tree/main/Day43). Layers touched: L1 Data, L4 System.

## Goals

- **G1. Generate a labelled traffic mix: routine events plus injected card testing, anomalies, policy violations and edge cases.**  
  You can: show `build_events()` output and explain why the `scenario` label never reaches the API.
- **G2. Drive the real HTTP server with a client that records one row per request.**  
  You can: run `scripts.simulate --spawn` and open the CSV it writes.
- **G3. Read a run like an operator: latency percentiles, route mix, LLM share and cost per decision.**  
  You can: explain why p95 is 2.7 s while requests without an LLM take about 8 ms.
- **G4. Check each injected scenario against a business expectation.**  
  You can: read the `Scenario checks` section and say what a FAILED line would mean.

## System map

The agent itself doesn't change today. Everything new sits around it: a traffic generator on the left, an HTTP client in front of the API, and a results store with an analysis on the right.

> Event Generator → API Client → Decision API → Results Store → Analysis

<div class="ae-map" role="img" aria-label="traffic.py builds 100 labelled events from the synthetic-world generator plus injected scenarios. scripts/simulate.py optionally spawns uvicorn with its own AUDIT_DB_PATH, waits for /health, then posts each event to POST /decision with an X-Request-ID. The decision graph runs tools, rules, policy, fast path and the LLM review against OpenAI and writes the audit record. The client stores one row per event as JSON and CSV. analyze_simulation.py reads the run and returns latency, routes, cost and per-scenario checks to you."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 443" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">TRAFFIC</text><text class="lane" x="264" y="18">CLIENT</text><text class="lane" x="508" y="18">DECISION API</text><text class="lane" x="752" y="18">AGENT (DAYS 31–42)</text><text class="lane" x="996" y="18">EXTERNAL</text><text class="lane" x="1240" y="18">RESULTS</text><path class="edge-old" d="M110,193 L110,212" marker-end="url(#mkm)"></path><path class="edge" d="M200,64 C230,64 230,114 261,114" marker-end="url(#mka)"></path><path class="edge" d="M200,257 C230,257 230,114 261,114" marker-end="url(#mka)"></path><path class="edge" d="M354,164 L354,184" marker-end="url(#mka)"></path><path class="edge" d="M444,114 C474,114 474,121 505,121" marker-end="url(#mka)"></path><path class="edge" d="M444,228 C474,228 474,216 505,216" marker-end="url(#mka)"></path><path class="edge-old" d="M688,121 C718,121 718,125 749,125" marker-end="url(#mkm)"></path><path class="edge" d="M688,216 C718,216 718,216 749,216" marker-end="url(#mka)"></path><path class="edge-old" d="M932,125 C962,125 962,166 993,166" marker-end="url(#mkm)"></path><path class="edge" d="M932,125 C1084,125 1084,104 1237,104" marker-end="url(#mka)"></path><path class="edge" d="M1330,146 L1330,166" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,270 V325 H110 V98" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="34"></rect><text class="nt t" text-anchor="middle" x="110" y="58">You</text><text class="ns s" text-anchor="middle" x="110" y="77">PowerShell</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="20" y="117"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="141">simulation.py</text><text class="ns s" text-anchor="middle" x="110" y="160">synthetic-world generator</text><text class="ns s" text-anchor="middle" x="110" y="175">(Day 30)</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="215"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="247">traffic.py</text><text class="ns s" text-anchor="middle" x="110" y="266">build_events(n, seed, mix)</text><text class="ns s" text-anchor="middle" x="110" y="281">84% routine + 4 scenarios</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="228">NEW</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="264" y="62"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="94">scripts/simulate.</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="112">py</text><text class="ns s" text-anchor="middle" x="354" y="132">waits for /health</text><text class="ns s" text-anchor="middle" x="354" y="146">X-Request-ID sim-&lt;seed&gt;-&lt;i&gt;</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="76">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="186"></rect><text class="nt t" text-anchor="middle" x="354" y="218">--spawn server</text><text class="ns s" text-anchor="middle" x="354" y="238">uvicorn on :8765</text><text class="ns s" text-anchor="middle" x="354" y="252">own AUDIT_DB_PATH</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="200">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="508" y="83"></rect><text class="nt t" text-anchor="middle" x="598" y="107">POST /decision</text><text class="ns s" text-anchor="middle" x="598" y="126">API key · rate limit</text><text class="ns s" text-anchor="middle" x="598" y="141">same endpoint as Day 34+</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="508" y="181"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="213">config.py</text><text class="ns s" text-anchor="middle" x="598" y="232">AUDIT_DB_PATH override</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="194">CHANGED</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="87"></rect><text class="nt t" text-anchor="middle" x="842" y="111">Decision graph</text><text class="ns s" text-anchor="middle" x="842" y="130">tools · rules · policy</text><text class="ns s" text-anchor="middle" x="842" y="145">fast path · LLM review</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="185"></rect><text class="nt t" text-anchor="middle" x="842" y="209">Audit store</text><text class="ns s" text-anchor="middle" x="842" y="228">SQLite, one db per run</text></g><g class="node-external"><rect height="76" rx="8" width="180" x="996" y="128"></rect><text class="nt t" text-anchor="middle" x="1086" y="152">OpenAI</text><text class="ns s" text-anchor="middle" x="1086" y="172">gpt-4.1-mini</text><text class="ns s" text-anchor="middle" x="1086" y="186">≈ 2 s per review</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="62"></rect><text class="nt t" text-anchor="middle" x="1330" y="94">run1.json + .csv</text><text class="ns s" text-anchor="middle" x="1330" y="114">one row per event</text><text class="ns s" text-anchor="middle" x="1330" y="128">route · latency · cost</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="76">NEW</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="1240" y="168"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="200">analyze_simulatio</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="218">n.py</text><text class="ns s" text-anchor="middle" x="1330" y="238">p50 · p95 · cost</text><text class="ns s" text-anchor="middle" x="1330" y="252">scenario checks</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="182">NEW</text></g><rect class="elbg" height="15" rx="3" width="110" x="175" y="72"></rect><text class="el" text-anchor="middle" x="230" y="83">--n 100 --seed 7</text><rect class="elbg" height="15" rx="3" width="46" x="207" y="168"></rect><text class="el" text-anchor="middle" x="230" y="179">events</text><rect class="elbg" height="15" rx="3" width="110" x="419" y="100"></rect><text class="el" text-anchor="middle" x="474" y="111">POST, one by one</text><rect class="elbg" height="15" rx="3" width="27" x="461" y="205"></rect><text class="el" text-anchor="middle" x="474" y="216">env</text><rect class="elbg" height="15" rx="3" width="59" x="1055" y="98"></rect><text class="el" text-anchor="middle" x="1084" y="109">response</text><rect class="elbg" height="15" rx="3" width="46" x="697" y="318"></rect><text class="el" text-anchor="middle" x="720" y="329">report</text><text class="lane" style="fill:var(--ghost)" x="20" y="373">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="246" x="20" y="383"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="143" y="410">Day 44 · async API handling</text></g><g class="node-ghost"><rect height="44" rx="8" width="238" x="286" y="383"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="405" y="410">Day 45 · queue and workers</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Judged one case at a time

- The evaluation set (Days 36–38) is small and deliberately adversarial
- Latency and cost were measured per decision, never over a stream
- Nobody had sent the running HTTP server a realistic mix of traffic
- Every run wrote into the same `data/audit.db`

### After this episode: Judged as a service

- `traffic.py` builds a seeded mix: 84% routine, 16% injected bad or odd events
- `scripts/simulate.py` sends them over HTTP and stores one row per request as JSON and CSV
- `analyze_simulation.py` reports p50/p95 latency, route mix, LLM share and cost per decision
- Each injected scenario is checked against what the business expects, and each run gets its own audit db

> **Why it matters:** a test suite tells you whether a decision is right. A traffic run tells you what the service costs and how fast it is at the rate real events arrive. Run1 shows throughput is capped by the LLM (0.75 requests per second in sequence), and that finding drives the next two episodes.

## Code walkthrough

Four snippets: the traffic generator, the client loop, the spawned server, and the scenario checks.

### traffic.py · the mix

```python
DEFAULT_MIX = {"routine": 0.84, "card_testing": 0.04, "anomalous_amount": 0.03, "policy_violation": 0.05, "edge_case": 0.04}
HIDDEN = ["simulated_risk_score", "is_fraud", "historical_provider", "approved_outcome"]
...
    routine = generate_transactions(n, seed=seed, end=now).drop(columns=HIDDEN).to_dict(orient="records")
    scenarios = rng.choices(list(mix), weights=list(mix.values()), k=n)
    events = []
    for i, scenario in enumerate(scenarios):
        if scenario == "routine":
            event = {**routine[i], "transaction_id": f"sim-{i:04d}"}
        else:
            event = _special(scenario, i, rng, now - timedelta(minutes=i))
        events.append({"scenario": scenario, "event": event})
```

**The label travels next to the event, never inside it.** The API sees only `event`. The `scenario` label stays in the client so the analysis can grade the answer later. The hidden truth columns from Day 30 are dropped, so the agent can't cheat.

### scripts/simulate.py · one row per request

```python
for i, item in enumerate(build_events(n, seed)):
    started = time.perf_counter()
    try:
        response = client.post("/decision", json=item["event"], headers={"X-Request-ID": f"sim-{seed}-{i:04d}"})
        wall_ms = (time.perf_counter() - started) * 1000
        body = response.json() if response.status_code == 200 else {}
        ...
    except httpx.HTTPError as exc:
        rows.append({"i": i, "scenario": item["scenario"], "transaction_id": item["event"]["transaction_id"], "status": 0,
                     "error": type(exc).__name__, "wall_ms": round((time.perf_counter() - started) * 1000, 1)})
```

**A failed request is a row too.** The request id links each row to the server logs and the audit record. Network errors become status 0 and the loop keeps going. Note the headers: only a request id. Remember that for the break-it segment.

### scripts/simulate.py · --spawn

```python
if args.spawn:
    port = 8765
    base_url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "AUDIT_DB_PATH": str(OUT_DIR / f"{args.label}_audit.db"), "PYTHONUNBUFFERED": "1"}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level", "warning"],
                              cwd=str(Path(__file__).resolve().parent.parent), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
```

**The simulator starts its own server with its own audit database.** That's why `config.py` changed today: `audit_db_path` now reads `AUDIT_DB_PATH`. The child process inherits your whole environment plus that one override, which matters in the break-it.

### scripts/analyze_simulation.py · expectations

```python
EXPECTATIONS = {
    "policy_violation": lambda r: r["action"] in ("decline", "manual_review") and "POLICY_BLOCK" in (r.get("reason_codes") or ""),
    "edge_case": lambda r: r["action"] == "manual_review" and (r.get("route") == "fallback" or "POLICY_BLOCK" in (r.get("reason_codes") or "")),
    "card_testing": lambda r: r["action"] in ("manual_review", "decline"),
    "anomalous_amount": lambda r: r["action"] in ("manual_review", "decline"),
}
...
def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * q))], 1) if ordered else 0.0
```

**A business rule, written as a check on a row.** Routine traffic has no expectation because any action can be right. The injected scenarios do, so the report can say `3/3 handled as expected` or list the ids that failed.

## Run it

Run from `Day43` in PowerShell with the venv active. The live run takes about two minutes, so start it and talk over the progress lines.

**Step 1**

```powershell
python -c "from collections import Counter; from traffic import build_events; print(Counter(e['scenario'] for e in build_events(100, seed=7)))"
```

**Expect:** A Counter dominated by `routine` (87 for seed 7), with a handful of each injected scenario.

**Step 2**

```powershell
python -m scripts.simulate --label run2 --n 100 --seed 8 --spawn
```

**Expect:** `sent 20/100` … `sent 100/100`, then `done: 100 events in … s -> data/simulation/run2.json`.

**Step 3**

```powershell
python -m scripts.analyze_simulation run2
```

**Expect:** The Markdown report: events and audit share, server latency avg/p50/p95/max, LLM vs no-LLM latency, cost, decisions and routes, then `Scenario checks` and `Slowest requests`.

**Step 4**

```text
Import-Csv data\simulation\run2.csv |
  Sort-Object { [double]$_.server_ms } -Descending |
  Select-Object -First 5 transaction_id, scenario, action, llm_status, server_ms
```

**Expect:** The five slowest rows. In run1 all of them were LLM-reviewed.

**Step 5**

```powershell
python -m pytest tests/test_simulation_traffic.py -q
```

**Expect:** `16 passed`. The server is replaced by `httpx.MockTransport`, so this costs nothing.

### Break it on purpose

#### 1 · The client forgets the API key

Set `$env:APP_API_KEY = "demo-key"` and run `python -m scripts.simulate --label locked --n 10 --spawn`. The spawned server inherits the variable, so `require_api_key` returns **401** for every request. The simulator never sends `X-API-Key`, so all rows get status 401 and `run()` still says `done`. Then `python -m scripts.analyze_simulation locked` crashes with `StatisticsError: mean requires at least one data point`, because `analyze()` averages the latencies of zero successful requests. Two real bugs: the client ignores the key the server may require, and the analysis has no guard for an all-failed run. Remove the variable with `Remove-Item Env:APP_API_KEY` afterwards.

```text
# scripts/simulate.py: send the key when one is configured
headers = {"X-Request-ID": f"sim-{seed}-{i:04d}"}
if settings.app_api_key:
    headers["X-API-Key"] = settings.app_api_key
response = client.post("/decision", json=item["event"], headers=headers)

# scripts/analyze_simulation.py: an all-failed run is a result, not a crash
if not ok:
    return {"events": len(rows), "succeeded": 0, "failed": len(rows), "statuses": dict(Counter(r.get("status") for r in rows))}
```

#### 2 · No server at all

Run `python -m scripts.simulate --label down --n 5` without `--spawn` and without a server on port 8000. `wait_until_healthy` polls `/health` for 30 seconds and raises `RuntimeError: the server did not become healthy in time`. That's the good kind of failure: loud, early, and before any rows are written.

> A load test is a client like any other, and it has to speak the server's full contract, including auth. When it doesn't, the numbers it produces are about the wrong thing, or there are no numbers at all.

## Cheat sheet

- **Traffic simulation**: Sending a realistic stream of events to the running service to measure how it behaves as a whole.
- **Traffic mix**: The share of each kind of event in the stream. Here 84% routine and 16% injected scenarios.
- **Injected scenario**: A deliberately bad or unusual event (card testing, sanctions, unknown country) mixed into normal traffic.
- **Seed**: The number that fixes the random generator, so the same seed always produces the same 100 events.
- **p50 / p95**: The latency that half the requests beat, and the latency that 95% of requests beat. p95 shows the slow tail.
- **Server vs wall latency**: Server latency is measured inside the API. Wall latency is measured by the client and includes the network and HTTP overhead.
- **Throughput**: Requests finished per second. Run1 managed about 0.75 in sequence.
- **Request ID**: The `X-Request-ID` header (`sim-<seed>-<i>`) that ties one client row to the server logs and audit record.
- **Scenario check**: A rule per injected scenario that says which actions are acceptable, for example every policy violation must carry `POLICY_BLOCK`.
- **Isolated audit db**: `AUDIT_DB_PATH` points each simulation at its own SQLite file so test runs never mix with real audit records.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why does the <code>scenario</code> label stay out of the event sent to the API?</summary><p>It's the answer key. If the API saw it, the agent could be graded on information it would never have in production. The client keeps it to check the result afterwards.</p></details>
<details><summary>Run1 had average latency 1,257 ms but p50 1,628 ms. How can the median be higher than the mean?</summary><p>The distribution has two groups: about a third of requests take a few milliseconds (fast path, policy, fallback) and two thirds take about 2 s with an LLM review. The fast group drags the mean below the median.</p></details>
<details><summary>Why does <code>--spawn</code> set <code>AUDIT_DB_PATH</code>?</summary><p>So 100 simulated decisions go into <code>data/simulation/&lt;label&gt;_audit.db</code> and don't mix with the real audit trail in <code>data/audit.db</code>.</p></details>
<details><summary>What limits throughput to about 0.75 requests per second, and what would you try first?</summary><p>Waiting on the LLM, one request at a time. Our code takes milliseconds. Sending requests concurrently is the first lever, which is Day 44's topic.</p></details>
<details><summary>If <code>APP_API_KEY</code> is set, what happens to a simulation run with the current code?</summary><p>Every request gets 401 because <code>simulate.py</code> never sends <code>X-API-Key</code>. The run still finishes, and <code>analyze_simulation</code> then crashes on <code>statistics.mean</code> of an empty list.</p></details>
</div>

**Next:** Day 44

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
