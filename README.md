# Update 1.0.10

Bestehende Homebrew-Adresse unverändert:

https://raw.githubusercontent.com/pacev93/stremio/homebrew/apps.json

Origin vollständig schließen und als Update installieren. Keine Deinstallation
oder Zurücksetzung erforderlich.

Cursor: Die zusätzliche Vordergrund-Serviceabfrage aus 1.0.9 ist entfernt.
Sie konnte die gesamte Zeigerbedienung sperren und danach sogar gültige
Scrollrad-Eingaben für Origin abweisen. Der neue Regressionstest reproduziert
diese Blockade mit dem 1.0.9-Code und besteht nach der Korrektur.

Rad- und linke Mausbetätigungen für das App-Fenster reparieren eine fehlende
Rückkehrmeldung vor Verarbeitung derselben Eingabe. Pfeile/OK und bestätigter
SDL-Mausfokus können die veraltete Sperre ebenfalls lösen. Bewegung allein
löst die Rad-Sperre nicht. Aktivierung nach Ausblenden bleibt ausschließlich
per Scrollrad. Hintergrundereignisse ohne passende Fenster-ID und bloße
Cursor-Show-Meldungen aktivieren die Bedienung nicht.

Spulen, DTS-Umwandlung, native Pufferautomatik und bedarfsgerechte
Textuntertitelabrufe sind unverändert gegenüber 1.0.9.

46 Cursor-/Fokusprüfungen und ARM-Build bestanden. Dazu gehören 100 wiederholte
Bildwechsel-/Klick-/Idle-Zyklen mit echter Desktop-SDL und 2000 kontrollierte
Menürückkehrfälle. Der unveränderte Wiedergabecode behält die 57 Prüfungen aus
1.0.9. Die endgültige IPK entspricht bei allen 330 Dateneinträgen den originalen
Rechten; Ressourcen, Bibliotheken und eingebettete App-Konfiguration bleiben
erhalten. Die tatsächlichen Ereignisse und das Verhalten des LG CX sind aus
dieser Umgebung weiterhin nicht überprüfbar.

Quellen und Details: https://github.com/pacev93/stremio/tree/3fbe463d32e516353df1eedbac11bce3ade17c60/docs/streaming-range-fix.md
