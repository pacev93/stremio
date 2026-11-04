# Update 1.0.9

Bestehende Homebrew-Adresse unverändert:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren. Keine Deinstallation
oder Zurücksetzung erforderlich.

Cursor: Die Rückkehr nach LG-Systemmenüs wird zusätzlich über den nativen
Vordergrundstatus und tatsächlich an die App gerichtete Pfeil-/OK-Eingaben
erkannt. Dadurch kann ein hängen gebliebener Hintergrundzustand gelöst werden.
Veraltete Antworten und mehrdeutige Panel-Zustände lösen keine Freigabe aus.
Aktivierung nach Ausblenden weiterhin ausschließlich per Scrollrad; Bewegung
allein aktiviert den Zeiger nicht. Verlorene Klicks werden abgebrochen, ohne
ihre alte Aktion auszulösen.

Spulen: Normale direkte und HLS-Streams bleiben in derselben Mediensitzung.
Die erzwungenen Konverter-Neustarts und direkten Rückwärts-Neuladungen aus
1.0.8 sind entfernt. Mehrere Sprünge werden weiterhin zusammengefasst. Der
bestehende Sonderpfad für indexlose TS-Ausgabe benötigt einen Neuaufruf mit
Zeitparameter und behält den Pause-Zustand bei.

Textuntertitel werden weiterhin nur bei Bedarf gelesen. Ton-/Bildmetadaten
und Kapitel bleiben verfügbar. Native Pufferautomatik und funktionierende
DTS-Umwandlung bleiben erhalten.

101 lokale Regressionsszenarien und ARM-Build erfolgreich. Endgültige IPK
mit allen 330 Original-Dateneinträgen verglichen: Rechte und Ressourcen
unverändert, nur Programm und Versionsangabe weichen ab. Originalbibliotheken
und eingebettete App-Konfiguration bleiben erhalten. Der eingebaute Updater
verweist weiterhin auf das Originalprojekt. Cursor und Decoderverhalten
bleiben auf dem aus dieser Umgebung nicht erreichbaren LG CX zu bestätigen.

Quellen und Details: https://github.com/pacev93/stremio/tree/11478ef85458a058de47899d43c174a41da9362b/docs/streaming-range-fix.md
