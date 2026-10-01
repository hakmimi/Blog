---
title: "Day 13: The Evaluation Loop"
description: "From \"the answers look fine to me\" to a repeatable evaluation: 22 labelled questions, deterministic scoring, JSON and CSV results. The first run finds two real weaknesses, two general fixes close them, and a second run proves it: accuracy 82 % → 100 %."
series: "ai-engineering"
order: 15
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "eval set", "scoring", "error analysis"]
readingTime: "11 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day13`](https://github.com/hakmimi/AIEngineering/tree/main/Day13). Layers touched: L1 Data, L2 LLM, L4 System.

## Business problem

Every AI product ships with a quiet promise: "the answers are good." In a normal software team that promise is backed by tests. In an LLM system most of the interesting behaviour is not deterministic, so teams fall back on eyeballing a few answers and calling it fine.

That works until the first prompt tweak, model upgrade or retrieval change. Nobody can say whether quality went up or down, so every change is a gamble, and nobody can show a customer or a manager evidence that the system works. Real AI teams therefore keep an **evaluation harness**: a fixed set of questions with known-good outcomes, a scoring step, and a report that can be compared run to run. It is the AI equivalent of a regression suite, and it is the component most beginner projects are missing.

## Goals

- **G1. Define what quality means for this assistant as numbers.**  
  You can: explain accuracy, retrieval hit rate, hallucination rate and false refusal rate in one sentence each.
- **G2. Build an eval set that includes traps as well as easy questions.**  
  You can: name the six case types and say why "unanswerable in domain" matters most.
- **G3. Run the loop: evaluate, read failures, fix, re-run, compare.**  
  You can: run `evaluate.py run` and `compare v1 v2` and read the deltas aloud.
- **G4. Explain the two fixes the data pointed to.**  
  You can: show `expand_with_siblings` and the `wide` margin, and link each to the failing cases it fixed.

## System map

The runtime path is the Day 12 system with two retrieval fixes. The big new piece sits outside it: an evaluation harness that drives the system with labelled questions and scores what comes back.

> Eval set → System → Scoring → Results (JSON + CSV) → Weaknesses → Fix → Re-run → Compare

