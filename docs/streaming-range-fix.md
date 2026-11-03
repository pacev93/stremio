# Streaming-Fix und Rücknahme der Cursor-Änderung

## Aktueller Stand: 1.0.3

Version 1.0.3 enthält den HTTP-Range-Fix und stellt das gesamte Cursor-Verhalten
des Originals wieder her. Unter `src/` unterscheidet sich nur noch
`src/core/net.c` vom Originalcommit
`051818e55cf38caed42d597fbcb05bdd3fc5bbd9`.

Die Cursor-Steuerung aus 1.0.1/1.0.2 wurde zurückgenommen: Der Nutzer meldete,
dass sich der Zeiger weder in Origin noch im LG-Homebildschirm wieder aktivieren
ließ und schließlich ein TV-Neustart nötig war. Die Tests mit simulierten
UI-/SDL-Funktionen hatten diese systemweite Wirkung nicht erfasst. Die native
Cursor-Steuerung und der SDL-Disable-Fallback sind vollständig entfernt.
Damit gilt wieder die ursprüngliche Einschränkung: Der Cursor kann sichtbar
bleiben. Diese Einschränkung wird bis zu einer separat überprüfbaren Lösung
akzeptiert, statt die Zeigersteuerung des Fernsehers zu blockieren.

Der zusätzlich gemeldete Fehler „Pause funktioniert, Play danach nicht“ ist
noch offen. Die Fernbedienungszuordnung ist in dieser Wiederherstellungsversion
ebenfalls unverändert gegenüber dem Original.

Homebrew-Repository:

```text
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json
```

1.0.3 als Update installieren, ohne die App vorher zu deinstallieren.
Der eingebaute Updater bleibt unverändert und verweist auf das Originalprojekt.

## Warum das Buffering wahrscheinlich besser wurde

Origins eigener Range-Leser bestätigte den letzten Datenblock einer vollständig
empfangenen `206 Partial Content`-Antwort mit null statt der empfangenen Länge.
Für libcurl ist das ein Abbruch (`CURLE_WRITE_ERROR`): Die Verbindung wird
verworfen. Origins Aufrufer sah trotzdem `NR_OK`, weil die angeforderten Bytes
bereits vorlagen. Der Transportfehler blieb deshalb verborgen.

Der Fix bestätigt vollständige 206-Antworten korrekt. Vier aufeinanderfolgende
Ranges verwenden im Regressionstest eine HTTP-Verbindung statt vier.
Bei HTTPS entfallen dadurch wiederholte Verbindungsaufbauten und zusätzliche
TCP-/TLS-Arbeit. Gerade bei vielen kleinen MKV-Zugriffen können Latenz und
zusätzliche Last neben dem Videostream ins Gewicht fallen.

Der Nutzer berichtet unter 1.0.2, dass das Buffering behoben zu sein scheint.
Das passt zur Korrektur, ist aber ohne vergleichbare TV-/Backend-Traces kein
abschließender Ursachennachweis. Geändert ist Origins eigener Leser für
MKV-Metadaten/Untertitel und den Konvertierungspfad. Der direkte Videodownload
im geschlossenen LG-Mediendienst wird durch diesen Fix nicht umgebaut.

## Vergleich mit dem öffentlichen offiziellen Player

