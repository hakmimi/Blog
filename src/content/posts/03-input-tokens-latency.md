---
title: "Fewer input tokens, faster answers? Testing the advice on real contracts"
description: "Anthropic's latency guide says input tokens cost time. I tested its four input-token levers on 60 real NDAs with OpenAI models. They saved money and bytes, but not seconds."
pubDatetime: 2026-11-09T16:00:00+02:00
tags: ["latency", "caching", "evals"]
draft: true
---

## The bottom line

**On OpenAI, from my home connection, the input-token levers saved money and bytes, not seconds.** Caching cut the cost of a chat by 80–85%. Keeping the chat on the server cut each upload from 397 KB to 1.3 KB. But the first word didn't come any sooner. Reading the prompt took about 0.4 s per 100K tokens on the small model, and that is less than the normal swings of the network and the API.

| Claim | Article (Claude) | Me (OpenAI, home connection) | Holds? |
|---|---|---|---|
| A bigger prompt = a slower first word | +0.25 s per 100K tokens | small model +0.39 s, large model **+1.04 s** per 100K | **Yes**, and more on the large model |
| Caching cuts cost | −85% | −80% (1 NDA), **−85%** (30 NDAs) | **Yes** |
| Caching speeds up a long prompt | turn 2: 1.7 s → 0.5 s | 1.20 s off, 1.56 s on | **No** |
| Pre-warming speeds up the first turn | 1.0 s → 0.8 s | 1.31 s cold, 1.64 s warmed | **No** |
| Server keeps the chat | 22.3 MB → 0.3 KB, 1.27 s → 0.63 s | **397 KB → 1.3 KB**, 1.14 s → 1.06 s | **Bytes yes, speed no** |

**The lesson:** turn caching on for the money. For speed, measure first. On my setup, **thinking and the network cost more time than reading.**

## Why I looked into this

Anthropic's cookbook has a guide called [Latency Optimization on the Claude API](https://platform.claude.com/cookbook/latency-optimization-latency-optimization#input-token-management). Its "input token management" section starts from a simple idea: **the model reads every input token before it writes the first word.** So send fewer tokens, and don't send the same ones twice.

It tests four levers and gives numbers for each. But the numbers are for Claude, on a made-up insurance desk, measured on Anthropic's own network.

> **Are these general rules about input tokens, or Claude facts?**

So I took the four claims and ran them on the stack I actually use: OpenAI models, real documents, my home connection.

## The use case: an NDA desk

I reused the 60 real NDAs from [part 2 of the prompt-vs-workflow series](/Blog/posts/02-prompt-vs-workflow-real-contracts/), with their lawyer-written labels.

A legal team keeps a **pack of NDAs** open and asks one question per chat turn:

> "Contract C07: may the receiving party share the information with its employees?"

The model answers with a label (says it / says the opposite / not mentioned) and the sentence numbers that prove it. So **every answer can be checked**, and "faster" can't quietly mean "worse".

The contracts are the big, fixed part of the prompt (about 79K tokens for 30 NDAs). The questions are small and change every turn. That's exactly the shape where caching should shine.

