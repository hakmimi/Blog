---
title: "One big prompt or a workflow?"
description: "When is one long prompt enough, and when does a multi-step LLM workflow pay off? I measured it on made-up insurance claims."
pubDatetime: 2026-11-09T10:00:00+02:00
tags: ["workflows", "prompting", "evals"]
draft: false
---

## The bottom line

**For this job, one well-written prompt beat the multi-step workflow. And when one prompt wasn't enough, a smarter model fixed it better than splitting the job did.**

I gave insurance claims to an AI in two ways. One way was a single big prompt ("here's everything, decide"). The other was a workflow that splits the job into small steps: sort the claim, check each document on its own, then decide step by step. Every answer was checked against right answers I wrote in advance.

| | Easy claims | Hard claims | Cost | Speed |
|---|---|---|---|---|
| **One big prompt** (small model) | **100%** right | **94%** | cheapest | fast |
| **Workflow, all steps** (small model) | 94% | 70% | 4–5× more | 2.5× slower |
| **One big prompt** (bigger model) | **100%** | **96%** | about 11× more | fastest |

**The lesson:** start with one prompt and a test set with known answers. Split the job only where you can show a step is failing, then measure again.

## Why I looked into this

I came across Anthropic's cookbook series on building with LLMs. One of the first posts, [Basic Multi-LLM Workflows](https://platform.claude.com/cookbook/patterns-agents-basic-workflows), shows three patterns for splitting a job across several model calls: **route**, **parallel** and **chain**.

The post shows *how* to build them. It doesn't say *when* they are worth it. That made me curious. A single long prompt is simple, cheap and fast. A workflow gives you more control, but every extra call costs time and money, and is one more place to break.

So the question was:

> **When is one long prompt enough, and when does a more structured workflow pay off?**

## The use case: insurance claims

I know insurance claims from the inside, so I picked that. A customer sends a claim: a short description, their customer ID and some attached documents. The system has to decide what happens next:

- **approve in full**, or **approve in part** (a cap, a private-provider rate, or part of the claim excluded)
- **decline**, with the reason (not covered, excluded, or no matching policy)
- **ask for documents**, naming exactly which one is missing or wrong
- **hand to a person**, when it can't tell what kind of claim it is

Three lines of business, all made up:

- **car comprehensive:** assessor's report, listed drivers, minimum driver age
- **home water damage:** water-damage add-on, slow leaks excluded, network vs private plumber
- **travel:** medical abroad, and trip cancellation

The workflow uses one pattern per step:

![Claims intake flow: route, parallel document check, chain](../../assets/images/01-prompt-vs-workflow/process-diagram.png)

## What I built

- **Simulated the data.** I wrote three short policy wordings for a made-up insurer, 21 customers with their policies, and two sets of 30 claims, each with its documents and a known right answer. The second set is harder, and I only used it at the end.
- **Built the full pipeline** in Python: an LLM router that decides the claim type, parallel document checks, and a step-by-step decision chain where plain code does the money math.
- **Ran every claim through five levels**, each one adding a step on top of the last, 3 times per level, and scored each answer against the key.

| Level | How a claim is handled | Calls per claim |
|---|---|---|
| **0** | One big prompt: all three policy wordings, the customer's policies, the claim and its documents. One answer. | 1 |
| **1** | **+ Route.** The model first decides the claim type, then a prompt with only that policy wording decides. | 2 |
| **2** | **+ Parallel.** Before deciding, one call per required document checks it, all at the same time. | about 5 |
| **3** | **+ Chain.** Covered? → any exclusion? → read the numbers. Code computes the amount. | about 6 |
| **0+** | Level 0 again, on a larger model. | 1 |

**How to read this table:** going down from level 0 to level 3 you add structure, one pattern at a time. If a pattern helps, accuracy should go up as you go down. If it doesn't, you pay more calls for nothing. Level 0+ asks a different question: is a smarter single call better than a workflow of cheaper calls?

Levels 0–3 use `gpt-6-luna` (a small, cheap model). Level 0+ uses `gpt-6.1-sol`. Prompt caching was on at every level.

Every answer was scored on: **decision right**, **amount right**, **document problems caught**, **false document alarms**, **time per claim** and **cost**.

**What I expected going in:** the workflow would be **more accurate**, especially on tricky claims, and would cost **more** and take **longer**. If it didn't beat one prompt, that's an answer too.

## What happened

### The main set

30 claims × 3 repeats per level. I ran the workflow once, found two bugs in it, fixed them, and ran levels 1–3 again.

| Level | Decision right | Amount right | Doc problems caught | False doc alarms | Time / claim | $ per 1,000 claims |
|---|---|---|---|---|---|---|
| 0 (gpt-6-luna) | **100%** | 100% | 100% | 0% | 3.0 s | $0.11* |
| 1, first try | 76% | 89% | 72% | 0% | 3.6 s | $0.13 |
| 2, first try | 60% | 80% | 33% | 28% | 5.0 s | $0.39 |
| 3, first try | 59% | 81% | 33% | 31% | 6.2 s | $0.46 |
| 1, fixed | 99% | 99% | 100% | 0% | 4.2 s | $0.12 |
| 2, fixed | 96% | 97% | 72% | 0% | 5.9 s | $0.43 |
| 3, fixed | 94% | 97% | 78% | 0% | 7.8 s | $0.53 |
| 0+ (gpt-6.1-sol) | **100%** | 100% | 100% | 0% | 2.9 s | $1.50 |

\* Level 0's cost here is a little low: it ran right after an identical run, so most of its prompt was already cached. With normal caching it's about $0.14.

