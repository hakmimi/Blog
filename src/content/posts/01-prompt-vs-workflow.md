---
title: "One big prompt or a workflow?"
description: "When is one long prompt enough, and when does a multi-step LLM workflow pay off? I measured it on made-up insurance claims."
pubDatetime: 2026-11-09T10:00:00+02:00
tags: ["workflows", "prompting", "evals"]
draft: true
---

<!--
HOW TO USE THIS FILE
- Each section has notes (in these comment blocks) with the key points and numbers from the README.
  Comments don't show on the site. Write your own text under each heading, then delete the notes.
- Drafts are hidden everywhere, even in the local preview. To preview: set draft: false,
  run `corepack pnpm@11.3.0 dev` in C:\Workshop\Blog, open the link it prints. Don't push until you're happy.
- Code and full results: https://github.com/hakmimi/ai-engineering-lab/tree/main/topics/01-prompt-vs-workflow
  (until the branch is merged, use .../tree/topic-01-prompt-vs-workflow/...)
-->

## The bottom line

<!--
- One well-written prompt beat the multi-step workflow on this job.
- When one prompt wasn't enough, a smarter model fixed it better than splitting the job did.
- Small table (easy / hard / cost / speed):
  one prompt, small model: 100% / 94% / cheapest / fast
  workflow, all steps:      94% / 70% / 4–5× more / 2.5× slower
  one prompt, bigger model: 100% / 96% / about 11× more / fastest
-->

## Why I looked into this

<!--
- Came across Anthropic's cookbook series; the post "Basic Multi-LLM Workflows" shows route, parallel and chain.
  Link: https://platform.claude.com/cookbook/patterns-agents-basic-workflows
- It shows how, not when. One long prompt is simple, cheap, fast; a workflow gives control but every call costs time, money, and is one more place to break.
- The question: when is one long prompt enough, and when does a structured workflow pay off?
-->

## The use case: insurance claims

<!--
- Why insurance: you know claims from the inside.
- A claim = short description + customer ID + attached documents.
- Outcomes: approve in full / in part, decline with a reason, ask for a specific document, hand to a person.
- Three made-up lines: car comprehensive, home water damage, travel (medical, cancellation).
- The workflow: route (what kind of claim?) → parallel (check every document at once) → chain (covered? exclusion? how much? — code does the math).
-->

![Claims intake flow: route, parallel document check, chain](../../assets/images/01-prompt-vs-workflow/process-diagram.png)

## What I built

<!--
- Made-up data: 3 policy wordings, 21 customers, 30 claims + 30 harder held-out claims, each with a known right answer.
- Five levels, each adds one step: 0 one big prompt, 1 + route, 2 + parallel document checks, 3 + chain with code math, 0+ one prompt on a bigger model.
- Every claim × 3 repeats, scored on: decision right, amount right, document problems caught, false alarms, time, cost.
- What I expected: the workflow more accurate, but more expensive and slower.
-->

## What happened

<!--
Main set:
- One prompt: 100% right, even on the small model.
- Workflow first try: 59–76%. Both bugs were glue: a router answer my code couldn't read, and a document rule each checker took word for word.
- After fixing: 94–99%, never beat one prompt. The fixes were tuned on the same claims, so it's a best case.
Hard set (never tuned on):
- One prompt 94%, routing 94%, + document checks 76%, full workflow 70%, bigger model 96%.
- Document checks hurt most (25–30% false alarms): a checker that sees one document takes the claim word for word ("the car was parked, so why a driver's license?").
- The chain can't answer "part of it": one excluded visit declined a whole medical claim.
- Good story material (cut from the README): the router wrote the right type in the wrong XML tag; my "must name the insured" rule failed on quotes that name an address; a parent's letter passed as proof of a child's illness (CAN-07).
-->

## Why the workflow lost

<!--
- Splitting a job doesn't make the model smarter. It makes each call see less.
- That helps when the job is too big or too mixed for one prompt; it hurts when a step needs context it no longer has.
- Every split adds glue (parsing, rules, hand-offs) — that's where most of the mistakes were.
- Still useful: routing cost almost nothing and didn't hurt; code doing the math keeps amounts exact and auditable.
-->

## When I'd use what

<!--
- One big prompt: when everything fits and the model can read it together. If it misses things you can test, try a bigger model first.
- Route: when types need very different rules, or the rules are too long for one prompt.
- Parallel: when checks are truly independent and each fits one short, exact rule.
- Chain: when you need to show each step, or the math must be exact — but watch for steps that need the full picture or a "part of it" answer.
- Rule of thumb: start with one prompt and a test set with known answers; split only the step you can show is failing; measure again.
-->

## Caveats

<!--
- Small, made-up data; one model family (OpenAI); 3 repeats.
- The answer key is my reading; two claims can be read two ways (water heater, friend's receipt).
- With real, long policies that don't fit one prompt, the workflow might win — that's the next test.
- Costs are tiny here (under $2 per 1,000 claims); the 4–5× difference matters at volume.
-->

## The code

<!--
- Link to the repo folder (see the note at the top).
- One line on what's there: the pipeline, the data, the tests, results.md built from real runs only.
-->
