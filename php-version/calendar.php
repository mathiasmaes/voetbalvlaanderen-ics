<?php
/**
 * calendar.php
 * ICS calendar generator with 3-day smart caching
 * Generates and serves iCalendar feeds for Voetbal Vlaanderen teams
 */

// Configuration
define('CACHE_DURATION', 3 * 24 * 3600); // 3 days in seconds
define('GRAPHQL_URL', 'https://datalake-prod2018.rbfa.be/graphql');
define('TEAM_CALENDAR_SHA', '3f0441e6723b9852b4f0cff2c872f4aa674c5de2d23589efc70c7a4ffb7f6383');
define('MATCH_DETAIL_SHA', ''); // Optional: set for match details
define('TIMEZONE', 'Europe/Brussels');
define('MATCH_DURATION_MIN', 60);
define('LANGUAGE', 'nl');

// Get team_id from query string
$team_id = $_GET['team_id'] ?? '';
$team_id = trim($team_id);

if (empty($team_id) || !ctype_alnum($team_id)) {
    http_response_code(400);
    die('Ongeldig team ID');
}

// Setup directories
$base_dir = __DIR__;
$cache_dir = $base_dir . '/cache';
$state_dir = $base_dir . '/state';

if (!file_exists($cache_dir)) {
    mkdir($cache_dir, 0755, true);
}
if (!file_exists($state_dir)) {
    mkdir($state_dir, 0755, true);
}

$cache_file = $cache_dir . '/' . $team_id . '.ics';
$state_file = $state_dir . '/' . $team_id . '.json';

// Check if cached file exists and is fresh
$should_regenerate = true;
if (file_exists($cache_file)) {
    $file_age = time() - filemtime($cache_file);
    if ($file_age < CACHE_DURATION) {
        $should_regenerate = false;
    }
}

// Regenerate if needed
if ($should_regenerate) {
    try {
        $ics_content = generate_ics($team_id, $state_file);
        file_put_contents($cache_file, $ics_content);
    } catch (Exception $e) {
        http_response_code(500);
        die('Fout bij genereren kalender: ' . $e->getMessage());
    }
}

// Serve the ICS file
header('Content-Type: text/calendar; charset=utf-8');
header('Content-Disposition: inline; filename="team_' . $team_id . '.ics"');
header('Cache-Control: public, max-age=' . CACHE_DURATION);
readfile($cache_file);

/**
 * Generate ICS content for a team
 */
function generate_ics($team_id, $state_file) {
    // Load state
    $state = load_state($state_file);
    
    // Fetch calendar from GraphQL
    $calendar_items = fetch_team_calendar($team_id);
    
    // Get team name
    $team_name = get_team_name($team_id, $calendar_items);
    
    // Build ICS
    $ics = build_ics_content($team_id, $team_name, $calendar_items, $state);
    
    // Save state
    save_state($state_file, $state);
    
    return $ics;
}

/**
 * Fetch team calendar from RBFA GraphQL
 */
function fetch_team_calendar($team_id) {
    $payload = [
        'operationName' => 'GetTeamCalendar',
        'variables' => [
            'teamId' => $team_id,
            'language' => LANGUAGE,
            'sortByDate' => 'asc'
        ],
        'extensions' => [
            'persistedQuery' => [
                'version' => 1,
                'sha256Hash' => TEAM_CALENDAR_SHA
            ]
        ]
    ];
    
    $ch = curl_init(GRAPHQL_URL);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'Content-Type: application/json',
        'Accept: application/json, text/plain, */*',
        'Origin: https://www.voetbalvlaanderen.be',
        'Referer: https://www.voetbalvlaanderen.be/',
        'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    ]);
    curl_setopt($ch, CURLOPT_TIMEOUT, 45);
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code !== 200) {
        throw new Exception('RBFA API fout');
    }
    
    $result = json_decode($response, true);
    
    if (isset($result['errors'])) {
        throw new Exception('GraphQL fout');
    }
    
    return $result['data']['teamCalendar'] ?? [];
}

