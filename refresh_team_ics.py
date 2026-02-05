#!/usr/bin/env python3
"""
refresh_team_ics.py
-------------------
Generate iCalendar (.ics) feed for any Voetbal Vlaanderen team.

Can be run:
1. Manually: python refresh_team_ics.py <team_id>
2. Via Flask app (on-demand with smart caching)

Features:
- Fetches team calendar from RBFA GraphQL API
- Optionally enriches with match details (location/referee/score)
- Maintains stable UIDs and SEQUENCE numbers for reliable calendar updates
- All text in Flemish (Dutch)
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from dateutil import parser as date_parser
from icalendar import Calendar, Event

import config

TZ = ZoneInfo(config.TZ)


# -----------------------------
# Small state file helpers
# -----------------------------
def load_state(team_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads state file for a specific team.
    State tracks event signatures and sequence numbers.
    """
    state_dir = os.path.join(config.BASE_DIR, "state")
    state_path = os.path.join(state_dir, f"{team_id}.json")
    
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def save_state(team_id: str, state: Dict[str, Dict[str, Any]]) -> None:
    """
    Saves state file for a specific team.
    """
    state_dir = os.path.join(config.BASE_DIR, "state")
    os.makedirs(state_dir, exist_ok=True)
    state_path = os.path.join(state_dir, f"{team_id}.json")
    
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def stable_sig(obj: Any) -> str:
    """
    Create stable hash for change detection.
    """
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


# -----------------------------
# Date/time parsing
# -----------------------------
def parse_dt(val: Optional[str]) -> Optional[dt.datetime]:
    """
    Parse RBFA timestamps (assume Europe/Brussels if no timezone).
    """
    if not val:
        return None
    d = date_parser.parse(val)
    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ)
    else:
        d = d.astimezone(TZ)
    return d


# -----------------------------
# GraphQL calls
# -----------------------------
def gql_post(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST to RBFA GraphQL endpoint.
    """
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://www.voetbalvlaanderen.be",
        "referer": "https://www.voetbalvlaanderen.be/",
        "user-agent": config.USER_AGENT,
    }

    r = requests.post(config.GRAPHQL_URL, headers=headers, json=payload, timeout=45)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, dict) and data.get("errors"):
        raise RuntimeError(f"GraphQL errors: {data['errors']}")

    return data


def fetch_team_info(team_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch basic team information (name, logo) for validation.
    Uses the same teamCalendar query but just extracts team info.
    """
    payload = {
        "operationName": "GetTeamCalendar",
        "variables": {
            "teamId": team_id,
            "language": config.LANGUAGE,
            "sortByDate": config.SORT_BY_DATE,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": config.TEAM_CALENDAR_SHA,
            }
        },
    }

    try:
        resp = gql_post(payload)
        items = resp.get("data", {}).get("teamCalendar", [])
        
        # Extract team info from first match
        if items and len(items) > 0:
            first_match = items[0]
            # Try to get team name from either home or away team
            home_team = first_match.get("homeTeam", {})
            away_team = first_match.get("awayTeam", {})
            
            # Determine which team matches our team_id
            team_name = None
            team_logo = None
            
            if isinstance(home_team, dict) and str(home_team.get("id")) == str(team_id):
                team_name = home_team.get("name")
                team_logo = home_team.get("logo") or home_team.get("logoUrl")
            elif isinstance(away_team, dict) and str(away_team.get("id")) == str(team_id):
                team_name = away_team.get("name")
                team_logo = away_team.get("logo") or away_team.get("logoUrl")
            
            if team_name:
                return {
                    "id": team_id,
                    "name": team_name,
                    "logo": team_logo
                }
        
        return None
    except Exception:
        return None


def fetch_team_calendar(team_id: str) -> List[Dict[str, Any]]:
    """
    Fetch full team calendar.
    """
    payload = {
        "operationName": "GetTeamCalendar",
        "variables": {
            "teamId": team_id,
            "language": config.LANGUAGE,
            "sortByDate": config.SORT_BY_DATE,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": config.TEAM_CALENDAR_SHA,
            }
        },
    }

    resp = gql_post(payload)
    items = resp.get("data", {}).get("teamCalendar", [])
    if not isinstance(items, list):
        raise RuntimeError("Unexpected response: teamCalendar not a list")
    return items


