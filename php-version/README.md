# Voetbal Vlaanderen iCalendar - PHP Version

⚽ **PHP versie voor one.com hosting**

Deze map bevat een volledig werkende PHP implementatie van de Voetbal Vlaanderen kalender generator, specifiek ontworpen voor one.com webhosting.

## 📁 Bestanden

```
php-version/
├── index.php          # Landing page met team validatie formulier
├── api.php            # API endpoint voor team validatie
├── calendar.php       # ICS generator met smart caching
├── .htaccess          # Apache configuratie
├── cache/             # Gegenereerde ICS bestanden (auto-aangemaakt)
├── state/             # Event state tracking (auto-aangemaakt)
└── README.md          # Deze file
```

## 🚀 Installatie op one.com

### Stap 1: Upload bestanden

1. Log in op je one.com control panel
2. Ga naar **File Manager**
3. Navigeer naar je public_html map (of een submap waar je de tool wilt hosten)
4. Upload ALLE bestanden uit de `php-version/` map:
   - `index.php`
   - `api.php`
   - `calendar.php`
   - `.htaccess`

### Stap 2: Zet permissies

1. Maak de volgende mappen aan (indien nog niet bestaand):
   - `cache/`
   - `state/`

2. Zet de juiste permissies via File Manager:
   - `cache/` → **755** (read/write/execute voor owner)
   - `state/` → **755** (read/write/execute voor owner)

### Stap 3: Test de installatie

Bezoek je website:
```
http://jouwdomein.com/
```

Je zou nu de landing page moeten zien met het team validatie formulier.

## ✅ Verificatie

Test de volledige workflow:

1. **Landing page**: Vul een team ID in (bijv. `347325`)
2. **Validatie**: Controleer dat team naam en logo verschijnen
3. **Calendar URL**: Klik op "Abonneer" of kopieer de URL
4. **ICS generatie**: Bezoek de calendar URL rechtstreeks:
   ```
   http://jouwdomein.com/calendar.php?team_id=347325
   ```
5. **Cache verificatie**: Check of `cache/347325.ics` bestaat

## 🔧 Configuratie

Alle configuratie staat in `calendar.php` (bovenaan het bestand):

```php
define('CACHE_DURATION', 3 * 24 * 3600);  // 3 dagen cache
define('TIMEZONE', 'Europe/Brussels');     // Tijdzone
define('MATCH_DURATION_MIN', 60);          // Wedstrijd duur
define('LANGUAGE', 'nl');                  // Taal (Nederlands)
```

### Optioneel: Match details

Voor extra informatie (locatie, scheidsrechter):

1. Vind de GraphQL hash voor match details (zie hoofd README)
2. Update in `calendar.php`:
   ```php
   define('MATCH_DETAIL_SHA', 'jouw_hash_hier');
   ```

## 🎨 Aanpassingen

### Design wijzigen

Open `index.php` en pas de CSS aan in de `<style>` sectie:
- Kleuren: wijzig gradient in `body { background: ... }`
- Lettertype: wijzig `font-family` properties
- Layout: pas padding/margins aan

### Andere taal

Alle teksten staan in:
- `index.php` (UI labels)
- `api.php` (foutmeldingen)
- `calendar.php` (ICS beschrijvingen)

Zoek en vervang de Nederlandse teksten.

## 📊 Hoe het werkt

### Smart Caching (3 dagen)

```
Gebruiker vraagt calendar.php?team_id=347325
    ↓
Bestaat cache/347325.ics EN jonger dan 3 dagen?
    ├─ JA → Serveer direct (instant)
    └─ NEE → Genereer nieuw ICS bestand
            ↓
        Roep RBFA GraphQL API aan
            ↓
        Bouw ICS bestand
            ↓
        Sla op in cache/347325.ics
            ↓
        Serveer aan gebruiker
```

### State Management

Elk team heeft een `state/<team_id>.json` bestand dat bijhoudt:
- **Event signatures**: MD5 hash van wedstrijd details
- **Sequence numbers**: Versienummer per event

Dit zorgt ervoor dat kalender-apps alleen updaten als er echt iets veranderd is.

## 🐛 Troubleshooting

