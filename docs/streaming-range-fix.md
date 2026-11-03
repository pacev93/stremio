# Streaming-, Cursor- und Audio-Korrekturen

## Aktueller Stand: 1.0.5

Version 1.0.5 behält den HTTP-Range-Fix und die DTS-Korrekturen aus 1.0.4 bei.
Der Nutzer bestätigt, dass die gewünschte DTS-zu-Dolby-Konvertierung mit 1.0.4
funktioniert. Die noch fehlerhaften Cursor- und Play-Tasten-Fälle werden
gezielt nachgebessert; der Player-/Konvertercode bleibt gegenüber 1.0.4 unverändert.
Ausgangspunkt bleibt das Original 1.0.0, Commit
`051818e55cf38caed42d597fbcb05bdd3fc5bbd9`. Der übrige Funktionsumfang und die
Originalressourcen bleiben erhalten. Es gibt keinen zusätzlichen Read-Ahead-Proxy.

Die fehlerhafte Cursor-Steuerung aus 1.0.1/1.0.2 wurde bereits mit 1.0.3
zurückgenommen: Der Nutzer konnte den Zeiger auch im LG-Homebildschirm nicht mehr
aktivieren und musste schließlich den TV neu starten. Die damaligen Tests mit
simulierten SDL-Funktionen hatten diese systemweite Wirkung nicht erfasst.
Die neue Umsetzung wird unten einschließlich ihrer Prüfgrenzen beschrieben.

Homebrew-Repository:

```text
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json
```

1.0.5 als Update installieren, ohne die App vorher zu deinstallieren.
Die bestehende Repository-Adresse bleibt erhalten.
Der eingebaute Updater bleibt unverändert und verweist auf das Originalprojekt.

## Cursor: ausschließlich das Bild austauschen

Nach drei Sekunden ohne Zeigerbedienung oder bei Pfeiltasten wird über
`SDL_CreateCursor`/`SDL_SetCursor` ein transparentes Cursorbild verwendet.
1.0.4 konnte die Sperre nach 350 ms durch eine spätere Cursor-Show-Meldung
verlieren. Danach aktivierte die kleinste Bewegung den Zeiger wieder. Außerdem
konnte ein Klick trotz unsichtbarem Bild noch den alten Zeigerort bedienen.

1.0.5 hält den Zeigermodus nach dem Ausblenden gesperrt: Show-Meldungen allein
aktivieren ihn nicht. In den ersten 350 ms werden Bewegungen ignoriert; danach
braucht es mindestens 64 Layout-Pixel Abstand vom Anfang einer zusammenhängenden
Bewegung. Pausen über 300 ms setzen diesen Anfang zurück, sodass vereinzelte
kleine Bewegungen sich nicht aufsummieren. Kleine Handbewegungen verändern weder
den Fokus noch die Player-Bedienelemente. Ein Klick im inaktiven Modus bestätigt
den aktuellen Tastaturfokus, ohne den Zeiger zu aktivieren; doppelte OK-/Maus-
Ereignisse derselben Fernbedienung werden weiterhin zusammengefasst. Erst die
deutliche Bewegung stellt das gesicherte Cursorbild und die Zeigerbedienung
wieder her. Dies ist eine lokale Gestenerkennung anhand der SDL-Bewegungen,
keine Änderung des Bewegungssensors der Fernbedienung.

`SDL_webOSCursorVisibility` und `SDL_ShowCursor` werden nicht aufgerufen oder
dynamisch aufgelöst. Der Bewegungseingang bleibt eingeschaltet. Beim Verlassen
des Vordergrunds und beim regulären Beenden wird das ursprüngliche Bild
wiederhergestellt. Hintergrundereignisse können es nicht erneut ausblenden;
ein beim Fokuswechsel gehaltener Klick wird zurückgesetzt. Falls SDL kein
wiederherstellbares Originalbild oder keinen transparenten Cursor bereitstellt,
bleibt der vorhandene Zeiger unverändert.

Zwölf Abläufe mit echter Desktop-SDL und einer lokalen X-Anzeige prüfen
Bildwechsel, absichtliches Aufwecken, kleine Bewegungen, wiederholte
Show-Meldungen, Klicks im Tastenmodus in beiden Ereignisreihenfolgen,
Fokuswechsel, gehaltene Klicks und Beenden. Acht zusätzliche Backend-Fälle prüfen fehlende Funktionen,
fehlendes Originalbild, fehlgeschlagene Erstellung und die Wiederherstellung
eines benutzerdefinierten Bilds. Das ist kein Nachweis für den geschlossenen
LG-Compositor; die Darstellung und das Wiederauftauchen auf dem CX bleiben
am TV zu prüfen.

## DTS: warum „Umwandeln“ später wirkungslos erscheinen konnte