/**
 * Get team name from calendar items
 */
function get_team_name($team_id, $calendar_items) {
    if (empty($calendar_items)) {
        return 'Team ' . $team_id;
    }
    
    foreach ($calendar_items as $match) {
        $home = $match['homeTeam'] ?? [];
        $away = $match['awayTeam'] ?? [];
        
        if (isset($home['id']) && (string)$home['id'] === $team_id) {
            return $home['name'] ?? 'Team ' . $team_id;
        }
        if (isset($away['id']) && (string)$away['id'] === $team_id) {
            return $away['name'] ?? 'Team ' . $team_id;
        }
    }
    
    return 'Team ' . $team_id;
}

/**
 * Build ICS file content
 */
function build_ics_content($team_id, $team_name, $calendar_items, &$state) {
    $tz = new DateTimeZone(TIMEZONE);
    $now = new DateTime('now', $tz);
    
    $lines = [];
    $lines[] = 'BEGIN:VCALENDAR';
    $lines[] = 'VERSION:2.0';
    $lines[] = 'PRODID:-//Voetbal Vlaanderen Kalender//NL';
    $lines[] = 'CALSCALE:GREGORIAN';
    $lines[] = 'METHOD:PUBLISH';
    $lines[] = 'X-WR-CALNAME:' . escape_ics($team_name);
    $lines[] = 'X-WR-TIMEZONE:' . TIMEZONE;
    
    foreach ($calendar_items as $item) {
        $match_id = $item['id'] ?? '';
        if (empty($match_id)) continue;
        
        // Parse start time
        $start_raw = $item['startDateTime'] ?? $item['startTime'] ?? $item['startDate'] ?? null;
        if (!$start_raw) continue;
        
        try {
            $start_dt = new DateTime($start_raw, $tz);
        } catch (Exception $e) {
            continue;
        }
        
        $end_dt = clone $start_dt;
        $end_dt->modify('+' . MATCH_DURATION_MIN . ' minutes');
        
        // Get team names
        $home = ($item['homeTeam']['name'] ?? 'Thuis');
        $away = ($item['awayTeam']['name'] ?? 'Uit');
        
        // Get series/competition
        $series = '';
        if (isset($item['series']['name'])) {
            $series = $item['series']['name'];
        }
        
        // Get score
        $score = format_score($item['outcome'] ?? null);
        
        // Get match state
        $match_state = strtolower(trim($item['state'] ?? ''));
        
        // Get officials
        $officials = format_officials($item['officials'] ?? []);
        
        // Build title: Add score at START if game is finished
        if (in_array($match_state, ['played', 'afgelopen', 'finished']) && $score) {
            $title = $score . ' ' . $home . ' - ' . $away;
        } else {
            // For upcoming/planned games, no score in title
            $title = $home . ' - ' . $away;
        }
        
        // Build description (in Flemish) - properly escaped for ICS
        $desc_parts = [];
        if ($series) {
            $desc_parts[] = 'Competitie: ' . $series;
        }
        if ($officials) {
            $desc_parts[] = 'Scheidsrechter: ' . $officials;
        }
        if ($score) {
            $desc_parts[] = 'Uitslag: ' . $score;
        }
        if (isset($item['state'])) {
            $desc_parts[] = 'Status: ' . $item['state'];
        }
        $desc_parts[] = 'Wedstrijd ID: ' . $match_id;
        
        // Join with escaped newlines for ICS format
        $description = implode('\\n', $desc_parts);
        
        // Location (if available)
        $location = '';
        if (isset($item['location'])) {
            $location = format_location($item['location']);
        }
        
        // Generate stable UID
        $uid = 'vv-' . $match_id . '@datalake.rbfa';
        
        // Calculate signature for change detection
        $core = [
            'start' => $start_dt->format('c'),
            'end' => $end_dt->format('c'),
            'title' => $title,
            'location' => $location,
            'description' => $description
        ];
        $new_sig = md5(json_encode($core));
        
        // Get previous state
        $prev = $state[$uid] ?? ['sig' => null, 'seq' => 0];
        $prev_sig = $prev['sig'];
        $prev_seq = (int)$prev['seq'];
        
        // Bump sequence only if changed
        $seq = ($prev_sig === $new_sig) ? $prev_seq : $prev_seq + 1;
        $state[$uid] = ['sig' => $new_sig, 'seq' => $seq];
        
        // Build VEVENT
        $lines[] = 'BEGIN:VEVENT';
        $lines[] = 'UID:' . $uid;
        $lines[] = 'SEQUENCE:' . $seq;
        $lines[] = 'DTSTAMP:' . $now->format('Ymd\\THis\\Z');
        $lines[] = 'DTSTART;TZID=' . TIMEZONE . ':' . $start_dt->format('Ymd\\THis');
        $lines[] = 'DTEND;TZID=' . TIMEZONE . ':' . $end_dt->format('Ymd\\THis');
        $lines[] = 'SUMMARY:' . escape_ics($title);
        
        if ($location) {
            $lines[] = 'LOCATION:' . escape_ics($location);
        }
        
        $lines[] = 'DESCRIPTION:' . $description;
        $lines[] = 'END:VEVENT';
    }
    
    $lines[] = 'END:VCALENDAR';
    
    return implode("\r\n", $lines);
}

