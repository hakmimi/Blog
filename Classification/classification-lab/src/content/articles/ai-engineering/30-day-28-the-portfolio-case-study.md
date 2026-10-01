---
title: "Day 28: The Portfolio Case Study"
description: "From 28 folders of daily increments to one project a reviewer can understand in ten minutes: verified end to end, measured, and explained with its limits. No code changes today. This is the Month 1 deliverable: the architecture, the evidence, the interview story and the backlog for Month 2."
series: "ai-engineering"
order: 30
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "verification", "docs", "evaluation evidence"]
readingTime: "10 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day28`](https://github.com/hakmimi/AIEngineering/tree/main/Day28). Layers touched: L1 Data, L2 LLM, L3 Orchestration, L4 System.

## Goals

- **G1. Verify the whole system before presenting it.**  
  You can: run the tests with the coverage gate, the live smoke test and one real request, and say what was not verified.
- **G2. Present evaluation evidence instead of adjectives.**  
  You can: read the final results table and the "how the numbers improved" line from the README.
- **G3. Explain the design as decisions with measurements and known limits.**  
  You can: pick three rows from `ARCHITECTURE.md` and state the decision, the reason and the number behind it.
- **G4. Tell the story and plan what's next.**  
  You can: give the 2-minute explanation from `INTERVIEW.md` and name the top Month 2 backlog items.

## System map

This is the final Month 1 system, every part grey because it's all built. The new boxes are on the right: the documents that turn the code into a case study.

> Client → API → Guardrails → Graph Router → Memory / Retrieval / Tools → LLM → Output Guard → Logs + Cost → Response

