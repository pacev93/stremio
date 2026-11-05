# Update 1.0.15

Bestehende Homebrew-Adresse:
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren. Keine Deinstallation.

Der vorhandene DTS-/DV-Konverter holt fortlaufende Dateibereiche mit 4 statt
2 MiB. Start und größere Sprünge beginnen mit 512 KiB. Sein Rücklesering hält
8 statt 4 MiB zuletzt gelesene Bytes. Ein neuer 4-MiB-Block verdrängt damit
nicht den gesamten Rücklesevorrat. Ring plus eingehende Antwort belegen bis
zu 12 statt 6 MiB Nutzdaten, zuzüglich bestehender Bibliotheks-/Decoderbelegung.

Kurze Vorwärtssprünge erreichen ihr Ziel auch über mehrere verkürzte Antworten.
Große Sprünge setzen die Abrufgröße wieder herunter; bekannte Dateigrenzen
begrenzen den letzten Abruf. Gestoppte Arbeit liefert keine alten Daten aus.
Eine laufende HTTP-Anfrage behält die bisherige Frist von 15 Sekunden.

Kein neuer Vorlade-Proxy oder Vorladethread. Die Änderung wirkt auf den
Konverter-Dateileser, direkt und mit dem bestehenden Header-Proxy. Native
Direktwiedergabe lädt weiterhin der LG-Mediendienst; ihre Abrufgröße ändert
sich hierdurch nicht. Cursor, Untertitelstrategie, DTS-Auswahl, Seek-Sitzung
und native Pufferautomatik bleiben erhalten.

56 Prüfungen bestanden: zwölf Leser-, zwölf Range-, 18 Seek- und 14 DTS-Fälle.
Zusätzlicher Vergleich: dieselben 32 MiB bytegenau mit elf statt 19 Anfragen,
jeweils über eine Serververbindung. Das ist kein TV-Durchsatzbenchmark.
ARM-Build und finales Paket geprüft; 330 Original-Dateirechte, Ressourcen,
Bibliotheken und beide mitgelieferten Schlüssel erhalten. Die Wirkung auf
CX-Buffering bleibt am TV zu bestätigen.

Details: https://github.com/pacev93/stremio/tree/0a35b99c20537ed88b53cf5cebc47ddc0a4bc8eb/docs/streaming-range-fix.md