Im Original schreibt ein Fehler beim Abspielen des lokal konvertierten
HEVC/HLS-Streams dauerhaft `hlsHevcOk=false` in die gespeicherten TV-Fähigkeiten.
Auch ein einzelner Start ohne Bild nach 25 Sekunden konnte das auslösen.
`dts_convert` verweigerte danach jeden weiteren HEVC-Konvertierungsversuch,
einschließlich der ausdrücklich gewählten Einstellung „Umwandeln“.
Ein erfolgreicher späterer Versuch konnte ein bereits gespeichertes Nein
ebenfalls nicht korrigieren. Diese Kombination passt dazu, dass derselbe
Build zuerst funktioniert und später die DTS-Fehlermeldung zeigt. Der Zustand
des konkreten TVs wurde nicht ausgelesen; dies ist ein im Code und in den
Regressionstests belegter Fehler, kein abschließender Nachweis vor Ort.

1.0.4 lässt die explizite Einstellung diese alte negative Beobachtung übergehen.
Ein einzelner Streamfehler wird nicht mehr als dauerhafte HEVC/HLS-Unfähigkeit
gespeichert. Erfolgreiche Wiedergabe kann das alte Nein wieder zu Ja ändern.
Fehlgeschlagene Versuche bleiben auf den aktuellen Stream begrenzt, ohne
Endlosschleife. „Automatisch“ respektiert weiterhin vorhandene negative
Beobachtungen, „Aus“ startet keine erzwungene DTS-Konvertierung.

Zusätzlich bekommt die ausgewählte DTS-Spur bei „Umwandeln“ Vorrang vor dem
automatischen Wechsel auf eine andere, etwa zweikanalige AC3-Spur. Dies gilt
auch bei der automatischen Sprachauswahl und der Tonwahl im bestehenden
Dolby-Vision-Konvertierungspfad. Die ursprüngliche Konverterbibliothek bleibt
unverändert: DTS mit sechs oder mehr Kanälen wird als Dolby Digital 5.1
ausgegeben, Stereo bleibt Stereo. Die Tests prüfen die Entscheidungen des
echten Playercodes mit kontrollierten Medien-/Transportgrenzen; sie decodieren
keine Datei und ersetzen keinen Wiedergabetest auf dem Fernseher.

## Separate Play-Taste

Der Nutzer bestätigt, dass Play mit den separaten Tasten der Magic Remote
auch ohne DTS-Konvertierung ausfällt, während Pause zuverlässig funktioniert.
Die in 1.0.4 ergänzten Werte 415/19/10252 gehören zur Web-App-Tastencode-Welt
und erklärten die native LG-SDL-Zuordnung nicht.

Die [öffentliche Dokumentation einer ausgelesenen LG-SDL-Tabelle](https://github.com/GLinnik21/plx-native/blob/579f44b97c7de6cc5274e76983eb608f638a7747/docs/remote-keys.md)
weist für die separate Play-Taste den privaten SDL-Scancode **450** aus
(Linux `KEY_PLAY`, 207); das Symbol kann dabei null sein. Die unveränderte
Pause-Taste verwendet den normalen SDL-Scancode 72. 1.0.5 ergänzt gezielt 450
als `K_PLAY` und entfernt die Web-Tastencode-Ergänzung aus 1.0.4.
Die normalisierten SDL-Tasten und der kombinierte Play/Pause-Schalter bleiben
unterstützt. Vier Fälle prüfen die tatsächliche Zuordnung zusammen mit den
Medienzweigen des Players, darunter Pause → Play und wiederholtes Play ohne
erneutes Pausieren. Die Referenztabelle stammt von einer anderen LG-Firmware;
welche Ereignisse der konkrete CX liefert, wurde nicht am TV aufgezeichnet.
Medien- und unbekannte private Scancodes werden nun auch nach dem Startfenster
im bestehenden App-Log protokolliert. Texteingaben und PIN-Tasten werden durch
diese zusätzliche Protokollierung nicht erfasst.

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
DISPLAY=:97 python3 tests/pointer/run.py --sdl-include "$SDK/usr/include"
python3 tests/audio/run.py
python3 tests/remote/run.py --sdl-include "$SDK/usr/include"
python3 tools/scrub_ipk.py candidate.ipk --reference original-1.0.0.ipk
python3 tests/package/check.py original-1.0.0.ipk candidate.ipk
```

Die zwölf Transportfälle umfassen feste und Chunked-Antworten, Wiederverwendung,
Redirects, Dateiende, ignorierte/falsche Ranges, unterbrochene/überlange
Antworten sowie HTTP-Fehler und Timeouts. Hinzu kommen 20 Cursor-, 14 Audio-
und vier Medien-Tasten-Fälle. Der Cursor-Test benötigt echte SDL2 sowie eine
lokale X-Anzeige (hier `:97`, gegebenenfalls mit `XAUTHORITY`); er verwendet
keinen abgeschalteten Zeiger. Das ausgelieferte Programm wird auf das Fehlen
der beiden verworfenen Cursor-API-Namen geprüft. Die Paketprüfung liest die
endgültige IPK-Datei und vergleicht alle 330 Daten-Einträge mit dem Original.