/**
 * Format score
 */
function format_score($outcome) {
    if (!is_array($outcome)) return '';
    
    $hg = $outcome['homeTeamGoals'] ?? null;
    $ag = $outcome['awayTeamGoals'] ?? null;
    
    if ($hg === null || $ag === null) return '';
    
    $score = $hg . '-' . $ag;
    
    $hp = $outcome['homeTeamPenaltiesScored'] ?? null;
    $ap = $outcome['awayTeamPenaltiesScored'] ?? null;
    
    if ($hp !== null && $ap !== null) {
        $score .= ' (strafschoppen ' . $hp . '-' . $ap . ')';
    }
    
    return $score;
}

/**
 * Format officials/referees
 */
function format_officials($officials) {
    if (!is_array($officials)) return '';
    
    $names = [];
    foreach ($officials as $official) {
        if (!is_array($official)) continue;
        
        $first = trim($official['firstName'] ?? '');
        $last = trim($official['lastName'] ?? '');
        $full = trim($first . ' ' . $last);
        
        if ($full) {
            $names[] = $full;
        }
    }
    
    return implode(', ', $names);
}

/**
 * Format location
 */
function format_location($location) {
    if (!is_array($location)) return '';
    
    $name = trim($location['name'] ?? '');
    $addr = trim($location['address'] ?? '');
    $postal = trim($location['postalCode'] ?? '');
    $city = trim($location['city'] ?? '');
    
    $parts = [];
    if ($name) {
        $parts[] = $name;
    }
    
    $line2_parts = [];
    if ($addr) $line2_parts[] = $addr;
    if ($postal || $city) $line2_parts[] = trim($postal . ' ' . $city);
    
    if (!empty($line2_parts)) {
        $parts[] = implode(', ', $line2_parts);
    }
    
    return implode(' — ', $parts);
}

/**
 * Escape text for ICS format
 */
function escape_ics($text) {
    $text = str_replace('\\', '\\\\', $text);
    $text = str_replace(',', '\\,', $text);
    $text = str_replace(';', '\\;', $text);
    $text = str_replace("\n", '\\n', $text);
    $text = str_replace("\r", '', $text);
    return $text;
}

/**
 * Load state from JSON file
 */
function load_state($state_file) {
    if (!file_exists($state_file)) {
        return [];
    }
    
    $content = file_get_contents($state_file);
    $state = json_decode($content, true);
    
    return is_array($state) ? $state : [];
}

/**
 * Save state to JSON file
 */
function save_state($state_file, $state) {
    file_put_contents($state_file, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}
