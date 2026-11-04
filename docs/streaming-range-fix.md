# Streaming-, Cursor- und Audio-Korrekturen

## Aktueller Stand: 1.0.10

1.0.10 entfernt die Vordergrund-Serviceabfrage aus 1.0.9 nach der Rückmeldung,
dass der Cursor damit dauerhaft sichtbar und unbedienbar bleibt. Die Rückkehr
wird anhand von SDL-Fokusereignissen und Eingaben für das eigene Fenster
erkannt. Der erzwungene Stream-Neustart aus 1.0.8 bleibt zurückgenommen. Die bedarfsgerechten
Textuntertitel-Abrufe aus 1.0.8 bleiben erhalten. Die native Pufferautomatik,
funktionierende DTS-Auswahl, mitgelieferte App-Konfiguration und alle
Originalbibliotheken bleiben erhalten. Es gibt keinen zusätzlichen Proxy.

- Ein verlorenes Pointer-Loslassen wird beim Navigationswechsel oder einer
  neuen Betätigung abgebrochen, ohne die alte Aktion auszulösen. Fehlende
  Fenster-Fokus-Rückkehr wird über Eingaben für das eigene SDL-Fenster
  repariert: Scrollrad, linker Tastendruck, Pfeile/OK oder bestätigter
  Mausfokus. Dies gilt auch für einen hängen gebliebenen App-Hintergrundzustand.
  Serviceantworten können keine Pointer-Sperre mehr setzen. Bewegung hebt die
  Rad-Sperre nicht auf; Cursor-Show-Meldungen bleiben ohne Rückkehrwirkung. Das transparente
  Bild wird nach nativen Bild-Resets erneut gesetzt. Rad-Aktivierung und
  Idle nach Rückkehr bleiben erhalten; native Hide-Meldungen verschlucken
  keinen unabhängigen OK-Tastendruck.
- Normales Vor-/Zurückspulen nutzt wieder den nativen Seek innerhalb derselben
  Mediensitzung, auch bei DTS-/DV-HLS. Die 350-ms-Zusammenfassung mehrerer
  Sprünge bleibt erhalten. Nur der bereits im Original vorhandene Sonderpfad
  für indexlose kontinuierliche TS-Ausgabe benötigt weiterhin einen Neuaufruf
  mit Zeitparameter. Sein Pause-Zustand bleibt erhalten. Wartende Anfragen
  eines tatsächlich gestoppten Konverters werden weiterhin abgewiesen.
- Der MKV-Worker liest weiterhin Header, Audio-/DV-Daten und Kapitel.
  Untertitelindex und Dialogdaten werden erst bei einer angeforderten
  Textspur gelesen. Es wird nur diese Spur im vorhandenen Zeitfenster
  bedient, kein ganzer Track und kein Vorrat aller Sprachen. Off/externe
  Untertitel erzeugen keine fortlaufenden eingebetteten Textabrufe.
  Auto-sync darf während seiner Referenzsuche gezielt eine Textspur
  anfordern und gibt sie beim Ende/Abbruch wieder frei.
- Die Statistik benennt den lokalen Konverterweg und zeigt ausgeschaltete
  Untertitel als `off`. Der Sekundenwert bleibt eine native Meldung und ist
  keine direkte Messung aller Pufferspeicher.

Die Korrekturen sind lokal geprüft, nicht auf der geschlossenen CX-Pipeline.
Ein vollständiges Ausbleiben weiterer Unterbrechungen oder Video-Hänger
ist damit noch nicht am TV nachgewiesen.

## Bisherige Korrekturen und Puffer-Rücknahme in 1.0.7

Version 1.0.7 entfernt die Puffer-Auswahl, die zusätzlichen nativen
Pufferparameter und den dazugehörigen Rückfall aus 1.0.6 nach der Rückmeldung
über Soundaussetzer. Der Videopfad, die Einstellungsseite und die deutsche
Übersetzung entsprechen wieder bytegenau dem Original.
HTTP-Range-Fix, DTS-Korrekturen aus 1.0.4, native Play-Zuordnung aus 1.0.5
und Cursor-Aktivierung ausschließlich per Scrollrad aus 1.0.6 bleiben erhalten.
Der Nutzer bestätigt, dass die gewünschte DTS-zu-Dolby-Konvertierung mit 1.0.4
funktioniert. Diese Auswahlregeln und die Konverterbibliothek bleiben
erhalten. 1.0.8 ergänzte bedarfsgerechte Untertitelabrufe und erzwang einen
Sitzungsneustart beim Spulen, um den einmal gemeldeten Bildstillstand zu
umgehen. Diese Neustarts störten laut Rückmeldung selbst kleine Sprünge;
1.0.9 entfernt sie. Andere Streaming-Ansätze bleiben Vorschläge.
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

