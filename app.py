"""
app.py
------
Tiny Flask app that serves the generated ICS file.

Your Apple Calendar subscription URL will be:
https://<yourusername>.pythonanywhere.com/team.ics
"""

from pathlib import Path

from flask import Flask, Response, abort

import config

app = Flask(__name__)

ICS_PATH = Path(config.ICS_OUTPUT_PATH)

@app.get("/team.ics")
def team_ics():
    if not ICS_PATH.exists():
        abort(404, "ICS not generated yet. Run refresh_team_ics.py once.")
    data = ICS_PATH.read_bytes()
    return Response(data, mimetype="text/calendar; charset=utf-8")
