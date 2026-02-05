# Voetbal Vlaanderen → iCalendar (ICS)

🔗 **Live demo:** [your-deployment-url.com](https://your-deployment-url.com)

Genereer een iCalendar feed voor elk Voetbal Vlaanderen / RBFA team door middel van RBFA's publieke GraphQL endpoint. Abonneer je op de feed in Apple Calendar, Google Calendar, Outlook of eender welke andere kalender-app.

## ✨ Features

- 🎯 **Multi-team ondersteuning** - Werkt voor elk Voetbal Vlaanderen team
- 🌐 **Gebruiksvriendelijke web interface** - Simpel team ID invoeren en valideren
- 📱 **Volledig responsive** - Werkt perfect op mobiel en desktop
- ⚡ **Smart caching** - Automatische updates elke 3 dagen
- 🇧🇪 **Vlaams** - Alle labels en instructies in het Nederlands
- 🎨 **Schone UI** - Modern, voetbal-thema design
- 🔄 **Geen cron jobs nodig** - On-demand generatie met intelligente caching

## 🚀 Hoe het werkt

### Voor eindgebruikers

1. Bezoek de website
2. Vul je team ID in (vind je op [voetbalvlaanderen.be](https://www.voetbalvlaanderen.be))
3. Valideer dat het juiste team wordt getoond (naam + logo)
4. Kopieer de kalender URL of klik op "Abonneer"
5. Voeg de URL toe aan je kalender-app
6. Klaar! Je kalender wordt automatisch bijgewerkt

### Technisch

- **Landing page**: Gebruikers voeren team ID in via een webformulier
- **Team validatie**: Flask API roept GraphQL aan om team info op te halen
- **ICS generatie**: Bij eerste request wordt `.ics` bestand gegenereerd
- **Smart caching**: Bestand wordt 3 dagen gecached (match schedules wijzigen zelden)
- **Automatische updates**: Kalender-apps pollen periodiek de URL, wat automatisch vernieuwing triggert na 3 dagen
- **Per-team state**: Elk team krijgt eigen state file voor SEQUENCE tracking

## 📋 Vereisten

- Python 3.9+
- Flask
- requests
- python-dateutil
- icalendar

## 🛠️ Installatie & Gebruik

### Lokaal draaien

```bash
# Clone de repo
git clone https://github.com/mathiasmaes/voetbalvlaanderen-ics.git
cd voetbalvlaanderen-ics

# Installeer dependencies
pip install -r requirements.txt

# Start de Flask app
export BASE_DIR=.
python app.py
```

Bezoek dan [http://localhost:5000](http://localhost:5000)

### Handmatige ICS generatie (CLI)

Je kan ook rechtstreeks een ICS bestand genereren:

```bash
python refresh_team_ics.py <team_id>
```

Dit genereert `static/<team_id>.ics`

### Deployment (PythonAnywhere)

1. **Upload bestanden** naar PythonAnywhere
2. **Stel environment variabelen in** via bash console of web tab:
   ```bash
   export BASE_DIR=/home/<username>/mysite
   export MATCH_DETAIL_SHA=<optioneel voor match details>
   ```
3. **Configureer WSGI**:
   ```python
   import sys
   sys.path.insert(0, '/home/<username>/mysite')
   
   from app import app as application
   ```
4. **Herlaad web app** en je bent klaar!

## ⚙️ Configuratie

Alle configuratie gebeurt via environment variabelen (zie `config.py`):

### Verplicht
- `BASE_DIR` - Map waar `static/` en `state/` worden aangemaakt

### Optioneel
- `MATCH_DETAIL_SHA` - GraphQL hash voor match details (locatie, scheidsrechter, score)
- `TZ` - Tijdzone (default: `Europe/Brussels`)
- `MATCH_DURATION_MIN` - Wedstrijd duur in minuten (default: `60`)
- `LANGUAGE` - Taal voor GraphQL queries (default: `nl`)
- `SORT_BY_DATE` - Sortering (default: `asc`)

## 📂 Project Structuur

```
voetbalvlaanderen-ics/
├── app.py                  # Flask web app (routes + API)
├── refresh_team_ics.py     # ICS generatie logica
├── config.py               # Configuratie (env vars)
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Landing page (responsive UI)
├── static/                # Gegenereerde ICS bestanden
│   └── <team_id>.ics     # Per-team kalender feeds
└── state/                 # State tracking per team
    └── <team_id>.json    # Event signatures & sequences
```

## 🔍 Team ID vinden

1. Ga naar [voetbalvlaanderen.be](https://www.voetbalvlaanderen.be)
2. Zoek je team via de zoekfunctie
3. Open het team profiel
4. Het team ID staat in de URL:
   ```
   https://www.voetbalvlaanderen.be/team/<TEAM_ID>/
   ```

## 🎨 Features van de UI

- **Modern design** met voetbal thema en gradient kleuren
- **Responsive layout** - werkt perfect op mobiel
- **Team logo weergave** - toont logo indien beschikbaar via API
- **Live validatie** - Controleert team info voor bevestiging
- **Copy-to-clipboard** - Eenvoudig URL kopiëren
- **Directe subscribe knop** - One-click abonneren
- **Stap-voor-stap instructies** - Voor Apple Calendar en Google Calendar

## 🔄 Update Strategie

**Geen cron jobs nodig!** Het systeem gebruikt smart caching:

1. **Eerste request**: ICS wordt gegenereerd en opgeslagen
2. **Volgende 3 dagen**: Gecachte versie wordt direct geserveerd (instant)
3. **Na 3 dagen**: Nieuwe versie wordt gegenereerd bij volgende request
4. **Kalender apps**: Pollen automatisch de URL, wat updates triggert

### Waarom 3 dagen?

- Voetbalwedstrijden worden zelden binnen 3 dagen gewijzigd
- Reduceert server load significant
- Kalender apps cachen zelf ook, dus real-time niet nodig
- Balans tussen actualiteit en efficiency

## 🧪 Testen

```bash
# Test ICS generatie voor specifiek team
python refresh_team_ics.py 347325

# Controleer of bestand is aangemaakt
ls -lh static/347325.ics

# Test Flask endpoints
curl http://localhost:5000/
curl http://localhost:5000/team/347325.ics
```

## 🤝 Bijdragen

Bijdragen zijn welkom! Open een issue of pull request.

## 📝 Licentie

MIT License - zie LICENSE bestand voor details.

## 🙏 Credits

- Data via [RBFA Datalake GraphQL API](https://datalake-prod2018.rbfa.be/graphql)
- Gebouwd voor de Voetbal Vlaanderen community

## 💡 Tips

### Voor administrators

- Monitor disk usage in `static/` en `state/` mappen
- Oude team bestanden kunnen handmatig verwijderd worden indien nodig
- Logs checken met `tail -f /var/log/pythonanywhere.log`

### Voor gebruikers

- Kalender updates kunnen tot 6 uur duren (afhankelijk van je kalender app)
- Bij problemen: verwijder het abonnement en voeg opnieuw toe
- Controleer dat je team ID correct is via voetbalvlaanderen.be

## 🐛 Troubleshooting

**"Team niet gevonden"**
- Controleer of team ID correct is
- Probeer het team te zoeken op voetbalvlaanderen.be

**"Kalender wordt niet bijgewerkt"**
- Sommige kalender apps updaten slechts 1x per dag
- Verwijder het abonnement en voeg opnieuw toe
- Controleer internetverbinding

**"Fout bij genereren kalender"**
- Check server logs
- Mogelijk tijdelijk probleem met RBFA API
- Probeer later opnieuw

---

⭐ **Star deze repo** als je het nuttig vindt!