1.0.10 als Update installieren, ohne die App vorher zu deinstallieren.
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

Der Nutzer meldet zu 1.0.8 einen dauerhaft sichtbaren, inaktiven Zeiger nach
LG-Systemmenüs, während Pfeiltasten und OK weiter die App bedienen. Das passt
zu einem veralteten Hintergrundzustand: Die Pointer-Handler bleiben gesperrt,
das ursprüngliche Cursorbild sichtbar, Tasteneingaben laufen jedoch weiter.
Ein TV-Ereignisprotokoll zum Nachweis liegt nicht vor.

1.0.9 ergänzte `getForegroundAppInfo`. Das war für diesen nativen Client kein
hinreichend bestätigter Sichtbarkeitsnachweis. Im Code kann eine leere bzw.
fremde App-Meldung selbst ohne SDL-Fokusverlust die gesamte Pointer-Bedienung
sperren. Ein danach korrekt an das Fenster gerichtetes Scrollrad-Ereignis
wurde ohne positiven Dienstnachweis weiter verworfen. Die neuen Tests
reproduzieren diese Blockade mit dem 1.0.9-Code. Die tatsächliche
Serviceantwort des CX ist weiterhin nicht aufgezeichnet.

1.0.10 entfernt die Abfrage, ihre Handles, Zeitgeber und Zustandsantworten
vollständig. Eine echte Radbewegung oder ein linker Tastendruck für die
passende SDL-Fenster-ID repariert einen fehlenden Rückkehrhinweis direkt vor
der Verarbeitung derselben Eingabe. Es geht keine zusätzliche erste
Betätigung verloren. Mausbewegung bzw. Window-Enter können dies nur bei
passender Fenster-ID und SDL-Mausfokus. Sie lösen die Rad-Sperre nicht.
Unadressierte Hintergrund-Zeigerereignisse, fremde Fenster, bloße
Cursor-Show-Meldungen und verwaiste Loslassen-Ereignisse lösen keine Rückkehr
aus. Fenster-Hidden/Minimized bleibt geschützt. Die Prüfung verlässt sich
nicht mehr auf den Namen des nativen Clients in einem Systemdienst.

22 Abläufe mit echter Desktop-SDL und einer lokalen X-Anzeige prüfen
Bildwechsel, Scrollrad-Aktivierung, ignorierte kleine und große Bewegungen, wiederholte
Show-Meldungen, Klicks im Tastenmodus in beiden Ereignisreihenfolgen,
Fokuswechsel, gehaltene/verlorene Klicks, Rückkehr mit unverändertem Bild,
nativen Hide zwischen OK-/Maus-Ereignissen und Beenden.
Acht zusätzliche Backend-Fälle prüfen fehlende Funktionen,
fehlendes Originalbild, fehlgeschlagene Erstellung und die Wiederherstellung
eines benutzerdefinierten Bilds. 16 weitere Fälle prüfen Eingaben und fehlende
Rückkehrereignisse mit kontrolliertem SDL-Zustand, darunter 2000 Menüwechsel,
fremde Fenster und verwaiste Releases. Ein Test verlangt, dass über 10000
Poll-Schritte keine Vordergrund-Dienstanfrage mehr erfolgt. Mit echter
Desktop-SDL werden zusätzlich 100 Wiederholungen aus Rad-Aktivierung, Klick
und Ausblenden nach fehlender Rückkehrmeldung geprüft.
Das ist kein Nachweis für den geschlossenen
LG-Compositor; die Darstellung und das Wiederauftauchen auf dem CX bleiben
am TV zu prüfen.

## Nativer Videopuffer: Originalautomatik wiederhergestellt

Die Pufferprofile aus 1.0.6 verursachten laut Nutzer Soundaussetzer und weitere
Probleme. In 1.0.7 sind Einstellung, Zeit-Ziele und automatischer Rückfall
vollständig entfernt. Der native Player erhält wieder ausschließlich
`bufferControl.userBufferCtrl=false` wie im Original. Ein gespeicherter
`nativeBufferSeconds`-Wert wird nicht mehr gelesen; weder Zurücksetzen noch
Neuinstallation ist nötig.

