# Testversion 1.0.6

Bestehende Adresse im Homebrew Channel aktualisieren:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Nach Ausblenden bleibt der Cursor gesperrt, bis das Scrollrad gedreht wird. Bewegung, Cursor-Show-Meldungen und OK aktivieren ihn nicht. Home bekommt beim Fokuswechsel das ursprüngliche Cursorbild; die App-Sperre bleibt bei der Rückkehr erhalten. Keine globale Cursor-Sichtbarkeits-API wird verwendet.

Neu: Einstellungen → Wiedergabe → Videopuffer mit Auto (Standard), 10 s, 20 s oder 30 s. Auf webOS 5/6 werden für entfernte HTTP-/HTTPS-Quellen native bufferControl-Schwellen angefordert; der lokale DTS-Konverter und andere Firmware behalten die Originaloptionen. Für den Vergleich mit derselben Datei zunächst Auto, dann 20 s wählen und den Stream neu öffnen.

Die Schwellen sind kein fester MB-Cache und keine bestätigte Änderung der physischen Pufferkapazität. Dokumentiert ist die Wirkung auf HLS einer webOS-6-Firmware; ob direkte MKVs auf dem CX die Werte beachten, muss am TV geprüft werden. Bei Ablehnung oder fehlendem ersten Bild wird einmal mit den Originaloptionen neu geladen. Das Zeitlimit ist Ziel + 8 Sekunden; nach dem ersten Bild erfolgt kein automatischer Neustart wegen späteren Bufferings. Größere Ziele können den Start verzögern und beheben keinen dauerhaft zu geringen Zufluss.

Der bisherige HTTP-Range-Fix, die funktionierende DTS-Konvertierung und die Play-Zuordnung bleiben erhalten. Die Originalbibliotheken, vorhandenen Ressourcen, Lizenzen und eingebettete App-Konfiguration bleiben erhalten; die deutsche Übersetzung erhält lediglich drei Texte für die neue Einstellung. Als Update installieren, ohne vorher zu deinstallieren. Der eingebaute Updater bleibt auf dem Originalprojekt.

Prüfungen: ARM-Build, 21 Cursorfälle (13 mit echter Desktop-SDL, 8 Backend-/Fehlerfälle), 10 native Puffer-Payload-/Rückfallfälle, 14 Audioentscheidungen, 4 Medien-Tasten-Fälle, 12 Transportfälle und alle 330 Paketdaten-Einträge mit Originalberechtigungen. Die effektive Medienpufferung wird durch die Tests nicht emuliert.

Analyse einschließlich Stremio-Issue #2771 und Nuvio-Vergleich: https://github.com/pacev93/stremio/tree/c6f88c7a5e382bb53ce67dca5b20d6139d968432/docs/streaming-range-fix.md
