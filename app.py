"""
app.py
------
Flask app that:
1. Shows a landing page for users to enter their team ID
2. Validates team ID and shows team name/logo
3. Serves dynamically generated ICS files with smart caching (3-day TTL)

Calendar subscription URL format:
https://<yourusername>.pythonanywhere.com/team/<team_id>.ics
"""

import os
from pathlib import Path
from datetime import datetime

from flask import Flask, Response, abort, render_template, jsonify, request

import config
from refresh_team_ics import generate_ics_for_team, fetch_team_info

app = Flask(__name__)

# Cache duration: 3 days (in seconds)
CACHE_DURATION = 3 * 24 * 3600  # 259200 seconds


@app.route("/")
def index():
    """Landing page with team ID input form"""
    return render_template("index.html")


@app.route("/api/validate-team", methods=["POST"])
def validate_team():
    """
    AJAX endpoint to validate team ID and return team info.
    Returns: {"success": true, "name": "...", "logo": "...", "id": "..."}
    """
    data = request.get_json()
    team_id = data.get("team_id", "").strip()
    
    if not team_id:
        return jsonify({"success": False, "error": "Vul een team ID in"}), 400
    
    try:
        team_info = fetch_team_info(team_id)
        if not team_info:
            return jsonify({"success": False, "error": "Team niet gevonden"}), 404
        
        return jsonify({
            "success": True,
            "id": team_id,
            "name": team_info.get("name", "Onbekend team"),
            "logo": team_info.get("logo"),
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Fout bij ophalen team: {str(e)}"}), 500


@app.route("/team/<team_id>.ics")
def team_ics(team_id):
    """
    Serve ICS file for a specific team.
    Uses smart caching: regenerates only if file is older than 3 days.
    """
    # Sanitize team_id (only alphanumeric)
    if not team_id.isalnum():
        abort(400, "Ongeldig team ID")
    
    # Define file path
    static_dir = Path(config.BASE_DIR) / "static"
    static_dir.mkdir(exist_ok=True)
    ics_path = static_dir / f"{team_id}.ics"
    
    # Check if cached file exists and is fresh
    now = datetime.now().timestamp()
    should_regenerate = True
    
    if ics_path.exists():
        file_age = now - ics_path.stat().st_mtime
        if file_age < CACHE_DURATION:
            should_regenerate = False
    
    # Regenerate if needed
    if should_regenerate:
        try:
            ics_bytes = generate_ics_for_team(team_id)
            ics_path.write_bytes(ics_bytes)
        except Exception as e:
            abort(500, f"Fout bij genereren kalender: {str(e)}")
    
    # Serve the file
    data = ics_path.read_bytes()
    response = Response(data, mimetype="text/calendar; charset=utf-8")
    
    # Add caching headers (tell calendar apps to cache for 3 days)
    response.headers["Cache-Control"] = f"public, max-age={CACHE_DURATION}"
    response.headers["Content-Disposition"] = f'inline; filename="team_{team_id}.ics"'
    
    return response


if __name__ == "__main__":
    app.run(debug=True)