### "Internal Server Error"

**Oorzaak**: PHP syntax error of verkeerde permissies

**Oplossing**:
1. Check PHP error log in one.com control panel
2. Controleer dat `cache/` en `state/` permissies 755 zijn
3. Test of PHP curl enabled is:
   ```php
   <?php phpinfo(); ?>
   ```
   Upload als `test.php` en zoek naar "curl"

### "Team niet gevonden"

**Oorzaak**: Fout team ID of RBFA API probleem

**Oplossing**:
1. Verifieer team ID op voetbalvlaanderen.be
2. Test API direct in browser:
   ```
   http://jouwdomein.com/api.php
   ```
   (POST request met `{"team_id": "347325"}`)

### Cache wordt niet vernieuwd

**Oorzaak**: Bestand permissions of disk space

**Oplossing**:
1. Verwijder handmatig oude cache bestanden via File Manager
2. Check disk space in one.com control panel
3. Verlaag cache duration in `calendar.php`

### Kalender-app update niet

**Normaal gedrag**: 
- Apple Calendar: update elke 4-6 uur
- Google Calendar: update elke 8-24 uur

**Force update**:
1. Verwijder abonnement in kalender-app
2. Voeg opnieuw toe

## 🔒 Beveiliging

### Bescherming tegen misbruik

De `.htaccess` blokkeert:
- Toegang tot `.json` state files
- Toegang tot `.log` bestanden
- Directory listing

### Optioneel: Rate limiting

Voor extra bescherming, voeg toe aan `calendar.php`:

```php
// Simpele rate limiting
session_start();
$last_request = $_SESSION['last_calendar_request'] ?? 0;
if (time() - $last_request < 10) {
    http_response_code(429);
    die('Te veel verzoeken, probeer over 10 seconden opnieuw');
}
$_SESSION['last_calendar_request'] = time();
```

## 📈 Performance

### Disk usage

Per team:
- Cache: ~10-50 KB per ICS bestand
- State: ~5-20 KB per JSON bestand

100 teams = ~5-7 MB totaal (zeer acceptabel voor one.com)

### Snelheid

- **Cache hit** (< 3 dagen oud): instant (< 50ms)
- **Cache miss** (regenerate): 2-5 seconden
- **RBFA API calls**: 1-3 seconden per team

## 🧹 Onderhoud

### Oude cache opruimen

Creëer `cleanup.php`:

```php
<?php
// Verwijder cache bestanden ouder dan 7 dagen
$cache_dir = __DIR__ . '/cache';
$max_age = 7 * 24 * 3600;

foreach (glob($cache_dir . '/*.ics') as $file) {
    if (time() - filemtime($file) > $max_age) {
        unlink($file);
    }
}

echo 'Cleanup voltooid';
```

Voer handmatig uit via browser of cron (als one.com dit support).

## 💡 Tips

1. **Test eerst lokaal**: Gebruik XAMPP/MAMP om lokaal te testen
2. **Backup**: Maak regelmatig backup van `state/` directory
3. **Monitor**: Check regelmatig je disk usage in one.com panel
4. **SSL**: Schakel HTTPS in voor betere beveiliging

## 🆚 Verschillen met Python versie

| Feature | Python (Flask) | PHP (one.com) |
|---------|----------------|---------------|
| Deployment | PythonAnywhere | one.com |
| Dependencies | pip packages | Geen (built-in) |
| Performance | Vergelijkbaar | Vergelijkbaar |
| Caching | Identiek | Identiek |
| Functionaliteit | 100% | 100% |
| Onderhoud | Makkelijker | Simpeler |

Beide versies hebben **identieke features** en **gebruikerservaring**.

## 🎯 Live Example

Bezoek de demo:
```
http://jouwdomein.com/
```

## 📞 Support

Problemen? Check:
1. Deze README (Troubleshooting sectie)
2. Hoofd README in parent directory
3. GitHub Issues: [github.com/mathiasmaes/voetbalvlaanderen-ics](https://github.com/mathiasmaes/voetbalvlaanderen-ics)

---

✅ **Klaar voor productie!** Upload en geniet van je Voetbal Vlaanderen kalender feeds.