<div class="ae-map" role="img" aria-label="The client calls the API, which applies the API key, rate limit, validation and the input guard. The LangGraph router sends the request through memory, retrieval or tools, then the LLM on OpenAI and the output guard, and the answer returns to the client. Logs, cost, tests and CI from Days 23 to 27 support it. The README now holds the final evaluation results. The regenerated graph.md, ARCHITECTURE.md, INTERVIEW.md and BACKLOG.md explain the system, its evidence, the interview story and the Month 2 plan."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 565" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">L4 · API</text><text class="lane" x="508" y="18">L1–L3 · GRAPH</text><text class="lane" x="752" y="18">L2 · MODEL</text><text class="lane" x="996" y="18">L4 · EVIDENCE</text><text class="lane" x="1240" y="18">CASE STUDY DOCS</text><path class="edge-old" d="M200,228 C230,228 230,228 261,228" marker-end="url(#mkm)"></path><path class="edge-old" d="M444,228 C474,228 474,228 505,228" marker-end="url(#mkm)"></path><path class="edge-old" d="M688,228 C718,228 718,186 749,186" marker-end="url(#mkm)"></path><path class="edge-old" d="M842,224 L842,243" marker-end="url(#mkm)"></path><path class="edge-old" d="M932,186 C962,186 962,174 993,174" marker-end="url(#mkm)"></path><path class="edge" d="M1086,212 L1086,232" marker-end="url(#mka)"></path><path class="edge" d="M688,228 C962,228 962,76 1237,76" marker-end="url(#mka)"></path><path class="edge" d="M1176,276 C1206,276 1206,182 1237,182" marker-end="url(#mka)"></path><path class="edge" d="M1176,276 C1206,276 1206,288 1237,288" marker-end="url(#mka)"></path><path class="edge" d="M1176,276 C1206,276 1206,386 1237,386" marker-end="url(#mka)"></path><path class="edge-back" d="M842,224 V447 H110 V261" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="197"></rect><text class="nt t" text-anchor="middle" x="110" y="221">Client</text><text class="ns s" text-anchor="middle" x="110" y="240">POST /rag/graph</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="190"></rect><text class="nt t" text-anchor="middle" x="354" y="214">API + input guard</text><text class="ns s" text-anchor="middle" x="354" y="232">key · rate limit · 422</text><text class="ns s" text-anchor="middle" x="354" y="248">injection rules</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="508" y="190"></rect><text class="nt t" text-anchor="middle" x="598" y="214">LangGraph router</text><text class="ns s" text-anchor="middle" x="598" y="232">memory · FAISS RAG · tools</text><text class="ns s" text-anchor="middle" x="598" y="248">fallback node</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="752" y="148"></rect><text class="nt t" text-anchor="middle" x="842" y="172">LLM + output guard</text><text class="ns s" text-anchor="middle" x="842" y="191">structured answer</text><text class="ns s" text-anchor="middle" x="842" y="206">numeric grounding</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="752" y="246"></rect><text class="nt t" text-anchor="middle" x="842" y="270">OpenAI</text><text class="ns s" text-anchor="middle" x="842" y="289">gpt-4.1-mini · embeddings</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="996" y="136"></rect><text class="nt t" text-anchor="middle" x="1086" y="160">logs · cost · CI</text><text class="ns s" text-anchor="middle" x="1086" y="180">tests + coverage</text><text class="ns s" text-anchor="middle" x="1086" y="194">Days 23–27</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="996" y="234"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="266">README results</text><text class="ns s" text-anchor="middle" x="1086" y="286">final eval · verification</text><text class="ns s" text-anchor="middle" x="1086" y="300">honest limits</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="248">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="1240" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="66">docs/graph.md</text><text class="ns s" text-anchor="middle" x="1330" y="85">regenerated, now with</text><text class="ns s" text-anchor="middle" x="1330" y="100">input/output guards</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="47">CHANGED</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="1240" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="172">ARCHITECTURE.md</text><text class="ns s" text-anchor="middle" x="1330" y="191">layers · decisions</text><text class="ns s" text-anchor="middle" x="1330" y="206">with evidence · limits</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="153">CHANGED</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="246"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="278">INTERVIEW.md</text><text class="ns s" text-anchor="middle" x="1330" y="297">2-min story · Q&amp;A</text><text class="ns s" text-anchor="middle" x="1330" y="312">5 CV bullets</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="259">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="1240" y="352"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="384">BACKLOG.md</text><text class="ns s" text-anchor="middle" x="1330" y="403">gaps → Month 2 plan</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="365">NEW</text></g><rect class="elbg" height="15" rx="3" width="34" x="214" y="210"></rect><text class="el" text-anchor="middle" x="230" y="222">JSON</text><rect class="elbg" height="15" rx="3" width="53" x="1090" y="211"></rect><text class="el" text-anchor="start" x="1092" y="222">numbers</text><rect class="elbg" height="15" rx="3" width="72" x="926" y="135"></rect><text class="el" text-anchor="middle" x="962" y="146">draw_graph</text><rect class="elbg" height="15" rx="3" width="181" x="386" y="440"></rect><text class="el" text-anchor="middle" x="476" y="451">answer + usage + request id</text><text class="lane" style="fill:var(--ghost)" x="20" y="495">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="505"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="532">Day 29 · payment-routing decision agent</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="300" y="505"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="430" y="532">Day 30 · synthetic business data</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: A working system with scattered proof

- Evidence spread across 27 READMEs: precision on Day 9, accuracy on Day 13, cost on Day 24
- `ARCHITECTURE.md` still described the end of Week 3, with no guardrails, cost or CI
- `docs/graph.md` was generated before the guard nodes existed
- No interview story, no CV bullets, no plan for what comes next

### After this episode: A case study a reviewer can follow

- README: one request-flow line, verification table, final eval results and honest limits
- `ARCHITECTURE.md`: layers, 10 design decisions each with its measurement, known limits
- `INTERVIEW.md`: the 2-minute explanation, likely questions with answers, 5 CV bullets
- `BACKLOG.md`: every gap tied to evidence and a next step for Month 2

> **Why it matters:** building something is half the job. The other half is making someone else believe it works, and that takes evidence, a clear design story and honesty about limits. The backlog written today is also the brief for Month 2.

## Code walkthrough

No application code changed today, so the snippets come from the case-study documents. Show them the same way: highlighted lines and one point each.

### README.md · the whole system in one line

```markdown
Client → API → Guardrails → Graph Router → Memory / Retrieval / Tools → LLM → Output Guard → Logs + Cost → Response
```