<div class="ae-map" role="img" aria-label="evaluate.py reads data/eval/eval_set.json and sends each question to the system, either get_rag_answer or run_pipeline. The RAG path routes, retrieves with FAISS, cuts by margin (wide 0.30 for complex questions), expands each retrieved document with its sibling chunks up to 8, and calls the LLM. score_case checks retrieved topics, required keywords and refusals; summarize computes accuracy, hit rate, hallucination and false refusal rates and latency percentiles. Results are saved as JSON and CSV and two runs can be compared."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 386" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">L1 · EVAL DATA</text><text class="lane" x="264" y="18">L4 · EVALUATE.PY</text><text class="lane" x="508" y="18">L3 · SYSTEM UNDER TEST</text><text class="lane" x="752" y="18">L1 · RETRIEVAL.PY</text><text class="lane" x="996" y="18">L4 · SCORING</text><text class="lane" x="1240" y="18">OUTPUT</text><path class="edge" d="M200,138 C230,138 230,92 261,92" marker-end="url(#mka)"></path><path class="edge" d="M444,92 C474,92 474,96 505,96" marker-end="url(#mka)"></path><path class="edge-old" d="M598,131 L598,150" marker-end="url(#mkm)"></path><path class="edge" d="M688,96 C718,96 718,76 749,76" marker-end="url(#mka)"></path><path class="edge" d="M842,118 L842,137" marker-end="url(#mka)"></path><path class="edge" d="M932,191 C962,191 962,85 993,85" marker-end="url(#mka)"></path><path class="edge" d="M1086,127 L1086,146" marker-end="url(#mka)"></path><path class="edge" d="M1176,191 C1206,191 1206,96 1237,96" marker-end="url(#mka)"></path><path class="edge-back" d="M1330,138 V268 H110 V183" marker-end="url(#mkg)"></path><g class="node-new"><rect height="84" rx="8" width="180" x="20" y="96"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="110" y="128">eval_set.json</text><text class="ns s" text-anchor="middle" x="110" y="147">22 cases · 6 types</text><text class="ns s" text-anchor="middle" x="110" y="162">incl. traps</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="192" y="109">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="50"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="82">run &lt;label&gt;</text><text class="ns s" text-anchor="middle" x="354" y="102">rag | multistep</text><text class="ns s" text-anchor="middle" x="354" y="116">times each case</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="64">NEW</text></g><g class="node-new"><rect height="69" rx="8" width="180" x="264" y="156"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="188">compare &lt;a&gt; &lt;b&gt;</text><text class="ns s" text-anchor="middle" x="354" y="208">metric deltas</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="170">NEW</text></g><g class="node-changed"><rect height="69" rx="8" width="180" x="508" y="62"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="94">get_rag_answer()</text><text class="ns s" text-anchor="middle" x="598" y="113">complex route → wide=True</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="75">CHANGED</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="508" y="153"></rect><text class="nt t" text-anchor="middle" x="598" y="177">router · LLM · memory</text><text class="ns s" text-anchor="middle" x="598" y="196">Days 6–12 (unchanged)</text></g><g class="node-changed"><rect height="84" rx="8" width="180" x="752" y="34"></rect><text class="nt t" text-anchor="middle" x="842" y="66">wide margin</text><text class="ns s" text-anchor="middle" x="842" y="85">0.30 instead of 0.12</text><text class="ns s" text-anchor="middle" x="842" y="100">for comparisons</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="47">CHANGED</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="752" y="140"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="172">expand_with_sibli</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="842" y="190">ngs</text><text class="ns s" text-anchor="middle" x="842" y="209">add the doc's other chunks</text><text class="ns s" text-anchor="middle" x="842" y="224">cap 8 · flag expanded</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="924" y="153">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="43"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="75">score_case()</text><text class="ns s" text-anchor="middle" x="1086" y="94">retrieval_hit · keywords</text><text class="ns s" text-anchor="middle" x="1086" y="109">· refusal · passed</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="56">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="996" y="149"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="181">summarize()</text><text class="ns s" text-anchor="middle" x="1086" y="200">accuracy · hallucination</text><text class="ns s" text-anchor="middle" x="1086" y="215">· false refusal · p50/p95</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="162">NEW</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="1240" y="54"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1330" y="86">results_&lt;label&gt;</text><text class="ns s" text-anchor="middle" x="1330" y="106">.json + .csv</text><text class="ns s" text-anchor="middle" x="1330" y="120">failures printed</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1412" y="68">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="160"></rect><text class="nt t" text-anchor="middle" x="1330" y="184">OpenAI API</text><text class="ns s" text-anchor="middle" x="1330" y="204">~22 answer calls per run</text></g><rect class="elbg" height="15" rx="3" width="66" x="198" y="98"></rect><text class="el" text-anchor="middle" x="230" y="109">questions</text><rect class="elbg" height="15" rx="3" width="187" x="626" y="261"></rect><text class="el" text-anchor="middle" x="720" y="272">read failures → fix → re-run</text><text class="lane" style="fill:var(--ghost)" x="20" y="316">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="260" x="20" y="326"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="150" y="353">Day 14 · project consolidation</text></g><g class="node-ghost"><rect height="44" rx="8" width="174" x="300" y="326"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="387" y="353">Day 20 · LLM judge</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Quality by gut feeling

- Day 9 measured retrieval, but nothing scored the **answers**
- No test for questions the system should refuse, like facts missing from the data
- Adaptive top-k could cut the chunk that held the answer, and nobody noticed
- Comparison questions often retrieved only one side

### After this episode: Quality as a number you can move

- `evaluate.py run <label>` scores 22 cases and saves `results_<label>.json` and `.csv`
- Metrics: accuracy, retrieval hit rate, keyword score, hallucination rate, false refusal rate, latency p50/p95
- `expand_with_siblings` adds a document's other chunks; complex routes use a `wide` 0.30 margin
- v1 → v2: accuracy 0.818 → 1.000, comparisons 0 → 1, false refusals 0.125 → 0

> **Why it matters:** so far every change was tested for behaviour. Nothing measured quality. Without an eval you can't tell if a prompt tweak helped or hurt, and you can't show anyone the system works. The eval also found problems no unit test could: the answer sat in a chunk the cutoff removed.

## Design decisions

- **Deterministic scoring first, no LLM judge.** Keyword groups and refusal markers are crude, but they give the same result every run and cost nothing. An LLM judge comes later (Day 20), once there is a baseline to compare it against.
- **Traps in the eval set.** The most valuable questions are the ones the system is tempted to answer but shouldn't, like the population of a city that appears in the data without that fact. Without them, a system that always answers scores perfectly.
- **Two failure rates, not one.** Hallucination (answering what should be refused) and false refusal (refusing what should be answered) pull in opposite directions. Tracking only one lets you "improve" by moving to the other extreme.
- **General fixes, not case-specific hacks.** The error analysis pointed at two mechanisms (a cutoff that dropped the chunk holding the answer, and comparisons that kept only one side). The fixes change those mechanisms, behind environment toggles so they can be switched off.

