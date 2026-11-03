# Streaming-, Cursor- und Audio-Korrekturen

## Aktueller Stand: 1.0.6

Version 1.0.6 behält den HTTP-Range-Fix, die DTS-Korrekturen aus 1.0.4 und
die native Play-Zuordnung aus 1.0.5 bei. Der Cursor wird nach dem Ausblenden
ausschließlich durch Drehen am Scrollrad wieder aktiv. Eine neue Einstellung
erlaubt einen begrenzten Versuch mit festen nativen Pufferzeit-Zielen.
Der Nutzer bestätigt, dass die gewünschte DTS-zu-Dolby-Konvertierung mit 1.0.4
funktioniert. Die noch fehlerhaften Cursor- und Play-Tasten-Fälle werden
gezielt nachgebessert; `src/screens/player.c` und die Konverterbibliothek
bleiben gegenüber 1.0.4 unverändert.
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

1.0.6 als Update installieren, ohne die App vorher zu deinstallieren.
Die bestehende Repository-Adresse bleibt erhalten.
Der eingebaute Updater bleibt unverändert und verweist auf das Originalprojekt.

## Cursor: ausschließlich das Bild austauschen

Nach drei Sekunden ohne Zeigerbedienung oder bei Pfeiltasten wird über
`SDL_CreateCursor`/`SDL_SetCursor` ein transparentes Cursorbild verwendet.
1.0.4 konnte die Sperre nach 350 ms durch eine spätere Cursor-Show-Meldung
verlieren. Danach aktivierte die kleinste Bewegung den Zeiger wieder. Außerdem
konnte ein Klick trotz unsichtbarem Bild noch den alten Zeigerort bedienen.

1.0.5 ließ eine deutliche Bewegung als Aktivierung zu. Auf ausdrücklichen Wunsch
gilt seit 1.0.6 stattdessen: Nach Ausblenden wegen Inaktivität, Pfeiltaste oder
TV-Hide-Meldung aktivieren weder kleine noch beliebig große Bewegungen den Zeiger.
Show-Meldungen und OK-Klicks lösen die Sperre ebenfalls nicht. Die erste echte
Scrollrad-Rastung aktiviert den Cursor ohne zusätzlichen Navigationsschritt.
Weitere Rastungen behalten die ursprüngliche Navigation bei. Ein Klick im
inaktiven Modus bestätigt den aktuellen Tastaturfokus; doppelte OK-/Maus-
Ereignisse derselben Fernbedienung werden weiterhin zusammengefasst.
Die Sperre bleibt auch beim Wechsel zu Home und zurück erhalten. Im Hintergrund
erhält Home das ursprüngliche Bild; erst im Vordergrund wird das App-Bild wieder
ausgeblendet. Es wird kein globaler Bewegungseingang abgeschaltet.

`SDL_webOSCursorVisibility` und `SDL_ShowCursor` werden nicht aufgerufen oder
dynamisch aufgelöst. Der Bewegungseingang bleibt eingeschaltet. Beim Verlassen
des Vordergrunds und beim regulären Beenden wird das ursprüngliche Bild
wiederhergestellt. Hintergrundereignisse können es nicht erneut ausblenden;
ein beim Fokuswechsel gehaltener Klick wird zurückgesetzt. Falls SDL kein
wiederherstellbares Originalbild oder keinen transparenten Cursor bereitstellt,
bleibt der vorhandene Zeiger unverändert.

13 Abläufe mit echter Desktop-SDL und einer lokalen X-Anzeige prüfen
Bildwechsel, Scrollrad-Aktivierung, ignorierte kleine und große Bewegungen, wiederholte
Show-Meldungen, Klicks im Tastenmodus in beiden Ereignisreihenfolgen,
Fokuswechsel, gehaltene Klicks und Beenden. Acht zusätzliche Backend-Fälle prüfen fehlende Funktionen,
fehlendes Originalbild, fehlgeschlagene Erstellung und die Wiederherstellung
eines benutzerdefinierten Bilds. Das ist kein Nachweis für den geschlossenen
LG-Compositor; die Darstellung und das Wiederauftauchen auf dem CX bleiben
am TV zu prüfen.

## Nativer Videopuffer: Automatik und feste Zeit-Ziele

Der Nutzer meldet verbleibende Unterbrechungen bei Remuxes mit ungefähr
60 Mbit/s und gelegentlich auch bei ungefähr 35 Mbit/s, unabhängig vom Ton.
Der CX verwendet den eingebauten 100-Mbit-LAN-Port. Die angehängte Servergrafik
zeigt grob 5–8 MB/s, also 40–64 Mbit/s. Sie misst die gesamte öffentliche
Serverschnittstelle, nicht den Füllstand oder Durchsatz des einzelnen TV-Puffers.
Die Anschlussbandbreite des Servers belegt keine konstante Einzelstream-Rate.
Auch Remux-Spitzen und kurze Lieferpausen sind damit nicht ausgeschlossen;
die 100-Mbit-Obergrenze allein erklärt den Fall mit 35 Mbit/s nicht.

