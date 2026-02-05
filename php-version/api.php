<?php
/**
 * api.php
 * Team validation API endpoint
 * Calls RBFA GraphQL to fetch team information
 */

header('Content-Type: application/json');

// Only allow POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit;
}

// Get POST data
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!isset($data['team_id']) || empty(trim($data['team_id']))) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Vul een team ID in']);
    exit;
}

$team_id = trim($data['team_id']);

// Validate team_id is alphanumeric
if (!ctype_alnum($team_id)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Ongeldig team ID formaat']);
    exit;
}

// Configuration
$graphql_url = 'https://datalake-prod2018.rbfa.be/graphql';
$team_calendar_sha = '3f0441e6723b9852b4f0cff2c872f4aa674c5de2d23589efc70c7a4ffb7f6383';

// Build GraphQL request
$graphql_payload = [
    'operationName' => 'GetTeamCalendar',
    'variables' => [
        'teamId' => $team_id,
        'language' => 'nl',
        'sortByDate' => 'asc'
    ],
    'extensions' => [
        'persistedQuery' => [
            'version' => 1,
            'sha256Hash' => $team_calendar_sha
        ]
    ]
];

// Make HTTP request
$ch = curl_init($graphql_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($graphql_payload));
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'Accept: application/json, text/plain, */*',
    'Origin: https://www.voetbalvlaanderen.be',
    'Referer: https://www.voetbalvlaanderen.be/',
    'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
]);
curl_setopt($ch, CURLOPT_TIMEOUT, 45);

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curl_error = curl_error($ch);
curl_close($ch);

if ($curl_error) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Fout bij verbinden met RBFA API']);
    exit;
}

if ($http_code !== 200) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'RBFA API fout']);
    exit;
}

$result = json_decode($response, true);

// Check for GraphQL errors
if (isset($result['errors'])) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'GraphQL fout: ' . json_encode($result['errors'])]);
    exit;
}

// Extract team info
$calendar_items = $result['data']['teamCalendar'] ?? [];

if (empty($calendar_items)) {
    http_response_code(404);
    echo json_encode(['success' => false, 'error' => 'Team niet gevonden of geen wedstrijden']);
    exit;
}

// Extract team info from first match
$first_match = $calendar_items[0];
$home_team = $first_match['homeTeam'] ?? [];
$away_team = $first_match['awayTeam'] ?? [];

$team_name = null;
$team_logo = null;

// Determine which team matches our team_id
if (isset($home_team['id']) && (string)$home_team['id'] === $team_id) {
    $team_name = $home_team['name'] ?? null;
    $team_logo = $home_team['logo'] ?? $home_team['logoUrl'] ?? null;
} elseif (isset($away_team['id']) && (string)$away_team['id'] === $team_id) {
    $team_name = $away_team['name'] ?? null;
    $team_logo = $away_team['logo'] ?? $away_team['logoUrl'] ?? null;
}

if (!$team_name) {
    // Try to find team in other matches
    foreach ($calendar_items as $match) {
        $home = $match['homeTeam'] ?? [];
        $away = $match['awayTeam'] ?? [];
        
        if (isset($home['id']) && (string)$home['id'] === $team_id) {
            $team_name = $home['name'] ?? null;
            $team_logo = $home['logo'] ?? $home['logoUrl'] ?? null;
            break;
        } elseif (isset($away['id']) && (string)$away['id'] === $team_id) {
            $team_name = $away['name'] ?? null;
            $team_logo = $away['logo'] ?? $away['logoUrl'] ?? null;
            break;
        }
    }
}

if (!$team_name) {
    http_response_code(404);
    echo json_encode(['success' => false, 'error' => 'Team informatie niet gevonden']);
    exit;
}

// Success response
echo json_encode([
    'success' => true,
    'id' => $team_id,
    'name' => $team_name,
    'logo' => $team_logo
]);
