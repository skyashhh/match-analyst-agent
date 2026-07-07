"""
Match Analyst Agent -- CLI entrypoint
=======================================
Usage:
    python3 main.py "Arsenal" "Chelsea"

Runs the 3-agent ADK pipeline (Data -> Analyst -> Report Writer) and
prints the final pre-match briefing.

Requires GOOGLE_API_KEY to be set in the environment (see .env.example).
Get one free at https://aistudio.google.com/apikey
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.pipeline import root_agent

load_dotenv()  # loads GOOGLE_API_KEY etc. from a local .env file, if present

APP_NAME = "football_match_analyst"
USER_ID = "cli_user"


async def run_matchup(home_team: str, away_team: str) -> str:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY is not set. Copy .env.example to .env and add your "
            "key (free from https://aistudio.google.com/apikey), or export it "
            "directly in your shell. Never commit a real key to source control."
        )

    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)

    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=f"Home team: {home_team}. Away team: {away_team}.")],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=user_message,
    ):
        # Print each agent's step as it completes, so the pipeline's
        # reasoning is visible -- useful for the demo video.
        if event.author and event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts)
            if text.strip():
                print(f"\n--- [{event.author}] ---\n{text.strip()}\n")
                final_text = text

    return final_text


def main():
    if len(sys.argv) != 3:
        print('Usage: python3 main.py "Home Team" "Away Team"')
        sys.exit(1)

    home_team, away_team = sys.argv[1], sys.argv[2]
    asyncio.run(run_matchup(home_team, away_team))


if __name__ == "__main__":
    main()