Origin 1.0.0 und der Ausgangsstand dieses Forks stimmen im Anwendungscode
überein. Vergleichsbasis des offiziellen offenen Clients ist
[stremio-web v5.0.0-beta.43](https://github.com/Stremio/stremio-web/blob/v5.0.0-beta.43/package.json)
mit `@stremio/stremio-video` 0.0.101, Commit
`fa1f32674159a0c0e2903cba44d4d41cd461e19f`.
Auch 0.0.103 wurde geprüft. Die Archive wurden gegen ihre npm-Integritätsangaben
geprüft. Die tatsächlich installierte LG-Store-Binärversion war nicht auslesbar;
der öffentliche Quellstand ist daher keine Bestätigung ihres exakten Inhalts.

| Bereich | Öffentlicher offizieller webOS-Player | Origin 1.0.0 |
| --- | --- | --- |
| Direkte Wiedergabe | URL im HTML-Videoelement, Download/Decodierung durch webOS | Direkter Aufruf von `com.webos.media/load`, Download/Decodierung durch webOS |
| Pufferoptionen | Keine explizite `bufferControl`-Vorgabe im untersuchten `WebOsVideo` | `userBufferCtrl:false` und `useSeekableRanges:true` |
| MKV-Zusatzdaten | Plattformspuren, optional `/tracks` des gebündelten Servers | Eigener Worker für Header, Kapitel, Cues und Untertitelblöcke; ohne Index Scanning |
| Datei-Hash | Direkter `withVideoParams`-Wrapper übernimmt Addon-Angaben | Untertitelabfrage kann erste und letzte 64 KiB lesen |
| Nicht unterstützter Ton | Plattform-/Server-abhängig | Eigener Konverter über 512-KiB-/2-MiB-Ranges, Ausgabe als lokales HLS |

Offizielle Quellen:
[WebOsVideo](https://github.com/Stremio/stremio-video/blob/fa1f32674159a0c0e2903cba44d4d41cd461e19f/src/WebOsVideo/WebOsVideo.js),
[Player-Auswahl](https://github.com/Stremio/stremio-video/blob/fa1f32674159a0c0e2903cba44d4d41cd461e19f/src/StremioVideo/selectVideoImplementation.js),
[Video-Parameter](https://github.com/Stremio/stremio-video/blob/fa1f32674159a0c0e2903cba44d4d41cd461e19f/src/withVideoParams/withVideoParams.js).

AIOStreams wurde bei Commit
[`49cc6fa39af54a5bdb244d897cdf6008a7ebb594`](https://github.com/Viren070/AIOStreams/tree/49cc6fa39af54a5bdb244d897cdf6008a7ebb594)
untersucht. Die native NNTP-Engine öffnet pro HTTP-Anfrage einen Byte-Stream,
nutzt dabei aber einen gemeinsamen Segmentcache/-pool und warme Dateisitzungen.
Zusätzliche weit entfernte MKV-/Hash-Zugriffe können mit der Wiedergabe um
Ressourcen konkurrieren; sie verwerfen nicht zwangsläufig den gesamten Cache.
Die genaue Serverversion und die Belastung beim Nutzer sind nicht gemessen.

[Stremio-Issue #2771](https://github.com/Stremio/stremio-bugs/issues/2771)
beschreibt eine mögliche native Downloadgrenze bei hochbitratigen Dateien auf
einem anderen LG-Modell. Das ist ein separater möglicher Engpass.
[Issue #2655](https://github.com/Stremio/stremio-bugs/issues/2655) betrifft
flackernde Untertitel. [Origin-Issue #1](https://github.com/stremio-origin/webos/issues/1)
beschreibt den ursprünglich dauerhaft sichtbaren Cursor.

## Paket und Prüfungen

Grundlage ist das verifizierte Original-IPK 1.0.0 mit SHA-256:

```text
949d4eabafb7290258eae8ad9e405e7f8f31f4c030071039258f382ca7769a42
```

Die Originalbibliotheken `libsbengine.so` und `libsbdts.so`, Ressourcen,
Übersetzungen, Lizenzen und eingebettete Trakt-/TMDB-App-Konfiguration bleiben
erhalten. Die Anwendungsdateien unterscheiden sich nur beim neu gebauten
Programm und der Versionsangabe in `appinfo.json`.

1.0.1 hatte einen Paketierungsfehler: Das Programm trug `0704` statt `0755`;
Datendateien trugen `0604` statt `0644`. Seit 1.0.2 werden die Zugriffsrechte
jedes Archiv-Eintrags aus dem Original übernommen. Die Paketprüfung verwirft
1.0.1 und überprüft die endgültige Veröffentlichungsdatei.

```sh
source /workspace/stremio-env/activate.sh
python3 tests/net/run.py --sdl-include "$SDK/usr/include"
python3 tools/scrub_ipk.py candidate.ipk --reference original-1.0.0.ipk
python3 tests/package/check.py original-1.0.0.ipk candidate.ipk
```

Die zwölf Transportfälle umfassen feste und Chunked-Antworten, Wiederverwendung,
Redirects, Dateiende, ignorierte/falsche Ranges, unterbrochene/überlange
Antworten sowie HTTP-Fehler und Timeouts. Die früheren Cursor-Tests sind mit der
fehlgeschlagenen Implementierung aus dem aktuellen Stand entfernt; ihre
Historie bleibt in Git nachvollziehbar. Die Cursor-Rücknahme wird zusätzlich
durch den vollständigen Quellvergleich gegen das Original und das Fehlen der
neu eingeführten Cursor-Steuerung im ausgelieferten Programm geprüft.
