# Update 1.0.14

Bestehende Homebrew-Adresse:
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren. Keine Deinstallation.

Der vorhandene Header-Proxy verwendet vollständig gelesene Serverantworten für
weitere Anfragen über dieselbe Verbindung. Vier curl-Sitzungen werden exklusiv
verwendet und nach URL sowie Anfrageheadern getrennt. Abbrüche und unvollständige
Antworten werden verworfen. Sind alle Sitzungen belegt, bleiben zusätzliche
Anfragen unabhängig; ein neuer Seek wartet nicht auf alte Antworten.

Bei ausgeschalteter Standard-Untertitelsprache starten externe Listen und
hashabhängige Addon-Suchen erst beim Öffnen der Untertitelauswahl. Automatische
Spurstatus-Abfragen vom Telefon lösen keine Suche aus. Bereits bekannte Hashes
werden wiederverwendet. MKV-Audio-/DV-/Kapitelinformationen bleiben verfügbar.

Die vorhandene Pufferzeile unterscheidet jetzt den tatsächlichen Header-Proxy
vom direkten Wiedergabepfad. Die Verbindungsoptimierung wirkt auf Quellen mit
diesem Proxy; der native LG-Direktabruf läuft weiterhin außerhalb davon.
Keine neue Puffergröße, kein Vorlade-Proxy und kein 8/32-MiB-Datencache.
Cursor-, Seek-, DTS- und native Pufferautomatik bleiben erhalten.

63 lokale Szenarien für dieses Release bestanden: elf HTTP-Proxy-, 17
Untertitel-/Hash-/Telefon-, zwölf Range-, neun MKV- und 14 DTS-Policyfälle.
ARM-Build und finaler Paketvergleich erfolgreich; alle 330 Original-Dateirechte,
Ressourcen, Bibliotheken und mitgelieferten Schlüssel erhalten.
Die Wirkung auf wiederkehrendes CX-Buffering bleibt am TV zu bestätigen.

Details: https://github.com/pacev93/stremio/tree/f43c152b7ce732fa34d08bb82b50d520bc81e8c6/docs/streaming-range-fix.md
