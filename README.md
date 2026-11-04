# Update 1.0.12

Bestehende Homebrew-Adresse:
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren. Keine Deinstallation.

Die zusätzliche Cursor-Leave-Sperre aus 1.0.11 ist zurückgenommen, nachdem
auch normales Ausblenden und Wiederaktivieren ohne LG-Menü ausfiel.
Zugestellte Mausbewegungen, linke Tastendrücke und Radereignisse lösen jetzt
eine veraltete Hintergrundsperre auch bei Fenster-ID 0 oder veralteten
SDL-Fokus-/Sichtbarkeitsangaben. Explizit fremde Fenster bleiben ausgeschlossen.
Bewegung allein aktiviert den ausgeblendeten Zeiger weiterhin nicht;
die Rad-Aktivierung und der vorhandene Klick-/Idle-Pfad bleiben erhalten.

Funktionales Update ohne Diagnoseanzeige. Keine Vordergrund-Serviceabfrage
und keine globalen Cursor-Schalter. Wiedergabe, DTS, Puffer und Spulen unverändert.

50 lokale Cursor-/Fokusprüfungen, ARM-Build und Paketprüfung bestanden.
Alle 330 Original-Dateirechte, Ressourcen, Bibliotheken und mitgelieferte
App-Konfiguration bleiben erhalten. Das Cursorverhalten auf dem CX ist
weiterhin am TV zu bestätigen.

Details: https://github.com/pacev93/stremio/tree/f3e0da29b439e489f6dee29e0d2c99fa7e5c67d9/docs/streaming-range-fix.md
