# /// script
# requires-python = ">=3.12"
# dependencies = ["mcp==1.29.0"]
# ///
"""Tiny MCP server over fake leads. draft_reply only saves locally; nothing is ever sent."""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

DATA_DIR = Path(__file__).parent / "data"
LEADS_FILE = DATA_DIR / "leads.json"
DRAFTS_FILE = DATA_DIR / "drafts.json"

# Defaults in mcp 1.29.0: host 127.0.0.1, port 8000, path /mcp
# DNS rebinding protection stays on. The first three hosts and the origins are the
# mcp 1.29.0 defaults. "host.docker.internal" is added because agentgateway runs in
# Docker and reaches this server by that name (it sends the Host header without a port).
mcp = FastMCP(
    "anzuelo-sandbox",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", "host.docker.internal"],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"],
    ),
)


def load_leads() -> list[dict]:
    return json.loads(LEADS_FILE.read_text())


@mcp.tool()
def search_leads(query: str, min_score: int = 0) -> list[dict]:
    """Find leads whose post text contains the query (case-insensitive) and whose score is at least min_score."""
    query_lower = query.lower()
    return [
        lead
        for lead in load_leads()
        if query_lower in lead["content"].lower() and lead["score"] >= min_score
    ]


@mcp.tool()
def get_lead(lead_id: str) -> dict:
    """Get one lead by its id, for example "lead-1"."""
    for lead in load_leads():
        if lead["id"] == lead_id:
            return lead
    raise ValueError(f"No lead with id {lead_id!r}")


@mcp.tool()
def draft_reply(lead_id: str, text: str) -> dict:
    """Save a draft reply to a lead in data/drafts.json. Nothing is sent anywhere."""
    get_lead(lead_id)  # fails loudly if the lead does not exist
    drafts = json.loads(DRAFTS_FILE.read_text())
    draft = {"lead_id": lead_id, "text": text}
    drafts.append(draft)
    DRAFTS_FILE.write_text(json.dumps(drafts, indent=2, ensure_ascii=False) + "\n")
    return draft


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
