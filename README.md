# ⚽ Match Analyst Agent

A multi-agent system that turns "who's playing this weekend?" into a
readable pre-match scouting briefing — automatically fetching form data,
analyzing trends, and writing the report, with no manual research.

Built for the **AI Agents: Intensive Vibe Coding Capstone Project** (Freestyle track).

## Problem

Casual fans and pundits want quick, informed pre-match context — recent
form, a notable streak, a storyline — without manually digging through
stats sites before every game. Doing this well requires three distinct
skills: pulling accurate data, spotting the meaningful pattern in that
data, and writing it up clearly. A single LLM call tends to blend these
steps and can quietly hallucinate a score or trend it never actually looked up.

## Why Agents?

Splitting the work into three specialist agents makes each step
**auditable**: the Data Agent's job is *only* to call tools and report
facts — it has no room to editorialize or invent a result. The Analyst
Agent's job is *only* to reason over facts that have already been
fetched — it cannot skip the data step. The Report Agent's job is *only*
to turn a finished analysis into prose. If the final report is ever
wrong, you know immediately which agent to inspect, instead of debugging
one monolithic prompt.

## Architecture

```
User ("Arsenal" vs "Chelsea")
        │
        ▼
┌─────────────────────────────────────────────┐
│         SequentialAgent (orchestrator)       │
│                                               │
│  ┌───────────┐   ┌──────────────┐   ┌───────────────┐
│  │Data Agent │──▶│Analyst Agent │──▶│ Report Agent  │
│  │(tool use) │   │(reasoning)   │   │ (writing)     │
│  └─────┬─────┘   └──────────────┘   └───────────────┘
│        │                                             │
└────────┼─────────────────────────────────────────────┘
         │  MCP (stdio)
         ▼
┌─────────────────────────┐
│  Football Data MCP      │
│  Server                 │
│  - search_team          │
│  - get_recent_results    │
│  - get_upcoming_fixtures │
└──────────┬───────────────┘
           │ REST
           ▼
     TheSportsDB API
```

Each agent's output is passed to the next automatically via ADK's
`output_key` state-passing mechanism — no manual glue code needed between
steps.

## Key Concepts Demonstrated (per rubric)

| Concept | Where |
|---|---|
| Multi-agent system (ADK) | `agent/pipeline.py` — `SequentialAgent` chaining 3 `LlmAgent`s |
| MCP Server | `mcp_server/football_server.py` — custom stdio MCP server, connected via `MCPToolset` |
| Security | API keys loaded from environment variables only (`.env`, never hardcoded); `.env` is git-ignored |
| Deployability | See "Deploying" below — runs locally today, one step from Cloud Run |

## Setup

```bash
git clone <this-repo>
cd football-match-analyst
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your free Gemini key from https://aistudio.google.com/apikey
```

## Run

```bash
python3 main.py "Arsenal" "Chelsea"
```

This prints each agent's output as it completes (data → analysis → final
report), so you can see the pipeline reasoning step by step.

## Security Notes

- No API keys are hardcoded anywhere in the codebase.
- The Gemini key and (optional) TheSportsDB key are read only from
  environment variables via `python-dotenv`.
- `.env` is listed in `.gitignore` so real keys are never committed.
- The default TheSportsDB key (`123`) is the *publicly documented free
  test key* provided by TheSportsDB itself for exactly this kind of demo —
  it is not a secret.

## Deploying

This currently runs as a local CLI for development speed. To make it a
public endpoint:

1. Wrap `run_matchup()` in a small FastAPI app (a few lines — `Runner` and
   `root_agent` are already async-ready).
2. Containerize with a standard Python Dockerfile.
3. Deploy the container to **Google Cloud Run**, setting `GOOGLE_API_KEY`
   as a Cloud Run secret (never as a plain environment variable in
   source-controlled config).
4. The MCP server subprocess ships inside the same container — no
   separate deployment needed since it talks to the agent over stdio.

## Project Structure

```
football-match-analyst/
├── main.py                     # CLI entrypoint, runs the pipeline
├── agent/
│   └── pipeline.py              # 3-agent ADK SequentialAgent pipeline
├── mcp_server/
│   └── football_server.py       # MCP server wrapping TheSportsDB API
├── requirements.txt
├── .env.example
└── README.md
```

## Possible Extensions

- Add a 4th agent that recommends a fantasy-football captain pick based
  on the analysis.
- Swap TheSportsDB for a paid API (API-Football) for deeper stats (xG,
  possession) — only `mcp_server/football_server.py` would need to change.
- Add a `ParallelAgent` to fetch both teams' data concurrently instead of
  sequentially, for lower latency.