**If you can't draw it in one line, a reviewer won't hold it in their head.** Compare it with Day 1's `Client → API → Python function → LLM → Response`. Every box added since then is a day of this series.

### docs/ARCHITECTURE.md · decisions with evidence

```markdown
| Decision | Why | Evidence (measured on this project) |
|---|---|---|
| Refuse **before** the LLM when retrieval is weak | cheapest, safest hallucination control | 0 % hallucination on 12 unanswerable/adversarial/trap cases |
...
| Sibling-chunk expansion | the answer sentence is often in a neighbour chunk | eval accuracy 82 % → 100 % |
| One retry layer (`OPENAI_MAX_RETRIES=0` + tenacity) | stacked retries multiplied a failure from ~9 s to 25 s | live failure drills |
| Schema not repeated in the prompt | strict JSON schema is enforced by the API | −28 % input tokens, −16 % cost, same accuracy |
```

**Every row has three parts: what, why, and the number that proves it.** This table is what separates a portfolio project from a tutorial. Each number points back to a specific day you can show on request.

### docs/INTERVIEW.md · the 2-minute explanation

```markdown
> Each request goes through a LangGraph workflow. First, cheap deterministic guardrails and a router decide the cheapest
> safe path: greetings and arithmetic never touch a model, prompt-injection attempts are blocked before anything expensive
> runs. Knowledge questions are embedded and searched in a persisted FAISS index, re-ranked with topic and keyword signals,
> and if the evidence is weak the system refuses *before* calling the LLM - that is what kept hallucination at zero on my
> unanswerable and trap questions. After generation an output guard checks the answer contract and rejects numbers that
...
> with a request id, run 400 offline tests at 99 % coverage in CI, and evaluate with a judged 36-case set. The system
> is small and clean, so I treat the evaluation as regression safety rather than proof of scale."
```

**End the story with a limit. It makes everything before it more believable.** The story follows a request through the system and attaches one number to each layer. The last sentence heads off the obvious challenge before an interviewer raises it.

### docs/BACKLOG.md · gaps become the plan

```markdown
| Gap (evidence) | Next step |
|---|---|
| Eval set is small/easy; 100 % cannot rank systems (prompt v1 = v2) | 100+ cases incl. adversarial, held-out split, different judge model, human spot checks |
| Guardrails miss paraphrase / obfuscation / Hebrew (4 of 27 attack cases) | learned classifier or LLM guard behind the rules; keep false-positive test set |
| Docker + CI validated only by simulation | build and run the image; push and watch the first green run |
```

**A weakness with evidence and a next step is a plan, not an excuse.** Each gap cites how we know it's a gap. The first item for Month 2 is building the evaluation set before the agent, because this month's eval was built after and saturated at 100 %.

### docs/graph.md · regenerated with the guards

```markdown
	call_llm -.-> output_guard;
	...
	input_guard -.-> finish;
	input_guard -.-> load_memory;
	input_guard -.-> route_query;
	load_memory --> contextualize;
	output_guard --> finish;
	receive_query -.-> __end__;
	receive_query -.-> input_guard;
	...
	tool_answer -.-> output_guard;
```

**The diagram updated itself because we generated it on Day 21.** One command added the Day 25 guard nodes to the docs. `input_guard -.-> finish` is the blocked path that skips memory, retrieval and the LLM.

## Run it

Run from `Day28` in PowerShell. This is the reviewer's path through the README's Run section, done live.

**Step 1**

```powershell
pip install -r requirements-dev.txt
python -m pytest --cov=. --cov-fail-under=95
```

**Expect:** `400 passed`, coverage about 99 %, `Required test coverage of 95% reached`.

**Step 2**

```powershell
python -m scripts.e2e_smoke
```

**Expect:** 12 `OK` lines and `12/12 scenarios passed`: greeting, clarify, fact, comparison, refusal, both tools, 3-turn memory, 2 validation cases.

**Step 3**

```powershell
python -m scripts.draw_graph
```

**Expect:** `docs/graph.md` rewritten. Show `input_guard` and `output_guard` in the Mermaid preview.

**Step 4**

