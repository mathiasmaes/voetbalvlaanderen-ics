#!/usr/bin/env python3
"""
refresh_team_ics.py
-------------------
Run this once per day on PythonAnywhere.

What it does:
1) Fetch the full team calendar from RBFA datalake (GraphQL persisted query)
2) Optionally fetch match details for EACH match (location/referee/score)
3) Generate an iCalendar (.ics) feed file
4) Maintain a small state.json so we can:
   - keep each event UID stable (no duplicates)
   - bump SEQUENCE only when something actually changed
     (Apple Calendar updates are much more reliable with SEQUENCE)

This script is safe for a public GitHub repo:
- no credentials required
- no cookies
- all configuration via environment variables
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
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
def load_state(path: str) -> Dict[str, Dict[str, Any]]:
    """
    Loads state.json (if it exists).

    We store per-event:
      state[uid] = {"sig": "<hash>", "seq": <int>}

    sig: signature of the event's important fields
    seq: the SEQUENCE number we last used for that event
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        # If file is corrupted, fail gracefully by starting fresh
        return {}


def save_state(path: str, state: Dict[str, Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def stable_sig(obj: Any) -> str:
    """
    Turn a Python object into a stable SHA1 hash.
    Any change in obj => different signature.
    """
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


# -----------------------------
# Date/time parsing
# -----------------------------
def parse_dt(val: Optional[str]) -> Optional[dt.datetime]:
    """
    RBFA datalake returns ISO timestamps that sometimes have NO timezone
    (e.g. '2025-12-18T19:00:00').

    We interpret such timestamps as local Europe/Brussels time.
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
    Basic GraphQL POST helper.

    Note:
    - No auth headers required (public data)
    - We mimic the website's Origin/Referer because some servers are picky.
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


def fetch_team_calendar() -> List[Dict[str, Any]]:
    """
    Calls the persisted query GetTeamCalendar you captured.

    Returns the list: data.teamCalendar[]
    """
    payload = {
        "operationName": "GetTeamCalendar",
        "variables": {
            "teamId": config.TEAM_ID,
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
        raise RuntimeError("Unexpected response shape: data.teamCalendar is not a list")
    return items


def fetch_match_detail(match_id: str) -> Optional[Dict[str, Any]]:
    """
    Calls the match detail persisted query (you need MATCH_DETAIL_SHA set).

    Why is this optional?
    - If you don't set MATCH_DETAIL_SHA, we still produce a basic calendar.
    - If you DO set it, we enrich events with location/referee/score.

    Return: data.matchDetail object (dict) or None.
    """
    if not config.MATCH_DETAIL_SHA:
        return None

    payload = {
        "operationName": "GetMatchDetail",  # operation name usually this; if yours differs, change it.
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
    officials is typically a list of dicts like:
      { firstName, lastName, function: "referee", personAssigned: true, ... }
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
    outcome typically has:
      homeTeamGoals, awayTeamGoals, (optional penalties)
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
        score += f" (pens {hp}-{ap})"
    return score


def format_location(location_obj: Any) -> str:
    """
    From your screenshot, matchDetail.location includes:
      name, address, postalCode, city

    We combine into a single LOCATION string that map apps can use.
    """
    if not isinstance(location_obj, dict):
        return ""
    name = (location_obj.get("name") or "").strip()
    addr = (location_obj.get("address") or "").strip()
    postal = (location_obj.get("postalCode") or "").strip()
    city = (location_obj.get("city") or "").strip()

    # Build "Name — Address, Postal City"
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
def build_ics(events: List[Dict[str, Any]], state: Dict[str, Dict[str, Any]]) -> bytes:
    """
    Convert match dicts into an iCalendar feed.

    Efficiency note:
    - We always regenerate the ICS file daily (simple + robust).
    - BUT we only bump SEQUENCE for events whose signature changed.
      That’s the “only update what changed” part.
    """
    cal = Calendar()
    cal.add("prodid", "-//Voetbal Vlaanderen DIY Feed//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", "FC De Ploegmoats (DIY)")
    cal.add("x-wr-timezone", config.TZ)

    now = dt.datetime.now(TZ)

    for item in events:
        match_id = str(item.get("id") or "").strip()
        if not match_id:
            continue

        # Base info from teamCalendar
        start_raw = item.get("startDateTime") or item.get("startTime") or item.get("startDate")
        start_dt = parse_dt(start_raw)
        if not start_dt:
            continue
        end_dt = start_dt + dt.timedelta(minutes=config.MATCH_DURATION_MIN)

        home = get_team_name(item.get("homeTeam")) or "Home"
        away = get_team_name(item.get("awayTeam")) or "Away"

        # Requested: hyphen instead of 'vs'
        base_title = f"{home} - {away}"

        series = ""
        if isinstance(item.get("series"), dict):
            series = (item["series"].get("name") or "").strip()

        # Some info might exist already in teamCalendar…
        score = format_score(item.get("outcome"))
        officials = format_officials(item.get("officials"))
        match_state = (item.get("state") or "").strip()

        # …but matchDetail is where location is guaranteed (based on your click example).
        location = ""
        detail = fetch_match_detail(match_id)
        if detail:
            # overwrite/enrich using detail (usually more complete)
            # score/ref can also be more accurate here than in calendar list
            location = format_location(detail.get("location"))
            score = format_score(detail.get("outcome")) or score
            officials = format_officials(detail.get("officials")) or officials
            match_state = (detail.get("state") or "").strip() or match_state
            if isinstance(detail.get("series"), dict):
                series = (detail["series"].get("name") or "").strip() or series

        # Title: optionally append score if we have one
        title = base_title + (f" ({score})" if score else "")

        # Description lines
        desc_lines = []
        if series:
            desc_lines.append(f"Competition: {series}")
        if officials:
            desc_lines.append(f"Referee: {officials}")
        if score:
            desc_lines.append(f"Score: {score}")
        if match_state:
            desc_lines.append(f"State: {match_state}")
        desc_lines.append(f"Match ID: {match_id}")

        description = "\n".join(desc_lines)

        # Stable UID => calendar updates the same event
        uid = f"vv-{match_id}@datalake.rbfa"

        # Signature => detect if anything important changed
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

        # Only bump sequence if something changed
        seq = prev_seq if prev_sig == new_sig else prev_seq + 1
        state[uid] = {"sig": new_sig, "seq": seq}

        # Build VEVENT
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


def main() -> None:
    state = load_state(config.STATE_PATH)

    # 1) fetch full calendar
    calendar_items = fetch_team_calendar()

    # 2) build ICS (and update state in-memory)
    ics_bytes = build_ics(calendar_items, state)

    # 3) write output
    os.makedirs(os.path.dirname(config.ICS_OUTPUT_PATH), exist_ok=True)
    with open(config.ICS_OUTPUT_PATH, "wb") as f:
        f.write(ics_bytes)

    # 4) persist state
    save_state(config.STATE_PATH, state)

    print(f"OK: wrote {len(calendar_items)} calendar items to {config.ICS_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
