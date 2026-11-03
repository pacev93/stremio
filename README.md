# Testversion 1.0.5

Bestehende Adresse im Homebrew Channel aktualisieren:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

1.0.5 ergänzt den nativen LG-Play-Scancode 450 und verbessert den inaktiven Cursor nach Pfeiltasten und automatischem Ausblenden. Einzelne kleine Bewegungen und Cursor-Show-Meldungen aktivieren den Zeiger nicht. Erst eine deutliche zusammenhängende Bewegung stellt die Zeigerbedienung wieder her. Klicks im inaktiven Modus bestätigen den Tastaturfokus und treffen keinen unsichtbaren Zeigerort.

Der Bildwechsel mit transparentem Cursor, die Wiederherstellung beim Fokusverlust und die übrigen Schutzmaßnahmen aus 1.0.4 bleiben erhalten. Keine Cursor-Sichtbarkeits-API wird aufgerufen. Die separate Play-Taste verwendet eine dokumentierte private LG-SDL-Zuordnung; die bisherigen Web-App-Tastencodes wurden entfernt. Medien-/private Tastencodes werden im bestehenden App-Log protokolliert, ohne zusätzliche Protokollierung von Text- oder PIN-Eingaben.

Der Nutzer bestätigt DTS-zu-Dolby mit 1.0.4. Player-/Konverter- und Streamingcode sind gegenüber 1.0.4 unverändert. Originalbibliotheken, Ressourcen, Lizenzen und eingebettete App-Konfiguration bleiben erhalten. Als Update installieren, ohne vorher zu deinstallieren. Der eingebaute Updater bleibt auf dem Originalprojekt.

Prüfungen: ARM-Build, 20 Cursorfälle (12 mit echter Desktop-SDL, 8 Backend-/Fehlerfälle), 4 Medien-Tasten-Fälle, 14 unveränderte Audioprüfungen und 12 Transportfälle. Alle 330 Daten-Einträge haben die Originalberechtigungen. Die Testanzeige emuliert den LG-Compositor nicht; die Play-Referenztabelle stammt von anderer LG-Firmware. Die Bestätigung auf dem CX steht aus.

Quellcode und Analyse: https://github.com/pacev93/stremio/tree/b5bd045d4ab2e6fd9ee433b82b4975b4c6b4bbc9/docs/streaming-range-fix.md
