# Wiederherstellung 1.0.7

Bestehende Homebrew-Adresse aktualisieren:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

1.0.7 entfernt die Puffer-Auswahl, zusätzlichen nativen Zeit-Schwellen und die zugehörige Rückfalllogik aus 1.0.6 nach der Rückmeldung über Soundaussetzer. Der native Video-Quellcode, die Einstellungsseite und die deutsche Übersetzung sind bytegenau auf upstream 1.0.0 zurückgesetzt. Ausschließlich userBufferCtrl=false bleibt im ursprünglichen Load-Payload. Alte gespeicherte nativeBufferSeconds-Werte werden nicht mehr gelesen; kein Zurücksetzen und keine Deinstallation erforderlich.

Die vorhandenen Korrekturen bleiben erhalten: HTTP-206-Verbindungswiederverwendung, erzwungene DTS-Konvertierung, native Play-Taste und Cursor-Aktivierung nach Ausblenden ausschließlich durch Scrollrad-Drehen. Es werden keine weiteren Streaming-Ansätze implementiert, bevor der Nutzer eine Option gewählt hat.

Release-Prüfungen: ARM-Build, 14 Audiotests, 4 Medientasten-Fälle, exakter Quellvergleich für die Rücknahme und den Erhalt der übrigen Änderungen sowie Prüfung der endgültigen IPK gegen alle 330 Original-Dateneinträge. Programm und Versionsangabe sind die einzigen abweichenden App-Dateien. Originalbibliotheken, Ressourcen, Lizenzen, eingebettete App-Konfiguration und Dateiberechtigungen bleiben erhalten. Der eingebaute Updater bleibt auf dem Originalprojekt.

Die bestehenden Cursor- und Transporttests bleiben unverändert; die Tests des verworfenen Puffer-Experiments sind aus dem aktuellen Stand entfernt und in Git erhalten. Reale TV-Wiedergabe lässt sich aus dieser Umgebung nicht überprüfen.

Untersuchung und bewertete, noch nicht umgesetzte Optionen: https://github.com/pacev93/stremio/tree/04201dba38815a759e0780a2203757b6b7bedacf/docs/streaming-range-fix.md