Origin setzte bisher nur `bufferControl.userBufferCtrl=false`. Eine feste
Standardgröße in MB oder Sekunden ist im App-Code nicht vorgegeben. Der
entsprechende Standard der geschlossenen CX-Firmware wurde nicht ausgelesen.
[Stremio-Issue #2771](https://github.com/Stremio/stremio-bugs/issues/2771)
beschreibt ähnliche hochbitratige HTTP-Remux-Stalls auf anderer LG-Hardware und
vermutet kleine serielle Range-Abrufe. Der Autor schloss den Bericht selbst;
das ist kein bestätigter Fix und keine Messung auf diesem CX.

[webOS-IPTV-Issue #96](https://github.com/lennylxx/webos-iptv-player/issues/96)
dokumentiert drei `bufferControl`-Parameter in Sekunden und einen Hardwaretest
auf webOS 6.5.3. Dort wird die native HLS-Automatik mit Start bei 3 s,
Unterlaufgrenze 1 s und Wiederaufnahme bei 5 s beschrieben. **Diese Werte sind
kein belegter Standard für direkte MKVs auf dem CX.** Die Werte 10/5/20 wurden
dort am Gerät getestet; die Übertragbarkeit auf webOS 5 und MKV bleibt ein Versuch.
Für neuere Firmware ab webOS 23 wird ein anderer Demuxer beschrieben.

Unter **Einstellungen → Wiedergabe → Videopuffer** gibt es nun:

| Auswahl | Startpuffer angefordert | Unterlaufgrenze | Wiederaufnahme angefordert |
| --- | --- | --- | --- |
| Auto (Standard) | webOS-Standard | webOS-Standard | webOS-Standard |
| 10 s | 5 s | 2 s | 10 s |
| 20 s | 10 s | 5 s | 20 s |
| 30 s | 15 s | 5 s | 30 s |

Die Auswahl wird gespeichert und gilt ab dem nächsten Stream. Feste Profile
werden nur auf webOS 5/6 für entfernte HTTP-/HTTPS-Quellen angefordert.
Auf anderer oder unbekannter Firmware ist die Auswahl deaktiviert. Für den
lokalen DTS-Konverter und andere lokale Quellen bleiben die Originaloptionen
erhalten. `userBufferCtrl` bleibt false. **Die Zeit-Ziele sind keine zugesicherte
Speicherreservierung und verändern keine belegte harte Byte-Grenze oder native
HTTP-Range-Größe.** webOS kann die Angaben begrenzen oder für MKV ignorieren.

Bei Ablehnung, Fehler vor dem ersten Bild oder ausbleibendem ersten Bild wird
einmal mit den Originaloptionen neu geladen. Das Zeitlimit beträgt Ziel + 8 s
(18/28/38 s); ein bereits laufender Film wird wegen späterer Dips nicht neu
gestartet. Ein neuer Stream darf das gewählte Profil erneut versuchen. Es
wird keine dauerhafte negative TV-Fähigkeit gespeichert. Das bestehende
App-Log meldet Anforderung und Rückfall.

Zum Vergleich desselben Remuxes zunächst Auto, dann 20 s verwenden und den
Stream jeweils neu öffnen. **Einstellungen → Über → Stats for nerds** zeigt
bereits im Original den gemeldeten `buffer … s ahead`-Wert. Größere Zeit-Ziele
können den Start verzögern; sie beheben keinen dauerhaft zu geringen Zufluss.
20 s bei 60 Mbit/s entsprechen rechnerisch ungefähr 150 MB komprimierten
Mediendaten, keine zugesicherte RAM-Belegung.

Der geprüfte [native Nuvio-webOS-Pfad](https://github.com/NuvioMedia/NuvioTVSmart/blob/2096c868b2a00ce55babac50140d12f731c1f792/js/core/player/engines/nativeVideoEngine.js)
setzt ein HTML-Videoelement. Der getrennte HLS-Pfad verwendet ein
[Zeitlimit von 50 s](https://github.com/NuvioMedia/NuvioTVSmart/blob/2096c868b2a00ce55babac50140d12f731c1f792/js/core/player/playerController.js).
Das liefert keinen Beleg für einen übertragbaren MB-Regler am nativen URI-Player.
Ein fester Byte-Cache in einer anderen Engine wäre eine andere Architektur.
Dieser Fork richtet keinen zusätzlichen Read-Ahead-Proxy ein.

Zehn Tests kompilieren die tatsächliche webOS-Videoimplementierung mit
kontrollierten Luna-Antworten und SDL-Uhr. Sie prüfen die vollständigen
Load-Payloads, alle Profile, Firmware-/Lokal-Grenzen, begrenzte Rückfälle,
Pause, laufende Wiedergabe mit späteren Stalls, neue Quellen und alte Antworten.
Eine wirksame Vergrößerung des CX-Puffers lässt sich damit nicht bestätigen.

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

Die Originalbibliotheken `libsbengine.so` und `libsbdts.so`, bestehenden
Ressourcen, Lizenzen und eingebettete Trakt-/TMDB-App-Konfiguration bleiben
erhalten. Neben Programm und Versionsangabe enthält `assets/i18n/de.json`
ausschließlich drei zusätzliche Texte für die angefragte Puffer-Einstellung.
Die Paketprüfung vergleicht alle vorhandenen Übersetzungen gegen das Original.

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
python3 tests/buffer/run.py --sdl-include "$SDK/usr/include"
python3 tools/scrub_ipk.py candidate.ipk --reference original-1.0.0.ipk
python3 tests/package/check.py original-1.0.0.ipk candidate.ipk
```

Die zwölf Transportfälle umfassen feste und Chunked-Antworten, Wiederverwendung,
Redirects, Dateiende, ignorierte/falsche Ranges, unterbrochene/überlange
Antworten sowie HTTP-Fehler und Timeouts. Hinzu kommen 21 Cursor-, 14 Audio-,
zehn native Puffer- und vier Medien-Tasten-Fälle. Der Cursor-Test benötigt echte SDL2 sowie eine
lokale X-Anzeige (hier `:97`, gegebenenfalls mit `XAUTHORITY`); er verwendet
keinen abgeschalteten Zeiger. Das ausgelieferte Programm wird auf das Fehlen
der beiden verworfenen Cursor-API-Namen geprüft. Die Paketprüfung liest die
endgültige IPK-Datei und vergleicht alle 330 Daten-Einträge mit dem Original.
