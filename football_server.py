"""
Football Data MCP Server
=========================
Exposes football (soccer) data as MCP tools, backed by TheSportsDB's free
JSON API. This is the "Data" layer of the Match Analyst Agent: any MCP
client (Claude, an ADK agent, a script) can talk to this server without
knowing anything about the underlying REST API.

Why MCP here?
-------------
Wrapping the data source as an MCP server (instead of calling requests.get()
directly inside the agent) decouples "how we fetch data" from "how the agent
reasons". You could swap TheSportsDB for API-Football or football-data.org
by only touching this file -- the agent code never changes.

Security note
-------------
TheSportsDB's free tier uses a shared "test" API key (the literal string
"123", documented publicly on thesportsdb.com). We still read it from an
environment variable rather than hardcoding it, so that swapping in a paid
personal key later is a one-line config change, not a code change. NEVER
hardcode real/paid API keys -- always load from environment variables.
"""

import os
import requests
from mcp.server.fastmcp import FastMCP

# Load the API key from environment, falling back to the public test key.
# In a paid/production deployment, set THESPORTSDB_API_KEY in your .env file.
API_KEY = os.environ.get("THESPORTSDB_API_KEY", "123")
BASE_URL = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}"

mcp = FastMCP("football-data-server")


def _get(endpoint: str, params: dict) -> dict:
    """Small internal helper: GET a TheSportsDB endpoint and return JSON."""
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def search_team(team_name: str) -> dict:
    """Look up a football team by name and return its TheSportsDB team ID,
    league, venue, and a short description.

    Args:
        team_name: Team name as commonly written, e.g. "Arsenal", "Real Madrid".
    """
    data = _get("searchteams.php", {"t": team_name})
    teams = data.get("teams") or []
    if not teams:
        return {"found": False, "message": f"No team found matching '{team_name}'"}

    team = teams[0]
    return {
        "found": True,
        "team_id": team.get("idTeam"),
        "name": team.get("strTeam"),
        "league": team.get("strLeague"),
        "stadium": team.get("strStadium"),
        "country": team.get("strCountry"),
    }


@mcp.tool()
def get_recent_results(team_id: str) -> dict:
    """Get a team's last 5 completed matches (score, opponent, date).

    Args:
        team_id: TheSportsDB numeric team ID (from search_team).
    """
    data = _get("eventslast.php", {"id": team_id})
    events = data.get("results") or []
    results = [
        {
            "date": e.get("dateEvent"),
            "home_team": e.get("strHomeTeam"),
            "away_team": e.get("strAwayTeam"),
            "home_score": e.get("intHomeScore"),
            "away_score": e.get("intAwayScore"),
            "league": e.get("strLeague"),
        }
        for e in events
    ]
    return {"team_id": team_id, "recent_results": results}


@mcp.tool()
def get_upcoming_fixtures(team_id: str) -> dict:
    """Get a team's next 5 scheduled fixtures.

    Args:
        team_id: TheSportsDB numeric team ID (from search_team).
    """
    data = _get("eventsnext.php", {"id": team_id})
    events = data.get("events") or []
    fixtures = [
        {
            "date": e.get("dateEvent"),
            "time": e.get("strTime"),
            "home_team": e.get("strHomeTeam"),
            "away_team": e.get("strAwayTeam"),
            "league": e.get("strLeague"),
            "venue": e.get("strVenue"),
        }
        for e in events
    ]
    return {"team_id": team_id, "upcoming_fixtures": fixtures}


if __name__ == "__main__":
    # Runs as a stdio MCP server -- the ADK agent spawns this as a subprocess
    # and talks to it over stdin/stdout using the MCP protocol.
    mcp.run(transport="stdio")
