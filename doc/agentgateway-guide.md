# agentgateway: run it with Docker and test it (step by step)

Written for agentgateway **v1.7.0** (the latest release, 2026-10-27).
Every command and result here comes from a run on 2026-11-24, on an Intel Mac
with Docker Desktop (engine 20.10.12).

**What agentgateway is:** a proxy that sits between an AI agent and its MCP
servers. The agent talks only to the gateway, so the gateway can see, log and
(later) block every tool call.

**What the playground is:** a page in agentgateway's web UI where you call MCP
tools by hand, without an agent. It's useful for checking that the wiring works
before an LLM gets involved.

```
Browser / agent  ──►  agentgateway (Docker, port 4000)  ──►  MCP server (Mac, port 8000)
```

## Why Docker and not the install script

The install script (`curl -sL https://agentgateway.dev/install | bash`) fails on
an Intel Mac with a 404. No agentgateway release (v1.0.0 to v1.7.0) ships a
`darwin-amd64` binary, only `darwin-arm64` (Apple chips). The release does ship
a Linux build, and Docker runs Linux programs on a Mac, so we use the official
Docker image.

Docs: https://agentgateway.dev/docs/standalone/latest/documentation/setup/install/docker/

**What Docker is:** a program that runs other programs inside an isolated box
called a container. An **image** is the downloaded package; a **container** is
that image while it runs.

## 1. Check Docker and download the image (once)

Open Docker Desktop first. The `docker` command only works while the app runs.

```sh
docker info --format '{{.ServerVersion}}'
docker pull cr.agentgateway.dev/agentgateway:v1.7.0
```

Expected: a version number, then `Status: Downloaded newer image for
cr.agentgateway.dev/agentgateway:v1.7.0`. The `:v1.7.0` tag pins the version
that `config.yaml` was written for.

## 2. Create the session key and the data folder (once)

```sh
cd ~/src/2026/anzuelo-sandbox
printf 'SESSION_KEY=%s\n' "$(openssl rand -hex 32)" > .env
mkdir -p gateway-data
```

- **Session key:** a secret agentgateway uses to encrypt MCP session IDs. If you
  don't give it one, it generates one and writes it into `config.yaml`, which
  would put a secret in git. With `SESSION_KEY` set, it doesn't write anything.
  Docs: https://agentgateway.dev/docs/standalone/latest/integrations/mcp/servers/http/#session-key
- **`gateway-data/`:** where the gateway keeps its small SQLite database.

Both `.env` and `gateway-data/` are in `.gitignore`.

## 3. Start the MCP server (terminal 1)

```sh
cd ~/src/2026/anzuelo-sandbox
uv run server.py
```

`uv` reads the header at the top of `server.py`, picks Python 3.12+ and
installs `mcp==1.29.0` in a throwaway environment. Your system Python is not
touched.

Expected: `Uvicorn running on http://127.0.0.1:8000`.

## 4. Start agentgateway (terminal 2)

```sh
cd ~/src/2026/anzuelo-sandbox
docker run --rm --name agentgateway \
  --user "$(id -u):$(id -g)" \
  --env-file .env \
  -v "$PWD/config.yaml:/config.yaml" \
  -v "$PWD/gateway-data:/gateway-data" \
  -p 4000:4000 \
  cr.agentgateway.dev/agentgateway:v1.7.0 \
  -f /config.yaml
```

| Part | Meaning |
|---|---|
| `--rm` | Delete the container when it stops (the image stays). |
| `--user "$(id -u):$(id -g)"` | Run as your Mac user, so files it creates belong to you. |
| `--env-file .env` | Pass `SESSION_KEY` into the container. |
| `-v A:B` | Share a file or folder from the Mac (A) into the container (B). |
| `-p 4000:4000` | Mac port 4000 → container port 4000, so the browser can reach it. |
| `-f /config.yaml` | Tell agentgateway which config to load. |

The docs run it with `-d` (in the background). We leave it out so the logs
show in the terminal. Stop it with `Ctrl+C`.

Expected: `serving UI at http://localhost:4000/ui` and no line about
generating a session key.

### Two Docker-specific details

1. **`host.docker.internal`.** Inside a container, `localhost` means the
   container itself, so `config.yaml` points to
   `http://host.docker.internal:8000/mcp`. That name is a Docker Desktop
   feature meaning "the Mac running this container".
   Docs: https://docs.docker.com/desktop/features/networking/
2. **The 421 error.** mcp 1.29.0 turns on DNS rebinding protection when the
   server runs on 127.0.0.1. It only accepts requests addressed to
   `localhost`/`127.0.0.1`. The gateway's requests arrive as
   `Host: host.docker.internal` (no port), so the server answered
   `421 Misdirected Request` / `Invalid Host header: host.docker.internal`.
   Fix (already in `server.py`): keep the protection on and add
   `"host.docker.internal"` to `allowed_hosts`. It has to be the exact name;
   the pattern `host.docker.internal:*` only matches when a port is present.

## 5. Open the playground

1. Go to http://localhost:4000/ui
2. In the **MCP** section, click **Tool Playground**.
3. If you see "Browser access is not allowed", click **Apply CORS**. (CORS is
   the browser rule that blocks a page from calling another address unless that
   address allows it.) We didn't need this on our run.
4. Click **Initialize**. Result: `HTTP 200`, `3 tools discovered`:
   `search_leads`, `get_lead`, `draft_reply`.

## 6. Test each tool

All six tests passed on 2026-11-24, through the gateway:

| Test | Tool | Input | Result |
|---|---|---|---|
| A | `search_leads` | query `web`, min_score `8` | lead-1, lead-3, lead-6 |
| B | `search_leads` | query `zzz`, min_score `0` | empty list, `isError: false` |
| C | `get_lead` | lead_id `lead-2` | the support-team AI post |
| D | `get_lead` | lead_id `lead-99` | `isError: true`, `No lead with id 'lead-99'` |
| E | `draft_reply` | lead_id `lead-1`, text `Hi! Happy to help.` | the draft; `data/drafts.json` has one entry |
| F | `draft_reply` | lead_id `lead-99`, text `x` | `isError: true`; `drafts.json` still has one entry |

**How to read a result:** `status: 200` is the gateway saying "delivered".
`isError` is the tool saying whether it worked. In test D the status is 200 and
`isError` is true: delivered fine, but the tool couldn't find the lead.

**The prompt injection:** the test A results include lead-3 (English) and
lead-6 (Spanish). Both end with a hidden instruction to AI assistants. The
gateway passed that text through unchanged. A later step adds gateway rules to
limit what the agent can *do* after reading it.

## 7. Stop and reset

- Stop either process with `Ctrl+C`.
- Clear saved drafts: `echo '[]' > data/drafts.json`