## Code walkthrough

Four snippets from `Day13`: two from the harness, two from the fixes it led to.

### evaluate.py · scoring one case

```python
def score_case(case: dict, result: dict, latency_ms: float) -> dict:
    topics = [c.get("topic") for c in result.get("retrieved_chunks", [])]
    refused = is_refusal(result.get("answer"))
    kw = keyword_score(result.get("answer"), case["must_include"])
    passed = refused if case["should_refuse"] else (not refused and kw == 1.0)
    ...
            "retrieval_hit": retrieval_hit(topics, case["expected_topics"], case["topic_match"]),
```

**A pass means different things for different questions.** For a trap question, passing means refusing. For a normal one, it means answering and hitting every keyword group. Retrieval hit is scored separately, so you can tell a retrieval miss from an answer miss.

### evaluate.py · the metrics

```python
        "accuracy": round(sum(r["passed"] for r in rows) / len(rows), 3),
        ...
        "hallucination_rate": round(sum(not r["refused"] for r in unanswerable) / max(len(unanswerable), 1), 3),
        "false_refusal_rate": round(sum(r["refused"] for r in answerable) / max(len(answerable), 1), 3),
        "retrieval_hit_rate": round(sum(hits) / max(len(hits), 1), 3),
        ...
        "latency_p50_ms": round(statistics.median(lat), 1),
        "latency_p95_ms": round(lat[min(len(lat) - 1, int(len(lat) * 0.95))], 1),
```

**Two failure modes, two separate numbers.** A system that refuses everything has zero hallucinations. A system that answers everything has zero false refusals. You only see the trade-off if you track both.

### retrieval.py · fix 1: sibling chunks

```python
def expand_with_siblings(chunks: list[dict], store: VectorStore) -> list[dict]:
    ...
    for anchor in chunks:                                   # chunks are already best-first
        doc_id = anchor["doc_id"]
        if doc_id in seen:
            continue
        seen.add(doc_id)
        for meta in sorted(by_doc.get(doc_id, [anchor]), key=lambda m: m["chunk_id"]):
            ...
            out.append({**meta, "similarity": source["similarity"], "score": source["score"] if is_anchor else anchor["score"],
                        "expanded": not is_anchor})
    return out[:settings.max_context_chunks]
```

**If the right document was found, give the model the whole document.** Chunks are about 30 words, so "How do visitors reach Masada?" matched one chunk while the cable car sentence sat in the next. Siblings are added in document order and flagged `expanded`, so you can see what retrieval found and what was added.

### rag.py + retrieval.py · fix 2: wide margin

```python
# rag.py
        chunks = get_relevant_chunks(question, route.top_k, filters, wide=route.name == RAG_COMPLEX)

# retrieval.py
    anchors = faiss_search(query_embedding, query, top_k, filters, settings.complex_margin if wide else None)
    if settings.expand_siblings and anchors:
        anchors = expand_with_siblings(anchors, get_store())
```

**A comparison needs both sides, even if one scores lower.** The Day 9 cutoff kept chunks within 0.12 of the best one. For "Compare Tel Aviv and Haifa" that often dropped Haifa. Complex routes now use 0.30. Both fixes are env toggles, which makes the break-it easy.

## Run it

Run from `Day13` in PowerShell. A full run takes about half a minute; keep the output scrolling on screen, then zoom into the summary.

**Step 1**

```powershell
python -m pytest tests -q
```

**Expect:** `130 passed`, including 13 new tests in `test_evaluation.py`. All offline.

**Step 2**

```powershell
python evaluate.py run v3
```

**Expect:** 22 `PASS` / `FAIL` lines with case id and type, then the summary JSON with `accuracy`, `hallucination_rate`, `false_refusal_rate`, `latency_p50_ms` and `by_type`.

**Step 3**

```powershell
python evaluate.py compare v1 v2
```

**Expect:** One line per metric: accuracy 0.818 → 1.0, false_refusal_rate 0.125 → 0.0, retrieval_hit_rate 0.944 → 1.0.

**Step 4**

```powershell
Invoke-Item data\eval\results_v3.csv
```

**Expect:** The CSV opens in Excel: one row per case with `answer`, `refused`, `retrieval_hit`, `keyword_score`, `passed`, `latency_ms`.

**Step 5**

