<?php
// ⚠️ Nur für privaten Gebrauch — keine öffentliche Nutzung!
// Diese Datei fungiert als einfacher Proxy, um CORS/X-Frame-Schutz zu umgehen.

$url = $_GET['url'] ?? '';

if (filter_var($url, FILTER_VALIDATE_URL)) {
    // Sicherheitsheader setzen
    header('Content-Type: text/html; charset=utf-8');
    header('Access-Control-Allow-Origin: *');
    header('Cache-Control: no-cache, no-store, must-revalidate');

    // Inhalt abrufen und ausgeben
    $context = stream_context_create([
        'http' => [
            'header' => "User-Agent: Mozilla/5.0 (compatible; PrivateProxy/1.0)\r\n"
        ]
    ]);
    echo @file_get_contents($url, false, $context);
} else {
    http_response_code(400);
    echo "Ungültige URL.";
}
?>