Der entfernte Versuch hatte nur zusätzliche native Zeit-Schwellen angefordert,
keinen festen MB-Cache eingerichtet. Die öffentlichen Hinweise auf diese
Schwellen betrafen HLS auf anderer Firmware. Die Rückmeldung zeigt, dass der
Ansatz auf diesem CX ungeeignet ist. Auch bestandene Payload-/Rückfalltests
konnten die tatsächliche Synchronität und Pufferung des geschlossenen
Mediendienstes nicht prüfen.

Die genaue Größe des CX-Standardpuffers bleibt unbekannt. Weiterhin gemeldet
sind Restunterbrechungen bei Remuxes um 60 Mbit/s und gelegentlich um 35 Mbit/s,
unabhängig vom Ton, am eingebauten 100-Mbit-LAN-Port. Die Servergrafik zeigt
ungefähr 5–8 MB/s für die gesamte öffentliche Schnittstelle; sie misst weder
den einzelnen TV-Stream noch seinen Puffer. Die LAN-Obergrenze allein erklärt
den 35-Mbit/s-Fall nicht.

[Stremio-Issue #2771](https://github.com/Stremio/stremio-bugs/issues/2771)
beschreibt ähnliche HTTP-Remux-Stalls auf anderer LG-Hardware und vermutet
kleine serielle Range-Abrufe. Das ist kein Ursachennachweis für diesen CX.
Einzelheiten des zurückgenommenen Versuchs und des Nuvio-Vergleichs stehen in
Commit `c6f88c7`; diese Profile werden nicht weiter empfohlen.

## Weitere Ansätze und getroffene Auswahl

Die bedarfsgerechten Textabrufe der zweiten Option sind mit 1.0.8 umgesetzt.
Hash-Abrufe, Range-Größen, Ausgabecontainer und Decoderzufuhr werden dabei
nicht umgebaut. Die übrigen Optionen bleiben unimplementiert.

| Ansatz | Erwarteter Nutzen | Risiken und Grenzen | Aufwand |
| --- | --- | --- | --- |
| Lokale Messung von Stalls, gemeldetem Videopuffer und eigenen Range-Zugriffen | Hoher Diagnosewert: Zusatzabrufe, Quelle und nativer Player besser auseinanderhalten | Behebt allein keine Unterbrechung; Auswertung eines TV-Laufs erforderlich | Klein |
| MKV-/Untertitel-/Hash-Zugriffe stärker hinter die Wiedergabe stellen | Plausible Entlastung für entfernte Usenet-Quellen, wenn Zusatzabrufe konkurrieren | Eingebettete Untertitel oder Hash-Treffer können später verfügbar sein; keine Korrektur des geschlossenen LG-HTTP-Clients | Klein bis mittel |
| Vorhandenen HLS-Pfad als Remux-Modus mit Audio-/Video-Kopie nutzen | Anderer Container und Zulieferpfad können direkten MKV-HTTP-Engpass umgehen | HDR/DV, Spuren und Seeking prüfen; hilft nicht zwangsläufig beim bereits HLS-konvertierten DTS-Fall | Mittel |
| Eigener Fetch-/Demux-Pfad mit direkter nativer Decoder-Zulieferung | Potenzial für echte Byte-Budgets und kontrollierte HTTP-Anfragen ohne zusätzlichen Proxy | Großer Eingriff; RAM/CPU, Synchronität, HDR/DV, Seeking und CX-API-Kompatibilität neu abzusichern | Hoch |

Codebasis vor 1.0.8: `src/core/mkvsubs.c:pick` forderte Daten für alle
Textspuren im Zeitfenster bis 90 s voraus an. Im indexierten Pfad fehlt die
Pufferprüfung des nicht dringenden Scanners; dieser prüft bereits eine
15-s-Reserve. `src/core/subs.c:subs_os_hash` kann zudem Dateianfang und -ende
lesen. Header und benötigte Audio-/Videometadaten müssen verfügbar bleiben,
damit der funktionierende DTS-Pfad erhalten bleibt. Ob diese Zugriffe mit
Aussetzern zusammenfallen, ist noch zu messen.

Codebasis der dritten Option: `HC_COPYAUDIO`/`SBD_COPYAUDIO` existieren bereits.
Der HLS-Leser nutzt zusammenhängende Ranges von zunächst 512 KiB, dann 2 MiB.
Ein Remux-Modus würde den vorhandenen lokalen HLS-Server verwenden und
kompatible Spuren kopieren. Es wird kein zusätzlicher Read-Ahead-Proxy
vorgeschlagen. Native Puffersteuerung bliebe bei der Originalautomatik.

Empfehlung: zuerst einen kurzen Messlauf, danach gegebenenfalls die gezielte
Priorisierung eigener Zusatzabrufe. Ein HLS-Remux ist eine weitere Option,
falls die direkte MKV-Zulieferung als Engpass bestätigt wird. Für alle
weiteren Streaming-Umbauten ist weiterhin die Auswahl des Nutzers abzuwarten.

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
| Nicht unterstützter Ton | Plattform-/Server-abhängig | Eigener Konverter über 512-KiB-/2-MiB-Ranges, Ausgabe als lokales HLS oder indexloses MPEG-TS |

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
erhalten. Die Anwendungsdateien unterscheiden sich wieder ausschließlich beim
neu gebauten Programm und der Versionsangabe. Die drei zusätzlichen
Puffer-Texte aus 1.0.6 wurden entfernt; die Übersetzung ist bytegenau original.

1.0.1 hatte einen Paketierungsfehler: Das Programm trug `0704` statt `0755`;
Datendateien trugen `0604` statt `0644`. Seit 1.0.2 werden die Zugriffsrechte
jedes Archiv-Eintrags aus dem Original übernommen. Die Paketprüfung verwirft
1.0.1 und überprüft die endgültige Veröffentlichungsdatei.

```sh
source /workspace/stremio-env/activate.sh
python3 tests/net/run.py --sdl-include "$SDK/usr/include"
DISPLAY=:97 python3 tests/pointer/run.py --sdl-include "$SDK/usr/include"
python3 tests/pointer/focus.py --sdl-include "$SDK/usr/include"
python3 tests/audio/run.py
python3 tests/remote/run.py --sdl-include "$SDK/usr/include"
python3 tests/seek/run.py --sdl-include "$SDK/usr/include"
python3 tests/mkv/run.py --sdl-include "$SDK/usr/include"
python3 tools/scrub_ipk.py candidate.ipk --reference original-1.0.0.ipk
python3 tests/package/check.py original-1.0.0.ipk candidate.ipk
```

Die zwölf Transportfälle umfassen feste und Chunked-Antworten, Wiederverwendung,
Redirects, Dateiende, ignorierte/falsche Ranges, unterbrochene/überlange
Antworten sowie HTTP-Fehler und Timeouts. Hinzu kommen 30 Cursor-, 16
Fokus-Rückkehr-, 14 Audio-, vier Medien-Tasten-, 18 Seek- und neun MKV-Worker-Fälle.
Insgesamt sind dies 103 Szenarien. Für 1.0.10 wurden die 46 Cursor-/Fokusfälle
erneut ausgeführt; der zu 1.0.9 geprüfte Wiedergabe-/Audio-/Transport-Code
bleibt unverändert. Die zehn Tests des
entfernten Puffer-Experiments bleiben in der Git-Historie. Die Seek-Tests
prüfen native Sitzungswiederverwendung bei kleinen und wiederholten Sprüngen,
die erhaltene Pause im notwendigen TS-Sonderpfad sowie den Abbruch
einer wartenden HLS-Anfrage mit echten Threads. Die MKV-Tests verwenden
einen seekbaren Matroska-Datensatz und zählen die echten Range-Aufrufe des
Workers für beide Indexpfade; Audio/DV/Kapitel und Sprachwechsel werden geprüft.
Die native Pufferkonfiguration bleibt unverändert, obwohl der native
Video-Quellcode die Pause-Erhaltung im TS-Sonderpfad enthält.
Der Cursor-Test benötigt echte SDL2 sowie eine
lokale X-Anzeige (hier `:97`, gegebenenfalls mit `XAUTHORITY`); er verwendet
keinen abgeschalteten Zeiger. Das ausgelieferte Programm wird auf das Fehlen
der beiden verworfenen Cursor-API-Namen geprüft. Die Paketprüfung liest die
endgültige IPK-Datei und vergleicht alle 330 Daten-Einträge mit dem Original.
