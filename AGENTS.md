# Anzuelo Sandbox

## What this is
A self-contained demo for my AAIF Ambassador work. It shows what happens when an
AI agent reads untrusted social media posts that contain a hidden instruction
(prompt injection), and how agentgateway in front of an MCP server limits what
the agent can do.

The data shape comes from Anzuelo (../Anzuelo), my lead-finding agent. This repo
never connects to Anzuelo's production Supabase and never changes anything in
../Anzuelo.

## Architecture
- MCP server: Python, FastMCP, over local JSON data
  - search_leads, get_lead: read tools
  - draft_reply: write tool, saves a draft locally, never sends anything
- agentgateway v1.7.0 in front of the MCP server, run with Docker
  (no Intel Mac binary exists). How to run it: doc/agentgateway-guide.md
- Goose as the client: Claude Sonnet 5.5 (local models were too slow or too weak on
  this Intel Mac, see runs/). Run with ./runs/run.sh 1|2|3
- Docker Compose to run everything with one command (later session)

## Rules
- Pin mcp to exactly 1.29.0. Looser constraints resolve to 2.x, which renames FastMCP.
- Less code is better. No fallbacks: if something fails, fail loudly and show the error.
- No real names, handles or post text in this repo. Data is fake or anonymized.
- ../Anzuelo is read-only reference. Never open its .env or any file with secrets.
- Don't guess agentgateway config. Check the installed version and read the docs
  for that version (the config format changes between versions). Put the doc URL
  in a comment next to each config block.
- Never invent results. Anything in the README must come from a run we actually did.
  If something hasn't been run, say so.
- I'm learning this. Explain each new concept in one or two plain sentences.
- Show me a plan and wait for my OK before writing code.

## Status: Module 2 (security, guardrails, gateways)
- [ ] 1. agentgateway quickstart with server-everything (skipped so far, went straight to step 2)
- [x] 2. Own FastMCP server with fake leads behind agentgateway (6 playground tests passed, 2026-11-24)
- [x] 3. First rule: allow read tools, block draft_reply (draft_reply hidden and blocked, 2026-11-24)
- [x] 4. Spike: route-level rule that reads tool arguments (English and Spanish)
  (link rule blocks both languages; known gaps: link without "http", non-string
  text fails open and only the server catches it. 2026-11-24)
- [x] 5. Goose, three attack runs, logs saved (runs/run1-3, 2026-11-24). Switched from
  local models to Claude Sonnet 5.5. The model ignored and reported the injection in
  all three runs, so the gateway never had to stop a fooled agent.
- [ ] 6. Swap in anonymized real Anzuelo leads