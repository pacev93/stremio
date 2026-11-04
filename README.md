# Update 1.0.8

Bestehende Homebrew-Adresse unverändert:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Als Update installieren, ohne Deinstallation oder Zurücksetzen.

Cursor: verlorene Klickzustände werden ohne Auslösen der alten Aktion abgebrochen.
Bestätigter SDL-Fokus kann eine verlorene Rückkehrmeldung reparieren; ein expliziter
App-Hintergrund bleibt geschützt. Das ausgeblendete Cursorbild wird bei Bedarf erneut
gesetzt. Ausschließlich Drehen am Rad aktiviert den ausgeblendeten Zeiger.

Spulen: konvertierte Streams beginnen eine neue Konverter- und Mediensitzung;
alte Segmentanfragen laufen aus. Direkte Rückwärtssprünge laden die Mediensitzung
neu. Zielposition, Tonspur, Untertitel und Pause werden erhalten. Zusätzliche
Ladezeit beim Spulen ist möglich.

Textuntertitel: Header, Audio-/DV-Daten und Kapitel bleiben verfügbar. Der Index
und Dialogdaten werden erst bei Bedarf gelesen, nur die angeforderte Textspur im
vorhandenen Zeitfenster. Off/externe Untertitel erfordern kein laufendes Sammeln
aller Sprachen. Auto-sync kann vorübergehend eine Referenzspur anfordern und gibt
sie danach frei. Auch Index-Wiederholungen warten nach dem Ausschalten.

Native Pufferautomatik und DTS-Umwandlung bleiben erhalten. Kein neuer Proxy,
keine Änderung der Range-Größen, keine neue Containerbibliothek. Die Statistik
kennzeichnet lokale Konvertierung und ausgeschaltete Untertitel korrekt.

83 lokale Regressionsszenarien und ARM-Build erfolgreich. Endgültige IPK mit allen
330 Original-Dateneinträgen verglichen: Rechte und Ressourcen unverändert, nur
Programm und Versionsangabe weichen ab. Die eingebettete Original-App-Konfiguration
bleibt erhalten. Der eingebaute Updater verweist weiterhin auf das Originalprojekt.
Die geschlossene LG-CX-Pipeline ist aus dieser Umgebung nicht erreichbar; Wiedergabe,
Seek und Cursor bleiben auf dem TV zu bestätigen.

Quellen und Details: https://github.com/pacev93/stremio/tree/a8d8eaa6d7d7da37867ffbe4eb309d02c73038d5/docs/streaming-range-fix.md
