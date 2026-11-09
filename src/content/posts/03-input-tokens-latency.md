---
title: "Fewer input tokens, faster answers?"
description: "Anthropic's latency guide says input tokens cost time, and shows four levers to cut them. I tested all four on 60 real NDAs with OpenAI models, from my home connection. They saved money and bytes, but not seconds."
pubDatetime: 2026-11-05T10:00:00+02:00
tags: ["latency", "caching", "evals"]
source: ["anthropic"]
draft: false
---

Almost everything I build sends the model a big, fixed block of text (rules, documents) and a small question that changes. If the model has to read that whole block before it writes a word, the block is slowing me down on every single call.

That's the starting point of the "input token management" section in Anthropic's guide [Latency Optimization on the Claude API](https://platform.claude.com/cookbook/latency-optimization-latency-optimization#input-token-management): **the model reads every input token before it writes the first word.** So send fewer tokens, and don't send the same ones twice. The guide has numbers, but they're for Claude, on Anthropic's network. I use OpenAI models, from home. Would the same levers make my answers come faster?

## Four levers, timed on Claude

The guide tests four levers on a made-up insurance desk, each with a before/after number:

1. **Fewer tokens.** A bigger prompt means a slower first word: about **+0.25 s per 100K tokens**.
2. **Prompt caching.** Keep the start of the prompt the same, and the model doesn't re-read it. Cost drops by about **85%**, and on a long prompt the second turn's first word goes from **1.7 s to 0.5 s**.
3. **Pre-warming.** Send a cheap request with the shared start before the user asks, so the cache is ready. The first turn goes from **1.0 s to 0.8 s**.
4. **Let the server keep the chat.** Instead of re-sending the whole conversation each turn, send only the new message. In their example, the upload drops from **22.3 MB to 0.3 KB** (the chat had page images), and the first word from **1.27 s to 0.63 s**.

The message: **trim and cache your input, and your users wait less.**

The guide is careful about one thing: short prompts don't get faster from caching. The speed win is for **long** prompts.

But every number is **Claude, on Anthropic's own network**. Are these rules about input tokens in general, or facts about one stack? The guide can't tell us.

## The same levers, from my desk

### What I timed

**Do the four input-token levers make the first word come sooner on OpenAI models, from a normal home connection, on real documents? And do they keep the answers just as good?**

### 60 NDAs, again

I reused the **60 real NDAs** from my [prompt-vs-workflow post](/Blog/posts/01-prompt-vs-workflow/), with their lawyer-written labels from **ContractNLI**.

The job is an **NDA desk**. A legal team keeps a pack of NDAs open and asks one question per chat turn:

> "Contract C07: may the receiving party share the information with its employees?"

The model answers with a label (says it / says the opposite / not mentioned) and the sentence numbers that prove it. So **every answer can be checked**, and "faster" can't quietly mean "worse".

The contracts are the big, fixed part of the prompt: about **79K tokens** for a 30-NDA pack. The questions are small and change every turn. That's exactly the shape where caching should shine.

### One lever per test

Each claim became a before/after test. One setting changes, everything else stays the same:

- **Test 0 · the floor.** A tiny prompt, to see how fast my connection can possibly be.
- **Test 1 · prompt size.** 20K / 43K / 83K / 151K tokens, never cached.
- **Test 2 · caching.** 17-turn chats, cache-friendly vs cache-busting, on 1 NDA and on 30 NDAs.
- **Test 3 · pre-warming.** The first question cold, vs right after a warm-up call.
- **Test 4 · server keeps the chat.** Re-send the whole chat, vs OpenAI's `previous_response_id`.

Each lever has an OpenAI version, and they're **close, not the same**:

- **Caching** is automatic on OpenAI. "Off" means putting a random line at the very start of the prompt, so nothing matches.
- **Pre-warming:** OpenAI has no zero-token request, so the warm-up is a tiny request with the shared start.
- **The server-side chat** is `previous_response_id`: the server keeps the conversation, and I send only the new question.

Models: `gpt-6-luna` (small) everywhere, and `gpt-6.1-sol` (large) in test 1, both at the lowest thinking effort each one accepts.

## The stopwatch

| What I measure | In plain words |
|---|---|
| ⏱️ **First word** | Seconds from sending the request to the first word of the answer. The main number |
| 📈 **Slope** | Extra first-word seconds for every 100K more input tokens |
| ♻️ **Read from cache** | How much of the input the model didn't have to read again |
| 📦 **Upload size** | How many bytes each request sends |
| 💰 **Cost** | Dollars per 17-question chat |
| ✅ **Label right** | Answer quality against the lawyers' labels. A guard rail, so speed can't hide worse answers |

**What Anthropic's guide suggests:** bigger prompts are slower, and caching, pre-warming and a server-side chat each give a clear speed-up on long prompts.

**What I expected** (my guesses before running anything):

- **Bigger prompts would be slower**, roughly like the guide says.
- **Caching would cut the cost** a lot, and **speed up the 30-NDA chats**, since that pack is long.
- **Pre-warming and the server-side chat would help a little**, maybe less than on Claude, because my home network adds its own delay.

## Cheaper, not faster

All numbers are medians. "First word" is the time to the first piece of answer text.

### Test 0 · my floor is about 0.9 s

A tiny prompt took **0.89 s** to the first word (slow tail 1.78 s), twice the guide's floor. And now and then a call took **4–10 s** for no reason in the request. Keep that in mind for everything below.

### Test 1 · bigger prompts: yes, but it depends on the model

| Model | 20K tokens | 43K | 83K | 151K | Slope |
|---|---|---|---|---|---|
| `gpt-6-luna` (small) | 1.87 s | 1.11 s | 2.58 s | 1.74 s | +0.39 s per 100K |
| `gpt-6.1-sol` (large) | 1.49 s | 1.32 s | 1.54 s | 2.81 s | **+1.04 s per 100K** |

- **The large model shows it clearly:** 1.5 s → 2.8 s. That's **four times** the guide's +0.25 s per 100K.
- **The small model barely shows it.** The line jumps around (one 83K call took 9.7 s). Reading is cheap there, and the noise is bigger than the reading.

### Test 2 · caching: the money claim holds, the speed claim doesn't

| Pack | Cache | First word, turns 2–17 | Read from cache | $ per chat |
|---|---|---|---|---|
| 1 NDA (~3K tokens) | off | 0.96 s | 0% | $0.0050 |
| 1 NDA | **on** | 1.08 s | 92% | **$0.0010** |
| 30 NDAs (~79K tokens) | off | 1.20 s | 0% | $0.1354 |
| 30 NDAs | **on** | 1.56 s | 94% | **$0.0209** |

- **Cost: −80% and −85%.** Almost exactly the guide's number.
- **Speed: no gain, even on the long pack.** The difference was within noise (interval −0.06 to +1.05 s).
- On the small pack, cache-on was even **a little slower** (+0.12 s). I don't know why. My guess: the cache sends a whole chat to one machine, which may queue.

### Test 3 · pre-warming: the cache was warm, and it still didn't help

My first warm-up **never worked**: 0 of 10 questions read from cache (more on that below). After the fix, **10 of 10** did, and the first word was **1.31 s cold vs 1.64 s warmed** (interval −1.29 to +1.16 s). No gain I can measure.

### Test 4 · server keeps the chat: a big cut in bytes, not in time

| Variant | Upload, turns 2–17 | First word, turns 2–17 |
|---|---|---|
| Re-send the whole chat | 397 KB | 1.14 s |
| `previous_response_id` | **1.3 KB** | 1.06 s |

The upload shrank by **99.7%**, and the first word stayed the same (interval −0.21 to +0.18 s). **0.4 MB of text is nothing for a home upload link.** The guide's win came from 22 MB of page images.

### Quality stayed level

Label right was **60–80%** in every variant, with no variant consistently ahead. 7 of 442 answers in test 2 broke the answer format, and I count them as wrong. (That's lower than the 82% in the prompt-vs-workflow post, because thinking was off and each question sits inside a 30-contract pack. Here it's a guard rail, not a score.)

## What I'll change in my own code

- **I was half right.** Caching cut the cost just like the guide says. But none of the levers made my first word come sooner.
- **On a small model, reading is cheap.** About 0.4 s per 100K tokens, so caching 79K tokens can save at most ~0.3 s. My network and the API swing more than that.
- **Thinking costs more than reading.** At thinking effort "low", the small model sometimes thought for 30–340 tokens, which added **0.5–4 s**. Turning thinking down was the biggest speed lever I touched, and it isn't even in this section of the guide.
- **The large model is where input size really bites** (+1 s per 100K). That's where caching might finally show a speed-up.

| Claim | Guide (Claude) | Me (OpenAI, home) | Holds? |
|---|---|---|---|
| Bigger prompt = slower first word | +0.25 s per 100K | +0.39 s small, **+1.04 s** large | **Yes**, more on the large model |
| Caching cuts cost | −85% | −80% / **−85%** | **Yes** |
| Caching speeds up a long prompt | 1.7 s → 0.5 s | 1.20 s off, 1.56 s on | **No** |
| Pre-warming speeds up turn 1 | 1.0 s → 0.8 s | 1.31 s cold, 1.64 s warm | **No** |
| Server keeps the chat | 22.3 MB → 0.3 KB, 1.27 s → 0.63 s | 397 KB → 1.3 KB, 1.14 s → 1.06 s | **Bytes yes, speed no** |

**My rule of thumb:** turn caching on **for the money**, always. For speed, check thinking effort and the network first, then measure before trusting any lever.

## Why these numbers might not travel

- **One machine, one home connection, one day.** Network noise is part of what I measured. From a cloud machine, reading time would stand out more.
- **OpenAI, not Claude.** The levers are close, not the same.
- **Caching and pre-warming ran on the small model only** (cost). The large model reads slower, so that's where they could help.
- **Small samples:** 5 + 3 rounds in test 1, 10 + 3 chats in test 2, 10 repeats in test 3, 3 chats in test 4.
- **My long pack is 79K tokens**, not the guide's 146K.

Total cost of the whole experiment: **about $3.55**.

**Data credit.** The NDAs and labels come from **ContractNLI** (Koreeda & Manning, 2021, [stanfordnlp.github.io/contract-nli](https://stanfordnlp.github.io/contract-nli/)), released under **CC BY 4.0**.

## How the timer works

### The documents

- **The NDAs, statements and answer key** are read straight from the prompt-vs-workflow topic's data folder. Nothing is copied.
- **Packs:** contracts numbered C01, C02… and stacked until a target size is reached (20K to 151K tokens). Each keeps its sentence numbers, so the proof can still be checked.
- **Questions:** 17 per chat, one per ContractNLI statement, each naming a contract code.

### Tools

| Tool | What I used it for |
|---|---|
| **Python 3** | Everything |
| **OpenAI Responses API**, streaming | The calls, timed event by event |
| **pytest** | Offline tests with a fake client, no network |
| **Claude Code** | My pair programmer: design, plan, code and review |

### Step by step

1. `timer.py` makes one **streamed** call and records the time of every event: first word, total, tokens and bytes sent.
2. `packs.py` builds the contract packs, the questions and the prompt text, and reads the answers.
3. `chat.py` runs one 17-turn chat three ways: cache on, cache off, and `previous_response_id`.
4. `experiments.py` runs tests 0–4. Variants **take turns** (A, B, A, B…), so a slow minute on my connection hits both.
5. `stats.py` gives medians, the slow tail, the slope and a bootstrap interval for every difference.
6. `run.py` prints a cost estimate, asks before spending, and refuses to pass a **$10 ceiling** for the topic. Every run is saved as a file.
7. `report.py` builds the results file **from the run files only**. No number is typed by hand.

### Tests for the timer

No API calls and no cost here. These tests guard the timing itself:

- **The timer is honest:** thinking tokens count as output, not as the first word; an error mid-stream keeps the partial times.
- **Rate limits are retried outside the clock**, and a bad request is never retried.
- **Cache on/off really differ:** "on" keeps the instructions and pack identical every turn, "off" changes the first line every turn.
- **The server-side chat** sends only the new question after turn one, and falls back to a full re-send on error.
- **Fair stats:** warm-up calls and errors are left out but counted; a "cold" request that read from cache is flagged and left out.
- **Money:** cached tokens are priced at the cache rate, and the run stops before crossing the budget.

### What the runs taught me

The runs caught four things my design hadn't:

- **OpenAI's cache needs the whole earlier prompt as the start.** My first warm-up sent the pack plus "Reply with OK.", so the next question never matched it (0 of 10 hits). A warm-up must send the shared start and nothing after it.
- **"Random" isn't random if you seed it.** A re-run with the same seed reused the last run's "fresh" first lines, and OpenAI still had them cached 8 minutes later. The report's cold check caught it. Each run now adds its own random part.
- **Re-sending an 80K-token chat every turn hits rate limits.** Test 4 hit the 2M tokens-per-minute limit 4 times.
- **Use medians.** One request in the pre-warm re-run stalled for about two hours. The median didn't move.

### Code and raw results

The code lives here: [ai-engineering-lab / 03-input-tokens-latency-contract-nli](https://github.com/hakmimi/ai-engineering-lab/tree/main/topics/03-input-tokens-latency-contract-nli). It has the streaming timer, the five tests, the offline tests, the design and plan, and a results file built only from real runs.
