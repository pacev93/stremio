# Update 1.0.11

Bestehende Homebrew-Adresse:
https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren; keine Deinstallation.

Der Zeigerfokus wird beim Verlassen des App-Fensters ausdrücklich abgegeben.
Tastaturfokus allein holt ihn während eines Systemmenüs nicht zurück. Bei
adressierter Zeigerrückkehr oder beobachtetem Mausfokuswechsel zurück zu Origin
werden Klickzustand und Cursorbild gemeinsam wiederhergestellt. Ein zuvor
verdeckter Cursor bleibt bis zur nächsten Radbewegung verborgen.

Keine Vordergrund-Serviceabfrage und keine globalen Cursor-Schalter. Wiedergabe,
Spulen, DTS und Pufferautomatik entsprechen 1.0.10.

50 lokale Cursor-/Fokusprüfungen, ARM-Build und Paketprüfung bestanden.
Alle 330 Original-Dateirechte, Ressourcen, Bibliotheken und mitgelieferte
App-Konfiguration bleiben erhalten. Der konkrete LG-CX-Ablauf ist nicht
aufgezeichnet und muss am TV geprüft werden. Bei erneutem Fehlschlag folgt
der Ereignismitschnitt vor weiteren funktionalen Änderungen.

Details: https://github.com/pacev93/stremio/tree/4582e074a3be866dc2af87291a2e5cc885cf811d/docs/streaming-range-fix.md
