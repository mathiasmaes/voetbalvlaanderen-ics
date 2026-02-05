# Voetbal Vlaanderen → iCalendar (ICS)

Generates an ICS feed for a Voetbal Vlaanderen / RBFA team by calling RBFA's public GraphQL endpoint.

## How it works
- Daily script fetches full team calendar via GraphQL persisted query.
- Optionally enriches each match using a match detail query (venue/referee/score).
- Generates `static/team.ics`.
- Flask serves it at `/team.ics` for Apple Calendar subscription.

## Config via environment variables
Required:
- TEAM_ID (default 347325)
- BASE_DIR (server folder where `static/team.ics` is written)
- MATCH_DETAIL_SHA (only if you want match detail enrichment)

Optional:
- TZ, MATCH_DURATION_MIN, LANGUAGE, SORT_BY_DATE

## Running locally
pip install -r requirements.txt
BASE_DIR=. python refresh_team_ics.py
python -c "from app import app; app.run()"