**Data credit.** The contracts and labels come from **ContractNLI** (Koreeda & Manning, 2021, [stanfordnlp.github.io/contract-nli](https://stanfordnlp.github.io/contract-nli/)), released under **CC BY 4.0**.

## What I built

Each claim became a before/after test: one setting changes, everything else stays the same.

| Test | Claim | What changes |
|---|---|---|
| **0** | (baseline) | Nothing: a tiny prompt, to see my network floor |
| **1** | A bigger prompt = a slower first word | Prompt size: 20K / 43K / 83K / 151K tokens, never cached |
| **2** | Caching cuts cost, and speeds up long prompts | Cache-friendly vs cache-busting prompt, on 1 NDA and on 30 NDAs, 17-turn chats |
| **3** | Pre-warming speeds up the first turn | First question cold vs right after a warm-up call |
| **4** | A server-side chat cuts upload time | Re-send the whole chat vs `previous_response_id` |

Each lever has an OpenAI version, and they are **close, not the same**:

- **Caching** is automatic on OpenAI. "Off" means putting a random line at the very start of the prompt, so nothing matches.
- **Pre-warming:** OpenAI has no zero-token request, so the warm-up is a tiny request with the shared start.
- **Message threads** become `previous_response_id`: the server keeps the conversation, and I send only the new question.

How I measured:

- A **streaming timer**: the clock starts just before the request, and "first word" is the first piece of answer text.
- Variants **take turns** (A, B, A, B…), so a slow minute on my connection hits both.
- **No hidden retries:** a rate-limit error is retried outside the clock.
- Medians, and a simple bootstrap interval for every difference.
- Models: `gpt-6-luna` (small) everywhere, and `gpt-6.1-sol` (large) in test 1.

## What happened

### My network floor is about 0.9 s

A tiny prompt took **0.89 s** to the first word (p90 1.78 s), twice the article's floor. And now and then a call took 4–10 s for no reason in the request. Keep that in mind for everything below.

### Prompt size: yes, but it depends on the model

| Model | 20K tokens | 43K | 83K | 151K | Slope |
|---|---|---|---|---|---|
| `gpt-6-luna` (small) | 1.87 s | 1.11 s | 2.58 s | 1.74 s | +0.39 s per 100K |
| `gpt-6.1-sol` (large) | 1.49 s | 1.32 s | 1.54 s | 2.81 s | **+1.04 s per 100K** |

- **The large model shows it clearly:** 1.5 s → 2.8 s from 20K to 151K tokens. That's **four times** the article's +0.25 s per 100K.
- **The small model barely shows it.** Its slope is +0.39 s, but the line jumps around (one 83K call took 9.7 s). Reading is cheap there, and the noise is bigger than the reading.

### Caching: the money claim holds, the speed claim doesn't

17-turn chats, cache on vs off:

| Pack | Variant | First word, turns 2–17 | Read from cache | $ per chat |
|---|---|---|---|---|
| 1 NDA (~3K tokens) | off | 0.96 s | 0% | $0.0050 |
| 1 NDA | **on** | 1.08 s | 92% | **$0.0010** |
| 30 NDAs (~79K tokens) | off | 1.20 s | 0% | $0.1354 |
| 30 NDAs | **on** | 1.56 s | 94% | **$0.0209** |

- **Cost: −80% and −85%.** That matches the article almost exactly.
- **Speed: no gain.** On the big pack the difference was within noise (interval −0.06 to +1.05 s). On the small pack, cache-on was even **a little slower** (+0.12 s, interval +0.01 to +0.24 s). I don't know why. My guess: the cache key sends a whole chat to one machine, which may queue.
- The article itself says short tasks don't get faster. What I didn't expect was the **long** pack not getting faster either.

### Pre-warming: the cache was warm, and it still didn't help

My first warm-up **never worked**: 0 of 10 questions read from cache. The warm-up sent the contract pack plus "Reply with OK.", and OpenAI only reused the cache when a new prompt **started with the whole earlier prompt**. A warm-up that sent the pack alone worked every time.

After that fix: **10 of 10** questions read the pack from cache, and the first word was **1.31 s cold vs 1.64 s warmed** (interval −1.29 to +1.16 s). No gain I can measure.

### The server-side chat: a big cut in bytes, not in time

| Variant | Request size, turns 2–17 | First word, turns 2–17 |
|---|---|---|
| Re-send the whole chat | 397 KB | 1.14 s |
| `previous_response_id` | **1.3 KB** | 1.06 s |

The upload shrank by 99.7%, and the first word stayed the same (interval −0.21 to +0.18 s). **0.4 MB of text is nothing for a home upload link.** The article's win came from 22 MB of page images.

### Quality stayed level

Label right was 60–80% in every variant, with no variant consistently ahead. 7 of 442 answers in test 2 broke the answer format, and I count them as wrong. (The labels are lower than part 2's 82% because thinking was off and each question sits inside a 30-contract pack. Here accuracy is a guard rail between variants, not a score.)

## Why the levers didn't show up as speed

- **Reading is cheap on the small model.** About 0.4 s per 100K tokens, so caching 79K tokens can save at most ~0.3 s.
- **My network and the API swing more than that.** A 0.9 s floor, and single calls at 4–10 s.
- **Thinking costs more than reading.** At reasoning effort "low", the small model sometimes thought for 30–340 tokens, which added **0.5–4 s** to the first word. I ran everything at the lowest effort each model accepts, and that was the biggest latency lever I touched.

## Gotchas the runs caught

- **OpenAI's cache needs the whole earlier prompt as the start.** A warm-up must send the shared start and nothing after it.
- **"Random" isn't random if you seed it.** A re-run with the same seed reused the last run's "fresh" first lines, and OpenAI still had them cached 8 minutes later. My report has a "cold check" that flags any cold request that read from cache, and it caught this.
- **Re-sending an 80K-token chat every turn hits rate limits.** Test 4 hit the 2M tokens-per-minute limit 4 times.
- **Use medians.** One request in the pre-warm re-run stalled for about two hours. The median didn't move.

## When I'd use what

| Lever | Article | Me (OpenAI, small model, home connection) | So… |
|---|---|---|---|
| **Fewer tokens** | +0.25 s per 100K | +0.4 s (small), +1 s (large) per 100K | Matters on large models and tight budgets (voice). On a small model, fix thinking and the network first. |
| **Caching** | −85% cost, faster long prompts | −80–85% cost, **not** faster | **Always on.** It's automatic on OpenAI: just keep the prompt start stable. Do it for the money. |
| **Pre-warming** | 0.2 s faster first turn | No gain | Skip it on a small model. If you do it, send exactly the shared start. |
| **Server keeps the chat** | Big win with images | Bytes down 99.7%, time the same | Use it for images, PDFs or slow uplinks. For text chats it saves bandwidth, not time. |
| **Lowest thinking effort** | (other section of the article) | Up to 4 s saved | **The first thing I'd check.** |

## Caveats

- **One machine, one home connection, one day.** Network noise is part of what I measured. From a cloud machine, the reading time would stand out more.
- **OpenAI, not Claude.** The levers are close, not the same.
- **Caching and pre-warming ran on the small model only** (cost). The large model reads slower (+1 s per 100K), so that's where caching could show a speed-up.
- **Small samples:** 5 + 3 rounds in test 1, 10 + 3 chats in test 2, 10 repetitions in test 3, 3 chats in test 4.
- **My long pack is 79K tokens,** not the article's 146K.

Total cost of the whole topic: **about $3.55**.

## What I'd try next

- Run caching and pre-warming on the **large model**, where reading is slow enough to save.
- Run the same tests **from a cloud machine** to take my home network out.
- Run them **on Claude**, to see whether the article's numbers hold on its own stack.
- Add **page images** to the pack, where the server-side chat should finally save time.

## The code

Everything is on GitHub: [ai-engineering-lab / 03-input-tokens-latency-contract-nli](https://github.com/hakmimi/ai-engineering-lab/tree/main/topics/03-input-tokens-latency-contract-nli). It has the streaming timer, the five tests, offline tests, the design and plan, and a results file built only from real runs.