```powershell
python -m scripts.evaluate run final graph
```

**Expect:** The 22-case keyword eval through the full graph, saved as `data/eval/results_final.json` and `.csv`. The README's run: accuracy 1.00, hallucination 0.00, false refusal 0.00.

**Step 5**

```powershell
uvicorn main:app --reload
```

**Expect:** Server on port 8000 with JSON logs.

**Step 6**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Where is Masada?","session_id":"me"}' | ConvertTo-Json -Depth 6
```

**Expect:** One response that shows the month: `source: rag`, `graph.trace`, `timings`, `usage` with the estimated cost, and `session`. Point at each field and name the day it came from.

### Break it on purpose

#### 1 · A known bug that isn't in the limits

The case study lists its limits, but two bugs found in this series are still in the Day 28 code and not in `ARCHITECTURE.md` or `BACKLOG.md`. The output guard refuses any answer containing "rules:": run `python -c "from guardrails import check_output; print(check_output('Shabbat rules: most shops close on Saturday.', 0.9, 'x'))"` and see `prompt_leak`. The secret scanner flags phrases like `high-risk-transactions-for-manual-review`. A reviewer who finds these first will trust the rest less. Add them to the backlog.

```text
| Output guard: "rules:" leak marker refuses normal answers (Day 25) | drop the generic marker; add a regression test |
| Secret scan: `sk-` pattern matches words like "risk-..." (Day 27) | require no letter/digit before `sk-`; add a false-positive test |
```

#### 2 · A claim you can't back yet

The README shows a CI badge, and a CV bullet says the project shipped with "a coverage-gated GitHub Actions workflow and Docker packaging". The verification table says the workflow was **not yet observed on GitHub** and Docker was only simulated. Click the badge the way a reviewer would. Either push and get the first green run, and build the image once, or reword the bullet to say exactly what was verified.

> A portfolio is judged by its weakest claim. Verify what you can, label what you only simulated, and put every known bug in writing. The honesty is part of the evidence.

## Cheat sheet

- **Case study**: A write-up of a project as problem, design, evidence and limits, written for someone who wasn't there.
- **Verification**: Checking the system actually runs end to end, and recording which checks were real and which were simulated.
- **Design decision record**: A decision written down with its reason and the measurement behind it, like the table in `ARCHITECTURE.md`.
- **Evidence**: A number from this project that supports a claim, like precision 0.43 → 0.91 on Day 9.
- **Known limits**: What the system can't show or doesn't handle, stated up front.
- **Regression safety**: What a small eval set really gives you: it catches when a change makes things worse.
- **Saturated eval**: An evaluation where every version scores 100 %, so it can no longer tell good from better.
- **Backlog**: An ordered list of next steps, here each one tied to the evidence that it's needed.
- **Month 2 decision agent**: The next project: a payment-routing agent that decides route, manual review or decline, with reason codes.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>What improved quality most in Month 1, prompting or retrieval?</summary><p>Retrieval. Topic-aware ranking took precision from 0.43 to 0.91 (Day 9) and sibling-chunk expansion took accuracy from 82 % to 100 % (Day 13). Prompt v2 measured no better than v1.</p></details>
<details><summary>Why does the case study say 100 % accuracy doesn't prove much?</summary><p>The eval set is 22–36 easy cases on small, clean data. Everything scores 100 %, so it catches regressions but can't rank strong systems or show behaviour at scale.</p></details>
<details><summary>Which parts were verified by simulation only, and why say so?</summary><p>The Docker build and run, and the GitHub Actions workflow. Saying so keeps every other claim credible, and it puts "do the real run" at the top of the backlog.</p></details>
<details><summary>How does the system keep hallucination at 0 % on trap questions?</summary><p>Layers: refuse before the LLM when retrieval is weak, a grounded prompt, an output guard that rejects numbers absent from the sources, and trap questions in the eval set.</p></details>
<details><summary>What's the first rule for Month 2, and why?</summary><p>Build the evaluation set before the agent. In Month 1 the eval came after the system and saturated at 100 %, so it couldn't guide improvements.</p></details>
</div>

**Next:** Day 29 – Design Before Code

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
