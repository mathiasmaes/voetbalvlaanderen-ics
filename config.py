"""
config.py
---------
Central config. All values can be overridden with environment variables so that:
- The repo can be public
- You don't leak team ids, paths, etc. (even though those aren't secret)
"""

import os

# --- Team configuration ---
TEAM_ID = os.getenv("TEAM_ID", "347325")
LANGUAGE = os.getenv("LANGUAGE", "nl")
SORT_BY_DATE = os.getenv("SORT_BY_DATE", "asc")

# --- RBFA datalake GraphQL endpoint ---
GRAPHQL_URL = os.getenv("GRAPHQL_URL", "https://datalake-prod2018.rbfa.be/graphql")

# Persisted query hash for GetTeamCalendar
TEAM_CALENDAR_SHA = os.getenv(
    "TEAM_CALENDAR_SHA",
    "3f0441e6723b9852b4f0cff2c872f4aa674c5de2d23589efc70c7a4ffb7f6383",
)

# Persisted query hash for GetMatchDetail (location, referee, score, etc.)
MATCH_DETAIL_SHA = os.getenv(
    "MATCH_DETAIL_SHA",
    "cd8867b845c206fe7aa75c1ebf7b53cbda0ff030253a45e2e2b4bcc13ee46c9a",
)

# --- Calendar behavior ---
TZ = os.getenv("TZ", "Europe/Brussels")
MATCH_DURATION_MIN = int(os.getenv("MATCH_DURATION_MIN", "60"))

# Cache duration (6 hours for timely updates)
CACHE_DURATION = int(os.getenv("CACHE_DURATION", str(6 * 3600)))

# --- Paths on server ---
# On PythonAnywhere, set BASE_DIR to /home/<username>/mysite (or wherever you deploy)
BASE_DIR = os.getenv("BASE_DIR", ".")

ICS_OUTPUT_PATH = os.path.join(BASE_DIR, "static", "team.ics")
STATE_PATH = os.path.join(BASE_DIR, "state.json")

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
)
