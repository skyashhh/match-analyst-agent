"""
Match Analyst Agent -- Multi-Agent Pipeline (Google ADK)
==========================================================
Three specialist agents chained with a SequentialAgent:

  1. DataAgent      -- calls the football MCP server (see mcp_server/) to
                        fetch team info, recent results, and upcoming fixtures
                        for BOTH teams in the matchup.
  2. AnalystAgent    -- turns raw results/fixtures into structured insight:
                        form trend (W/D/L streaks), scoring rate, and any
                        notable pattern (e.g. "unbeaten in last 5").
  3. ReportAgent     -- writes the final human-readable pre-match scouting
                        report, combining the analysis into a short,
                        readable briefing a fan or pundit could use.

Why multiple agents instead of one big prompt?
-----------------------------------------------
Each agent has a narrow, verifiable job. The DataAgent only fetches; it
never invents a score. The AnalystAgent only reasons over structured data
that's already been fetched -- it can't accidentally skip fetching data
and hallucinate a “recent result”. The ReportAgent only writes prose -- it
never touches tools. This separation is what makes the pipeline auditable:
if the final report is wrong, you know exactly which agent's output to
inspect.

State passing: each agent's output_key writes its final text into the
shared session state, so the next agent's {instruction} can reference
{previous_agent_output_key} directly -- this is ADK's built-in mechanism
for passing context between sequential agents.
"""

import os
from pathlib import Path

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

MODEL = os.environ.get("ADK_MODEL", "gemini-2.5-flash")

# Path to our MCP server script, launched as a subprocess over stdio.
_SERVER_SCRIPT = str(Path(__file__).parent.parent / "mcp_server" / "football_server.py")

football_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python3",
            args=[_SERVER_SCRIPT],
        ),
        timeout=15,
    ),
)

# ---------------------------------------------------------------------------
# 1. Data Agent -- only responsibility is calling tools and returning facts
# ---------------------------------------------------------------------------
data_agent = LlmAgent(
    name="data_agent",
    model=MODEL,
    description="Fetches team info, recent results, and upcoming fixtures for a matchup.",
    instruction="""You are a football data-retrieval assistant.
The user will give you two team names (home and away).
For EACH team:
  1. Call search_team to resolve its team_id.
  2. Call get_recent_results with that team_id.
  3. Call get_upcoming_fixtures with that team_id.
Return ONLY the raw structured facts you retrieved for both teams -- do not
analyze or editorialize. If a team can't be found, say so plainly.""",
    tools=[football_toolset],
    output_key="match_data",
)

# ---------------------------------------------------------------------------
# 2. Analyst Agent -- reasons over the fetched data, no tools
# ---------------------------------------------------------------------------
analyst_agent = LlmAgent(
    name="analyst_agent",
    model=MODEL,
    description="Turns raw match data into structured form/trend analysis.",
    instruction="""You are a football analyst. You will receive raw team
data (recent results and upcoming fixtures) for two teams:

{match_data}

For each team, work out:
  - Current form as a W/D/L string over their last available results
  - Goals scored and conceded in those matches
  - Any notable streak (e.g. "unbeaten in last 4", "conceded in every game")

Then compare the two teams head-to-head on form. Output your analysis as
clearly labeled bullet points per team, plus one "Key Storyline" bullet
comparing them. Do not write final prose paragraphs yet -- that's the next
step.""",
    output_key="analysis",
)

# ---------------------------------------------------------------------------
# 3. Report Writer Agent -- only responsibility is prose, no tools
# ---------------------------------------------------------------------------
report_agent = LlmAgent(
    name="report_agent",
    model=MODEL,
    description="Writes the final human-readable pre-match scouting report.",
    instruction="""You are a sports writer producing a short pre-match
briefing for fans. Using this analysis:

{analysis}

Write a report with this structure:
  # <Home Team> vs <Away Team> -- Pre-Match Briefing
  ## Form Guide (short paragraph per team)
  ## Key Storyline (1-2 sentences, the single most interesting angle)
  ## Fixture Details (date/venue if available)

Keep it under 250 words, punchy and readable -- like a matchday newsletter,
not a stats dump.""",
    output_key="final_report",
)

# ---------------------------------------------------------------------------
# Orchestrator: runs the three agents in a fixed sequence, passing state
# forward automatically via output_key / instruction templating above.
# ---------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="match_analyst_pipeline",
    description="End-to-end pre-match football analysis pipeline.",
    sub_agents=[data_agent, analyst_agent, report_agent],
)