- **One big prompt was right every time**, even on the small model. On these claims the workflow had nothing to fix.
- **The first try of the workflow was much worse (59–76%).** Both bugs were in the glue between steps: a router answer my code couldn't read, and a document rule each checker took word for word.
- **After fixing, the workflow came close (94–99%) but never beat one prompt.** Each narrow step adds its own chances to fail: the "is it covered?" step, for example, got a rule that's wrong for trip cancellations.
- **The workflow cost about 4–5× more and took about 2.5× longer.**

I tuned the fixes on these same 30 claims, so the "fixed" rows are a best case. That's why I built a second set.

### The hard set

30 new claims that **no prompt was tuned on**:

- longer documents and extra attachments: last year's assessor's report, a car registration named "license", a friend's receipt
- sums over many lines with no total
- numbers that conflict between documents
- facts buried in long text: who really drove, a corroded pipe, an old illness, the date of a call-up
- routing traps: a car flooded in a parking garage is a car claim, and a home flood found after a holiday is not a travel claim

| Level | Decision right | Amount right | Doc problems caught | False doc alarms | Time / claim | $ per 1,000 claims |
|---|---|---|---|---|---|---|
| 0 (gpt-6-luna) | **94%** | 93% | 89% | 4% | 3.5 s | $0.15 |
| 1 | **94%** | 94% | 89% | 6% | 5.4 s | $0.20 |
| 2 | 76% | 83% | 67% | 25% | 6.6 s | $0.55 |
| 3 | 70% | 80% | 67% | 30% | 7.7 s | $0.61 |
| 0+ (gpt-6.1-sol) | **96%** | 96% | 100% | 1% | 3.0 s | $1.76 |

- **Now one prompt does fail, but only a little (94%).** It missed a buried date once, and a friend's receipt split it every time (that claim can be read two ways).
- **Routing (level 1) didn't help or hurt.** It caught both routing traps, but added a call.
- **The narrow document checks hurt most (25–30% false alarms).** A checker that sees one document takes the claim word for word: a parked car "has no driver", so the license is "wrong".
- **The chain can't answer "part of it".** One excluded visit declined a whole medical claim, every time.
- **The bigger single model was the most accurate (96%) and the fastest**, at about 11× the small model's cost and 3× the workflow's.

## Why the workflow lost

- **Each small step sees only part of the claim.** A step that checks one document doesn't know the rest of the story ("the car was parked, so why is there a driver's license?"), so it flags things that are fine.
- **Every split adds more things to get right:** more prompts, more rules, more hand-offs between steps. Most of the mistakes happened there, not in the model's thinking. My first try of the workflow got only about 60% right, until I fixed two bugs in that glue.

Splitting a job doesn't make the model smarter. It makes each call see **less**. That helps when the full job is too big or too mixed for one prompt. It hurts when a step needs context it no longer has.

**What the workflow is still good for:**

- **Sorting claims by type (routing)** didn't hurt and cost almost nothing. It's useful when the rules are too long for one prompt.
- **Letting code do the math** keeps the amounts exact and easy to check.

## When I'd use what

| Option | Use it when… | Skip it when… |
|---|---|---|
| **One big prompt** | Everything the model needs (rules, documents) fits in one prompt and it can read it all together. Here it was the most accurate on the small model, the cheapest and the fastest. | It starts missing things you can name and test. Then try a **bigger model** first: one change, and here still the fastest option. |
| **Route** | Each type needs very different rules, or the full rule set is too long for one prompt. Here it cost almost nothing extra. | Everything already fits in one prompt. It adds a call and doesn't add accuracy. If you use it, read its answer forgivingly. |
| **Parallel** | The checks are truly independent, and each one fits in one short, exact rule, or speed across many documents matters. | A check needs the rest of the claim to judge it. One document alone led to 25–30% false alarms on the hard set. |
| **Chain** | You need to show each step, or the math must be exact and auditable, so code does it. | A step's short instructions leave out a rule the full text has, a step has to answer yes/no where the real answer is "part of it", or the outcome is a case the code can't express. |

**My rule of thumb:** start with one prompt and a small test set with known answers. Split only the step you can **show** is failing, and measure again.

## Caveats

- **Made-up data:** 3 short policy wordings and 30 + 30 claims. Real policies and files are much longer and messier, and that's where routing and splitting should start to pay off.
- **One model family** (OpenAI), and 3 repeats per level.
- **The answer key is one person's reading** (mine). Two claims can be read two ways (the water heater, the friend's receipt).
- **Prompt caching was on everywhere**, which helps the long single prompt the most. Cache warmth also depends on run order, so the hard-set costs are the fairer ones.
- **Costs are tiny here** (under $2 per 1,000 claims at every level). The workflow's 4–5× cost and 2–2.5× time only matter at real volume.

## What I'd improve next time

- Ask the API for a **fixed answer format** (structured output) instead of reading XML tags.
- Let the document check **see the whole claim**, or check all documents in one call.
- Let the chain answer **"partial because part is excluded"**.
- Build the **hard set first**, before any tuning, and keep it hidden until the end.
- Try **longer, real-size documents**, where one prompt should start to struggle. That's the next test.

## The code

Everything is on GitHub: [ai-engineering-lab / 01-prompt-vs-workflow](https://github.com/hakmimi/ai-engineering-lab/tree/topic-01-prompt-vs-workflow/topics/01-prompt-vs-workflow). It has the full pipeline in Python, the made-up data with its answer key, offline tests, and a results file built only from real runs.
