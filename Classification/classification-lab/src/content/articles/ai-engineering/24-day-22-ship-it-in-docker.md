---
title: "Day 22: Ship It in Docker"
description: "From an assistant that runs because your laptop happens to have the right packages to an image that runs the same way on any machine with Docker. Pinned dependencies, a Dockerfile, a volume for data that must survive, and secrets that never enter the image."
series: "ai-engineering"
order: 24
date: 2026-10-01
keywords: ["ai engineering", "israel knowledge assistant", "docker", "compose", "pinned requirements"]
readingTime: "8 min read"
---

Part of the **Israel knowledge assistant** arc. Code for this day: [`Day22`](https://github.com/hakmimi/AIEngineering/tree/main/Day22). Layers touched: L4 System.

## Goals

- **G1. Make the build reproducible by pinning every runtime dependency.**  
  You can: explain why `requirements.txt` now has `==` versions and why pytest moved to `requirements-dev.txt`.
- **G2. Write a Dockerfile that caches well and runs safely.**  
  You can: walk the Dockerfile top to bottom and say why `requirements.txt` is copied before the code.
- **G3. Keep secrets out of the image and state out of the container.**  
  You can: show the key arriving through `--env-file` and `memory.db` surviving a container restart.
- **G4. Run the whole system with one command.**  
  You can: run `docker compose up --build` and hit `/health`, `/ready` and `/rag/graph` from PowerShell.

## System map

The application in the middle is unchanged from Day 21. Everything new is around it: how it's built, how it's started, where its secrets come from and where its data lives.

> Client → localhost:8000 → Docker container (uvicorn 0.0.0.0) → FastAPI + LangGraph → FAISS / tools / LLM → Response, with /app/data ⇄ ./data on the host

<div class="ae-map" role="img" aria-label="The client calls localhost:8000 on the host. Docker maps that port into a container built from the israel-assistant:day22 image, where uvicorn listens on 0.0.0.0:8000 as a non-root user. The key arrives from .env through --env-file or env_file in compose. The unchanged FastAPI and LangGraph app reads docs and the FAISS index and writes SQLite memory under /app/data, which is a volume mounted from ./data on the host. The RAG path calls OpenAI and the answer returns to the client."><svg font-family="IBM Plex Sans, Segoe UI, sans-serif" style="min-width:1050px" viewbox="0 0 1440 404" xmlns="http://www.w3.org/2000/svg"><defs><marker id="mka" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"></path></marker><marker id="mkm" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"></path></marker><marker id="mkg" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ok)"></path></marker><marker id="mkx" markerheight="7" markerwidth="7" orient="auto-start-reverse" refx="9" refy="5" viewbox="0 0 10 10"><path d="M0,0 L10,5 L0,10 z" fill="var(--ghost)"></path></marker></defs><text class="lane" x="20" y="18">CLIENT</text><text class="lane" x="264" y="18">HOST</text><text class="lane" x="508" y="18">L4 · CONTAINER</text><text class="lane" x="752" y="18">L2–L3 · APP</text><text class="lane" x="996" y="18">L1 · DATA</text><text class="lane" x="1240" y="18">EXTERNAL</text><path class="edge" d="M200,147 C230,147 230,98 261,98" marker-end="url(#mka)"></path><path class="edge" d="M444,98 C474,98 474,209 505,209" marker-end="url(#mka)"></path><path class="edge" d="M444,200 C474,200 474,209 505,209" marker-end="url(#mka)"></path><path class="edge" d="M598,136 L598,155" marker-end="url(#mka)"></path><path class="edge" d="M688,209 C718,209 718,147 749,147" marker-end="url(#mka)"></path><path class="edge" d="M932,147 C962,147 962,147 993,147" marker-end="url(#mka)"></path><path class="edge-old" d="M932,147 C1084,147 1084,147 1237,147" marker-end="url(#mkm)"></path><path class="edge-back" d="M1330,178 V286 H110 V180" marker-end="url(#mkg)"></path><g class="node-external"><rect height="61" rx="8" width="180" x="20" y="116"></rect><text class="nt t" text-anchor="middle" x="110" y="140">Client</text><text class="ns s" text-anchor="middle" x="110" y="160">PowerShell · browser</text></g><g class="node-new"><rect height="84" rx="8" width="180" x="264" y="56"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="88">docker compose up</text><text class="ns s" text-anchor="middle" x="354" y="107">or docker run</text><text class="ns s" text-anchor="middle" x="354" y="122">-p 8000:8000</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="436" y="69">NEW</text></g><g class="node-existing"><rect height="76" rx="8" width="180" x="264" y="162"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="354" y="186">.env</text><text class="ns s" text-anchor="middle" x="354" y="205">--env-file / env_file</text><text class="ns s" text-anchor="middle" x="354" y="220">never copied into the image</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="508" y="34"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="66">israel-assistant:</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="84">day22</text><text class="ns s" text-anchor="middle" x="598" y="103">python:3.13-slim</text><text class="ns s" text-anchor="middle" x="598" y="118">pinned requirements</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="47">NEW</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="508" y="158"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="190">uvicorn</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="598" y="208">0.0.0.0:8000</text><text class="ns s" text-anchor="middle" x="598" y="227">non-root appuser</text><text class="ns s" text-anchor="middle" x="598" y="242">HEALTHCHECK /health</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="680" y="171">NEW</text></g><g class="node-existing"><rect height="61" rx="8" width="180" x="752" y="116"></rect><text class="nt t" text-anchor="middle" x="842" y="140">FastAPI + LangGraph</text><text class="ns s" text-anchor="middle" x="842" y="160">Day 21 code, unchanged</text></g><g class="node-new"><rect height="102" rx="8" width="180" x="996" y="96"></rect><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="128">/app/data ⇄</text><text class="nt t" font-family="JetBrains Mono, monospace" style="font-size:13px" text-anchor="middle" x="1086" y="146">./data</text><text class="ns s" text-anchor="middle" x="1086" y="165">docs · FAISS index</text><text class="ns s" text-anchor="middle" x="1086" y="180">memory.db survives rebuilds</text><text class="el" style="fill:var(--accent);font-size:9px" text-anchor="end" x="1168" y="109">NEW</text></g><g class="node-external"><rect height="61" rx="8" width="180" x="1240" y="116"></rect><text class="nt t" text-anchor="middle" x="1330" y="140">OpenAI</text><text class="ns s" text-anchor="middle" x="1330" y="160">embeddings + LLM</text></g><rect class="elbg" height="15" rx="3" width="40" x="210" y="106"></rect><text class="el" text-anchor="middle" x="230" y="116">:8000</text><rect class="elbg" height="15" rx="3" width="59" x="445" y="136"></rect><text class="el" text-anchor="middle" x="474" y="148">port map</text><rect class="elbg" height="15" rx="3" width="59" x="445" y="188"></rect><text class="el" text-anchor="middle" x="474" y="198">env vars</text><rect class="elbg" height="15" rx="3" width="27" x="602" y="134"></rect><text class="el" text-anchor="start" x="604" y="146">CMD</text><rect class="elbg" height="15" rx="3" width="85" x="920" y="130"></rect><text class="el" text-anchor="middle" x="962" y="141">read / write</text><rect class="elbg" height="15" rx="3" width="110" x="665" y="279"></rect><text class="el" text-anchor="middle" x="720" y="290">{ "results": … }</text><text class="lane" style="fill:var(--ghost)" x="20" y="334">COMING LATER</text><g class="node-ghost"><rect height="44" rx="8" width="246" x="20" y="344"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="143" y="371">Day 23 · request-id logging</text></g><g class="node-ghost"><rect height="44" rx="8" width="260" x="286" y="344"></rect><text class="ns" style="fill:var(--ghost);font-size:12px" text-anchor="middle" x="416" y="371">Day 24 · token + cost tracking</text></g></svg></div>

<div class="ae-legend"><span><i style="background:var(--accent-soft);border:1.5px solid var(--accent)"></i>New this episode</span><span><i style="border:1.5px dashed var(--accent)"></i>Changed this episode</span><span><i style="border:1.5px solid var(--line)"></i>Already built</span><span><i style="border:1.5px solid var(--ink)"></i>External</span><span><i style="border:1.5px dashed var(--ghost)"></i>Coming later</span></div>

## Before and after

### Before this episode: Works on my machine

- `requirements.txt` listed names with no versions, and included `pytest` and `httpx`
- `tenacity`, which `resilience.py` imports, wasn't listed at all
- Running it meant: install Python, create a venv, pip install, hope the versions match
- Data and memory lived wherever you ran the code from

### After this episode: Runs the same everywhere

- Runtime pins in `requirements.txt`, dev tools in `requirements-dev.txt`
- A `Dockerfile`: slim base, cached dependency layer, non-root user, `HEALTHCHECK`
- Secrets passed at run time with `--env-file`, kept out by `.dockerignore`
- `./data` mounted at `/app/data`, so memory and index rebuilds survive the container

> **Why it matters:** a reviewer, a teammate or a server should be able to run your system with one command and get the same behaviour you measured. Every later deployment step, from CI to the cloud, assumes the app is already a container.

## Code walkthrough

Four snippets from `Day22`. None of them is Python: today's code is packaging.

### requirements.txt · pinned runtime

```text
# Runtime dependencies - pinned to the versions the test suite and live runs used (Python 3.13)
fastapi==0.138.0
uvicorn==0.49.0
openai==2.43.0
...
langgraph==1.2.12
tenacity==9.1.4
# OS certificate store for TLS (fixes SSL errors behind corporate proxies / antivirus on Windows); optional elsewhere
truststore==0.10.4; sys_platform == "win32"
```

**Pin what you tested against, and nothing you don't ship.** Day 21's file had no versions and no `tenacity`, which only worked because another package pulled it in. The environment marker installs `truststore` on Windows only, so the Linux image doesn't need it.

### Dockerfile · cache-friendly layers

```text
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code + sample data (docs, embedded chunks, FAISS index). Secrets are NOT copied (.dockerignore).
COPY . .
```

**Dependencies before code, so editing code doesn't reinstall packages.** Docker reuses a layer until one of its inputs changes. Change `graph.py` and only the `COPY . .` layer rebuilds. `PYTHONUNBUFFERED` makes log lines show up in `docker logs` right away.

### Dockerfile · run safely

```text
# Run as a non-root user; /app/data must be writable (SQLite memory, index rebuilds).
RUN useradd --create-home appuser && chown -R appuser:appuser /app/data
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Least privilege, a health signal, and an address the host can reach.** The slim image has no curl, so the health check uses Python's own `urllib`. The only writable folder is `/app/data`, which is where SQLite and index rebuilds need to write.

### docker-compose.yml · the run command, written down

```yaml
services:
  api:
    build: .
    image: israel-assistant:day22
    ports:
      - "8000:8000"
    env_file:
      - .env                      # OPENAI_API_KEY=...  (optional: APP_API_KEY=... to require the X-API-Key header)
    volumes:
      - ./data:/app/data          # data + FAISS index + SQLite memory live on the host, survive container rebuilds
    restart: unless-stopped
```

**Secrets in at run time, state out on the host.** This file replaces a long `docker run` line. The volume hides the data copied into the image, so the host's `./data` is what the app actually uses.

## Run it

**Step 1**

```text
docker build -t israel-assistant:day22 .
```

**Expect:** Build finishes. Run it a second time: every step says `CACHED`. Touch `graph.py` and rebuild: only `COPY . .` and later layers rerun.

**Step 2**

```text
docker run --rm -p 8000:8000 --env-file .env `
  -v "${PWD}/data:/app/data" israel-assistant:day22
```

**Expect:** `Uvicorn running on http://0.0.0.0:8000`. Logs appear immediately because of `PYTHONUNBUFFERED`.

**Step 3**

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready | ConvertTo-Json
```

**Expect:** `status: ok`, then `status: ready` with `docs_file`, `embedded_chunks_file` and `openai_api_key` all `true`.

**Step 4**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/rag/graph" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Where is Masada?","session_id":"demo"}'
```

**Expect:** A RAG answer mentioning the Dead Sea. `data/memory.db` now exists on the host.

**Step 5**

```text
docker compose up --build -d
docker ps
```

**Expect:** Stop the `docker run` container first. After ~30 s the status column shows `(healthy)`.

**Step 6**

```text
docker compose down
docker compose up -d
Invoke-RestMethod http://localhost:8000/session/demo
```

**Expect:** `turns: 1`. The container was destroyed and recreated, and the conversation survived on the volume.

### Break it on purpose

#### 1 · Bind to 127.0.0.1 inside the container

Override the command: `docker run --rm -p 8000:8000 --env-file .env israel-assistant:day22 uvicorn main:app --host 127.0.0.1 --port 8000`. Uvicorn starts happily, but `Invoke-RestMethod http://localhost:8000/health` from the host fails. Inside the container, 127.0.0.1 is the container's own loopback, and the port mapping can't reach it. That's why the `CMD` says `0.0.0.0`.

#### 2 · Forget the key

Run the image without `--env-file`. `/health` still says ok, because the process is alive. `/ready` says `degraded` with `openai_api_key: false`, and a RAG question goes to the fallback path. Liveness and readiness are two different questions.

```text
docker run --rm -p 8000:8000 --env-file .env `
  -v "${PWD}/data:/app/data" israel-assistant:day22
```

> A container changes three things about your app: its paths, its network address and where its secrets come from. Paths already came from `config.BASE_DIR`, so only the other two needed work. The honest part: the README says the original build was simulated, so today's first real build is part of the episode.

## Cheat sheet

- **Image**: A read-only package of a filesystem plus a start command, built from a Dockerfile.
- **Container**: A running instance of an image. Delete it and start another, and you get a fresh copy.
- **Layer**: One cached filesystem step of an image. A changed input rebuilds that layer and every layer after it.
- **Pinning**: Fixing exact versions (`fastapi==0.138.0`) so every install produces the same environment.
- **.dockerignore**: Files left out of the build context. `.env*` here keeps the API key out of every layer.
- **--env-file**: Passes variables from a file into the container at run time, so secrets never live in the image.
- **Volume / bind mount**: A host folder mapped into the container (`./data:/app/data`). Data written there outlives the container.
- **0.0.0.0**: Listen on every network interface. Needed so traffic from the host's port mapping reaches the app.
- **HEALTHCHECK**: A command Docker runs on a schedule. Its exit code marks the container healthy or unhealthy.
- **Liveness vs readiness**: `/health` says the process is up. `/ready` says it has what it needs (data files, API key) to answer.

## Self-check

Answer out loud first, then open the card.

<div class="ae-quiz">
<details><summary>Why copy <code>requirements.txt</code> and run pip before <code>COPY . .</code>?</summary><p>Docker caches each layer. With dependencies first, editing code only rebuilds the code layer, and the slow pip install is reused.</p></details>
<details><summary>What would happen without <code>.env*</code> in <code>.dockerignore</code>?</summary><p><code>COPY . .</code> would copy <code>.env</code> into an image layer. Anyone with the image, or a registry it gets pushed to, could read the API key.</p></details>
<details><summary>Why does uvicorn bind to 0.0.0.0 in the container?</summary><p>127.0.0.1 inside a container is the container's own loopback. Port mapping from the host arrives on the container's network interface, which only 0.0.0.0 covers.</p></details>
<details><summary>Which data goes into the image and which goes on the volume?</summary><p>Read-mostly data (docs, embedded chunks, FAISS index) is copied in so the image runs out of the box. State that must survive (SQLite memory, index rebuilds) goes to the mounted <code>/app/data</code>.</p></details>
<details><summary>Why split <code>requirements.txt</code> and <code>requirements-dev.txt</code>?</summary><p>The image only needs what the app runs with. pytest, httpx and ruff stay in the dev file, which starts with <code>-r requirements.txt</code>, so the image is smaller and ships less.</p></details>
</div>

**Next:** Day 23 – Trace Every Request

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
