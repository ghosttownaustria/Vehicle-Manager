# Vehicle-Manager

Vehicle Manager

## Servicehistorie im Python-Projekt

Auf jeder Fahrzeugseite zeigt die Servicehistorie eine Zeitachse mit Datum,
Kilometerstand, Beschreibung und verknüpften Aufträgen. Über **Neuer
Historieneintrag** können Techniker und Admins mehrere Kategorien (z. B. Service
und Reparatur), Standardarbeiten und offene oder geschlossene Aufträge desselben
Fahrzeugs auswählen. Kategorien haben eigene Farben und Symbole. Einträge lassen
sich anschließend bearbeiten oder löschen; verknüpfte Aufträge bleiben erhalten.
Kunden können die Historie ihrer zugewiesenen Fahrzeuge ansehen.

Die Filter für Kategorie und Standardarbeit lassen sich mit der Suche in der
Beschreibung kombinieren. Die Suche ignoriert Groß- und Kleinschreibung.

Die benötigten Tabellen werden beim nächsten Start automatisch ergänzt. Die
Historie ist auch im JSON-Export und -Import des Datenbankmanagers enthalten;
ältere Exporte ohne Historie können weiterhin importiert werden.

Integrationstests mit einer isolierten Datenbank aus dem Projektverzeichnis:

```sh
python -m unittest discover -s Python/tests -v
```

## Contributors

Lead Developer - [Red05Jack](https://github.com/Red05Jack)
