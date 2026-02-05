# Changelog

Alle belangrijke wijzigingen aan dit project worden gedocumenteerd in dit bestand.

## [2.0.0] - 2026-02-05

### 🎉 Grote Release: Multi-Team Support + PHP Versie

#### ✨ Nieuwe Features

**Multi-Team Ondersteuning**
- ✅ Ondersteunt nu ELKE Voetbal Vlaanderen team (niet meer hardcoded)
- ✅ Webformulier voor team ID validatie
- ✅ Team logo en naam weergave voor bevestiging
- ✅ Unieke kalender URL per team
- ✅ Per-team state tracking voor SEQUENCE nummers

**PHP Versie voor one.com**
- 🆕 Volledig werkende PHP implementatie in `/php-version/` folder
- 🆕 Identieke functionaliteit als Flask versie
- 🆕 Geen dependencies - upload en klaar
- 🆕 Apache .htaccess configuratie included
- 🆕 Uitgebreide README met installatie instructies

**Smart Caching (3 dagen)**
- ⚡ Automatische caching van ICS bestanden
- ⚡ Regenereert alleen na 3 dagen
- ⚡ Geen cron jobs meer nodig
- ⚡ HTTP cache headers voor optimale performance

**UI Verbeteringen**
- 🎨 Volledig responsive design voor mobiel en desktop
- 🎨 Modern voetbal-thema met gradient kleuren
- 🎨 Loading states en error handling
- 🎨 Copy-to-clipboard functionaliteit
- 🎨 Direct subscribe knoppen
- 🎨 Stap-voor-stap instructies in Vlaams

**Vlaams (Nederlands)**
- 🇧🇪 Alle UI teksten in het Nederlands
- 🇧🇪 ICS beschrijvingen in Vlaams (Competitie, Scheidsrechter, Uitslag)
- 🇧🇪 Foutmeldingen in het Nederlands
- 🇧🇪 Instructies voor Vlaamse gebruikers

#### 🔧 Technische Wijzigingen

**Python/Flask Versie**
- Refactored `app.py` met nieuwe routes:
  - `GET /` - Landing page
  - `POST /api/validate-team` - Team validatie
  - `GET /team/<team_id>.ics` - Dynamische ICS feeds
- Refactored `refresh_team_ics.py`:
  - `generate_ics_for_team(team_id)` - Herbruikbare functie
  - `fetch_team_info(team_id)` - Team info ophalen
  - Per-team state management in `state/<team_id>.json`
- Nieuwe `templates/index.html` met responsive UI
- Updated `config.py` voor flexibele configuratie

**PHP Versie**
- `php-version/index.php` - Landing page
- `php-version/api.php` - GraphQL team validatie
- `php-version/calendar.php` - ICS generatie met caching
- `php-version/.htaccess` - Apache configuratie
- Cache en state directories worden automatisch aangemaakt

**State Management**
- Van `state.json` naar `state/<team_id>.json` structuur
- MD5/SHA1 signatures voor change detection
- SEQUENCE bumping alleen bij echte wijzigingen
- Persistent across regenerations

**Documentatie**
- Uitgebreide README updates voor beide versies
- PHP-specifieke README in `/php-version/`
- Troubleshooting guides
- Deployment instructies voor PythonAnywhere en one.com
- Comparison table Python vs PHP

#### 🐛 Bug Fixes
- Fixed timezone handling voor wedstrijden zonder explicit timezone
- Fixed CORS issues door correcte headers naar RBFA API
- Fixed ICS escaping voor speciale karakters
- Improved error handling voor ontbrekende team data

#### 📝 Breaking Changes

**⚠️ Migratie nodig van v1.0 naar v2.0**

Als je de oude versie gebruikt met hardcoded team ID:

1. **State file**: Verplaats `state.json` naar `state/<jouw_team_id>.json`
2. **ICS file**: Hernoem `static/team.ics` naar `static/<jouw_team_id>.ics`
3. **URL wijziging**: Verander subscription URL:
   - Oud: `https://jouwsite.com/team.ics`
   - Nieuw: `https://jouwsite.com/team/<jouw_team_id>.ics`
4. **Environment vars**: `TEAM_ID` is nu optioneel (enkel voor CLI gebruik)

## [1.0.0] - Initiële Release

### Features
- Single-team kalender generator
- Hardcoded team ID in config
- Daily cron job voor updates
- GraphQL integratie met RBFA API
- Basic Flask web server
- ICS generatie met state tracking

---

## Toekomstige Plannen

### Overwogen voor v2.1
- [ ] Email notificaties bij schema wijzigingen
- [ ] Admin dashboard voor populaire teams
- [ ] Automatische cleanup van oude cache files
- [ ] Rate limiting voor API misbruik preventie
- [ ] Meerdere talen (Frans, Engels) naast Nederlands
- [ ] Dark mode voor UI
- [ ] QR code generator voor snelle mobile subscriptions

### Ideeën voor v3.0
- [ ] Database integratie (SQLite/PostgreSQL)
- [ ] User accounts en persoonlijke dashboard
- [ ] Multiple team subscriptions per gebruiker
- [ ] Push notificaties voor wedstrijd reminders
- [ ] Integration met populaire messaging apps
- [ ] API voor third-party integraties

---

**Feedback?** Open een [GitHub Issue](https://github.com/mathiasmaes/voetbalvlaanderen-ics/issues)!
