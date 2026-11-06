# Update 1.0.16

Bestehende Homebrew-Adresse:
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren. Keine Deinstallation.

HLS-Segmentanfragen dürfen mehrere Segmente vorausliegen oder Wiederholungen
sein. Sie brechen die laufende Konverterausgabe nicht mehr ab. Bisher setzte
bereits das übernächste angefragte Segment ein Stoppsignal für die aktuelle
Ausgabe; diese Entscheidung ist auf 1.0.15 lokal reproduziert.

Ein tatsächlicher nativer Seek in die aktive eigene Playlist stoppt die alte
Arbeit und verwirft wartende Anfragen von davor. Das Signal kommt erst nach
dem bisherigen Seek-Debounce. Alte Anfragen können ein neueres Stoppsignal
nicht zurücksetzen. Indexierte Seeks starten weder Konverter noch native
Mediensitzung neu. Andere Medien-URLs werden ignoriert.

Im vorhandenen indexlosen TS-Sonderpfad ersetzt eine neue Anfrage weiterhin
die alte. Bei mehreren wartenden Anfragen läuft nur die neueste, auch wenn
Antwortheader verzögert fertig werden. Die dort nötige zeitbasierte native
Neuöffnung bleibt erhalten.

Kein neuer Datencache oder Vorlade-Proxy. 4-MiB-Dateiabrufe und 8-MiB-Rücklesering
bleiben erhalten, ebenso Cursor, DTS-Auswahl und native Pufferautomatik.
Stoppsignale werden wie bisher an den vorhandenen Prüfpunkten beachtet;
laufende synchrone Netzwerk-/Socket-Aufrufe haben keinen neuen Sofortabbruch.

59 Szenarien bestanden: 13 Nebenläufigkeits-, 20 Seek-, zwölf echte HTTP-Leser-
und 14 DTS-Policyfälle. ARM-Build und finales Paket erfolgreich geprüft:
330 Original-Dateirechte, Ressourcen, Bibliotheken und mitgelieferte Schlüssel
erhalten. Die Wirkung auf die Hänger des CX bleibt am TV zu bestätigen.

Details: https://github.com/pacev93/stremio/tree/2c1f9e17c9037bd7661b1b0957cf4361090e7b9a/docs/streaming-range-fix.md
