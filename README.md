# Testversion 1.0.4

Bestehende Repository-Adresse im Homebrew Channel aktualisieren:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

1.0.4 enthält den bestehenden HTTP-206-Verbindungsfix, einen neuen Cursorbild-Wechsel, die Korrektur der erzwungenen DTS-Konvertierung und zusätzliche LG-Medientastenwerte. Als Update installieren, ohne vorher zu deinstallieren.

Der Cursorfix tauscht nur das Bild gegen ein transparentes Bild aus und stellt es bei Bewegung, Fokusverlust und regulärem Beenden wieder her. Die verworfenen Cursor-Sichtbarkeits-APIs werden nicht verwendet. Falls die Cursorbild-Funktionen nicht verfügbar sind, bleibt der normale Zeiger erhalten.

Die DTS-Einstellung „Umwandeln“ übergeht eine früher gespeicherte negative HEVC/HLS-Beobachtung. Ein einzelner Wiedergabefehler sperrt künftige Versuche nicht dauerhaft. Gewähltes DTS wird vor automatischen Ersatzspuren konvertiert, auch bei automatischer Sprachauswahl. Die Konverterbibliothek ist unverändert; Mehrkanal-DTS wird als AC3 5.1 ausgegeben, Stereo bleibt Stereo.

Prüfungen: ARM-Build, 12 Transportfälle, 15 Cursorfälle (7 mit echter Desktop-SDL, 8 mit kontrollierten Backend-/Fehlergrenzen), 14 Audioentscheidungen, 4 Medien-Tasten-Fälle sowie alle 330 Paketeinträge gegen das Original. Originalbibliotheken, Ressourcen, Lizenzen und eingebettete App-Konfiguration bleiben erhalten. Die Tests bilden den LG-Compositor und die tatsächliche Medienwiedergabe nicht nach; ein Test auf dem TV steht aus.

1.0.1/1.0.2 hatten einen Cursorfehler mit systemweiten Nebenwirkungen. Dieser wurde in 1.0.3 zurückgenommen; 1.0.4 verwendet einen anderen Weg. Der eingebaute Updater bleibt auf dem Originalprojekt.

Quellcode und Analyse: https://github.com/pacev93/stremio/tree/96ec8a0d2a20265e9c5d791480b6965b07389205/docs/streaming-range-fix.md