def fetch_match_detail(match_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed match info (location, referee, score).
    Only works if MATCH_DETAIL_SHA is configured.
    """
    if not config.MATCH_DETAIL_SHA:
        return None

    payload = {
        "operationName": "GetMatchDetail",
        "variables": {
            "matchId": match_id,
            "language": config.LANGUAGE,
        },
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": config.MATCH_DETAIL_SHA,
            }
        },
    }

    resp = gql_post(payload)
    detail = resp.get("data", {}).get("matchDetail")
    if isinstance(detail, dict):
        return detail
    return None


# -----------------------------
# Field formatting helpers
# -----------------------------
def get_team_name(team_obj: Any) -> str:
    if isinstance(team_obj, dict):
        return (team_obj.get("name") or "").strip()
    return ""


def format_officials(officials: Any) -> str:
    """
    Format referee names.
    """
    if not isinstance(officials, list):
        return ""
    names: List[str] = []
    for o in officials:
        if not isinstance(o, dict):
            continue
        first_ = (o.get("firstName") or "").strip()
        last_ = (o.get("lastName") or "").strip()
        full = f"{first_} {last_}".strip()
        if full:
            names.append(full)
    return ", ".join(names)


def format_score(outcome: Any) -> str:
    """
    Format match score.
    """
    if not isinstance(outcome, dict):
        return ""
    hg = outcome.get("homeTeamGoals")
    ag = outcome.get("awayTeamGoals")
    if hg is None or ag is None:
        return ""
    score = f"{hg}-{ag}"
    hp = outcome.get("homeTeamPenaltiesScored")
    ap = outcome.get("awayTeamPenaltiesScored")
    if hp is not None and ap is not None:
        score += f" (strafschoppen {hp}-{ap})"
    return score


def format_location(location_obj: Any) -> str:
    """
    Format venue location.
    """
    if not isinstance(location_obj, dict):
        return ""
    name = (location_obj.get("name") or "").strip()
    addr = (location_obj.get("address") or "").strip()
    postal = (location_obj.get("postalCode") or "").strip()
    city = (location_obj.get("city") or "").strip()

    parts = []
    if name:
        parts.append(name)
    line2 = ", ".join([p for p in [addr, " ".join([postal, city]).strip()] if p])
    if line2:
        parts.append(line2)

    return " — ".join(parts).strip()


# -----------------------------
# ICS building
# -----------------------------
def build_ics(team_id: str, events: List[Dict[str, Any]], state: Dict[str, Dict[str, Any]]) -> bytes:
    """
    Build iCalendar feed in Flemish.
    """
    # Get team name for calendar title
    team_name = "Team" + f" {team_id}"
    if events and len(events) > 0:
        team_info = fetch_team_info(team_id)
        if team_info:
            team_name = team_info.get("name", team_name)
    
    cal = Calendar()
    cal.add("prodid", "-//Voetbal Vlaanderen Kalender//NL")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", team_name)
    cal.add("x-wr-timezone", config.TZ)

    now = dt.datetime.now(TZ)

    for item in events:
        match_id = str(item.get("id") or "").strip()
        if not match_id:
            continue

        # Parse start time
        start_raw = item.get("startDateTime") or item.get("startTime") or item.get("startDate")
        start_dt = parse_dt(start_raw)
        if not start_dt:
            continue
        end_dt = start_dt + dt.timedelta(minutes=config.MATCH_DURATION_MIN)

        home = get_team_name(item.get("homeTeam")) or "Thuis"
        away = get_team_name(item.get("awayTeam")) or "Uit"

        base_title = f"{home} - {away}"

        series = ""
        if isinstance(item.get("series"), dict):
            series = (item["series"].get("name") or "").strip()

        score = format_score(item.get("outcome"))
        officials = format_officials(item.get("officials"))
        match_state = (item.get("state") or "").strip()

        location = ""
        detail = fetch_match_detail(match_id)
        if detail:
            location = format_location(detail.get("location"))
            score = format_score(detail.get("outcome")) or score
            officials = format_officials(detail.get("officials")) or officials
            match_state = (detail.get("state") or "").strip() or match_state
            if isinstance(detail.get("series"), dict):
                series = (detail["series"].get("name") or "").strip() or series

        # Title with score if available
        title = base_title + (f" ({score})" if score else "")

        # Description in Flemish
        desc_lines = []
        if series:
            desc_lines.append(f"Competitie: {series}")
        if officials:
            desc_lines.append(f"Scheidsrechter: {officials}")
        if score:
            desc_lines.append(f"Uitslag: {score}")
        if match_state:
            desc_lines.append(f"Status: {match_state}")
        desc_lines.append(f"Wedstrijd ID: {match_id}")

        description = "\n".join(desc_lines)

        # Stable UID
        uid = f"vv-{match_id}@datalake.rbfa"

        # Detect changes
        core = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "title": title,
            "location": location,
            "description": description,
        }
        new_sig = stable_sig(core)

        prev = state.get(uid, {})
        prev_sig = prev.get("sig")
        prev_seq = int(prev.get("seq", 0) or 0)

        # Bump sequence only if changed
        seq = prev_seq if prev_sig == new_sig else prev_seq + 1
        state[uid] = {"sig": new_sig, "seq": seq}

        # Build event
        ev = Event()
        ev.add("uid", uid)
        ev.add("sequence", seq)
        ev.add("dtstamp", now)
        ev.add("dtstart", start_dt)
        ev.add("dtend", end_dt)
        ev.add("summary", title)

        if location:
            ev.add("location", location)

        ev.add("description", description)

        cal.add_component(ev)

    return cal.to_ical()


def generate_ics_for_team(team_id: str) -> bytes:
    """
    Main function to generate ICS for a specific team.
    Called by Flask app or can be run standalone.
    """
    state = load_state(team_id)
    calendar_items = fetch_team_calendar(team_id)
    ics_bytes = build_ics(team_id, calendar_items, state)
    save_state(team_id, state)
    return ics_bytes


def main() -> None:
    """
    CLI entry point.
    Usage: python refresh_team_ics.py <team_id>
    """
    if len(sys.argv) > 1:
        team_id = sys.argv[1]
    else:
        team_id = config.TEAM_ID
    
    print(f"Generating ICS for team {team_id}...")
    ics_bytes = generate_ics_for_team(team_id)
    
    # Write to static directory
    static_dir = os.path.join(config.BASE_DIR, "static")
    os.makedirs(static_dir, exist_ok=True)
    output_path = os.path.join(static_dir, f"{team_id}.ics")
    
    with open(output_path, "wb") as f:
        f.write(ics_bytes)
    
    print(f"✓ Wrote ICS to {output_path}")


if __name__ == "__main__":
    main()
