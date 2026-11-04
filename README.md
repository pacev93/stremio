# Update 1.0.13

Bestehende Homebrew-Adresse:
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren. Keine Deinstallation.

Nach expliziter App-/Fenster-Deaktivierung fordert Origin bei bestätigter Rückkehr
oder echter App-Navigation einmal die native Fensteraktivierung an. Der Aufruf
ist gegen Fokusereignis-Schleifen gesichert. Cursor-Show, Leave, bloßes Shown und
gepollter Tastaturfokus lösen keine Aktivierung aus. Das Cursorbild wird nach
Wiederherstellung der gewünschten Darstellung bei tatsächlichem App-Mausfokus
einmal ausdrücklich neu gezeichnet. Rad-Aktivierung bleibt erhalten.

Mögliche Größenänderungen der nativen Fläche werden für logische Mauskoordinaten,
Drawable/Grafik sowie bestehende Video-/Crop-Rechtecke aktualisiert. Die
Mediensitzung wird nicht neu geladen; DTS, Bufferautomatik und Seeking bleiben
in ihrer bisherigen Form erhalten. Keine Diagnoseanzeige, keine globalen
Cursor-Schalter, kein Vordergrund-Servicepolling.

80 lokale Szenarien bestanden: 32 Cursor-, 24 Fokus-, sechs Geometrie- und
18 Seek-Prüfungen. ARM-Build und finaler Paketvergleich erfolgreich; alle 330
Original-Dateirechte, Ressourcen, Bibliotheken und App-Konfiguration erhalten.
Die konkrete CX-System-SDL und das Compositorverhalten bleiben am TV zu prüfen.

Details: https://github.com/pacev93/stremio/tree/4d263298c960d5879e0dd0783176525356a9e04c/docs/streaming-range-fix.md