```powershell
python evaluate.py run v3_multi multistep
```

**Expect:** The same 22 cases through the Day 10 pipeline. Compare its latency p50 with the RAG run.

### Break it on purpose

#### 1 · Switch the fixes off

Run `$env:EXPAND_SIBLINGS="0"; $env:COMPLEX_SCORE_MARGIN="0.12"`, then `python evaluate.py run v2_off` and `python evaluate.py compare v2 v2_off`. The comparison and sibling cases fail again and accuracy drops back toward the v1 level. This is the eval as a regression alarm: if someone "simplifies" retrieval later, the numbers say so. Clean up with `Remove-Item Env:EXPAND_SIBLINGS, Env:COMPLEX_SCORE_MARGIN`.

#### 2 · A typo that lies in the report

Run `python evaluate.py run v4 multi-step` (with a hyphen). `get_system` only checks for `"multistep"`, so any other name silently runs the plain RAG path, but the summary saves `"system": "multi-step"`. You now have a results file that claims to be the pipeline and isn't. Validate the name.

```python
SYSTEMS = ("rag", "multistep")

def get_system(name: str):
    if name not in SYSTEMS:
        raise SystemExit(f"unknown system '{name}', use one of {SYSTEMS}")
    ...
```

> An evaluation is only as honest as its setup. 22 cases that were used to find and to verify the fixes can overstate the result, and a mislabelled run can mislead you. Keep the set growing, keep a held-out part, and make the harness fail loudly.

## What went wrong

The harness itself had a hole. `evaluate.py run v4 multi-step` (with a hyphen) silently ran the plain RAG path, because the system lookup only checked for the exact name `multistep`, yet the saved summary still said `"system": "multi-step"`. The result was a report that claimed to measure the pipeline and measured something else. The fix is to validate the name and fail loudly.

The bigger caveat is the headline number. 82% → 100% on 22 cases that were used both to find and to verify the fixes is overfitting in miniature. Treat it as a proof that the loop works, not as a quality guarantee.

## Cheat sheet

- **Evaluation set**: A fixed list of questions with expected outcomes, here 22 cases in `data/eval/eval_set.json`.
- **Accuracy**: Share of cases passed. What "pass" means depends on whether the case should be refused.
- **Retrieval hit rate**: Share of cases where the expected topic was retrieved: any of them, or all of them for comparisons.
- **Keyword score**: Share of required keyword groups found in the answer. Each group is any-of, so synonyms can pass.
- **Hallucination rate**: Share of should-refuse questions that got an answer instead of a refusal.
- **False refusal rate**: Share of answerable questions the system refused. The opposite failure to hallucination.
- **Unanswerable in domain**: A trap: the topic exists in the data but the fact doesn't, like the population of Tel Aviv.
- **Error analysis**: Reading the failed cases (retrieved topics, answer, keyword score) to find the cause before changing code.
- **Neighbour expansion**: Adding the other chunks of a retrieved document so a split-off answer sentence isn't lost.
- **p50 / p95 latency**: The median and the 95th-percentile response time. p95 shows the slow tail users actually notice.
- **Overfitting the eval**: Tuning on the same cases you report on. The 100 % here needs a held-out split and more cases to be trusted.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why track hallucination rate and false refusal rate separately?</summary><p>They pull in opposite directions. Refusing everything gives zero hallucinations; answering everything gives zero false refusals. Only both together show the real balance.</p></details>
<details><summary>v1 retrieved the right topic for "How do visitors reach Masada?" but still failed. Why?</summary><p>The answer sentence was in a sibling chunk of the same document, and the adaptive cutoff dropped it. The model saw the topic but not the fact, and said the context didn't provide it.</p></details>
<details><summary>How does the wide margin help comparison questions?</summary><p>For <code>rag_complex</code> routes the cutoff keeps chunks within 0.30 of the best score instead of 0.12, so the lower-scoring second item in a comparison survives.</p></details>
<details><summary>Why should you be careful with the 100 % accuracy result?</summary><p>22 cases is small, and the same cases were used to find and verify the fixes. Keyword scoring can also miss paraphrases. A bigger set, a held-out split and an LLM judge (Day 20) are the next steps.</p></details>
<details><summary>expand_with_siblings caps the output at 8 chunks. What could go wrong in a comparison?</summary><p>Chunks are grouped by document in rank order before the cap. If the first document has 8 or more chunks, the second document is cut entirely, and the comparison loses a side again.</p></details>
</div>

**Next:** Day 14 – One System, One Story

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
