# Vehicle-Manager

Vehicle Manager

## Servicehistorie im Python-Projekt

Auf jeder Fahrzeugseite zeigt die Servicehistorie eine Kurve mit Datum und
Kilometerstand. Beim Überfahren oder Fokussieren eines Punkts erscheinen Kurzinfos;
ein Klick oder Antippen öffnet die vollständige Beschreibung, Arbeiten und
verknüpften Aufträge. Dicht beieinanderliegende Einträge werden als Punkt mit
Anzahl zusammengefasst und lassen sich gemeinsam öffnen. Über **Neuer
Historieneintrag** können Techniker und Admins mehrere Kategorien (z. B. Service
und Reparatur), Standardarbeiten und offene oder geschlossene Aufträge desselben
Fahrzeugs auswählen. Kategorien haben eigene Farben und Symbole. Einträge lassen
sich anschließend bearbeiten oder löschen; verknüpfte Aufträge bleiben erhalten.
Kunden können die Historie ihrer zugewiesenen Fahrzeuge ansehen.

Die Filter für Kategorie und Standardarbeit lassen sich mit der Suche in der
Beschreibung kombinieren. Die Suche ignoriert Groß- und Kleinschreibung.
Filter blenden nur Ereignispunkte ein oder aus. Die vollständige Kilometerkurve
und ihre Achsen bleiben auch bei null Treffern unverändert.

Ab dem letzten Eintrag wird die Kurve gestrichelt bis heute verlängert. Die
Schätzung nutzt die durchschnittliche Fahrleistung pro Tag, gewichtet nach der
Dauer zwischen den Einträgen. Dafür sind mindestens zwei unterschiedliche Tage
erforderlich; Zeiträume mit sinkendem Kilometerstand werden ausgelassen.
Geschätzte Kilometerstände werden nur angezeigt und nicht als Eintrag gespeichert.

Die benötigten Tabellen werden beim nächsten Start automatisch ergänzt. Die
Historie ist auch im JSON-Export und -Import des Datenbankmanagers enthalten;
ältere Exporte ohne Historie können weiterhin importiert werden.

Integrationstests mit einer isolierten Datenbank aus dem Projektverzeichnis:

```sh
python -m unittest discover -s Python/tests -v
```

## Markenlogos im Python-Projekt

Fahrzeugnamen zeigen automatisch links das Logo der eingetragenen Marke.
Als öffentliche Quelle dient [VehicleSpecs Brand Logos](https://github.com/vehiclespecs/brand-logos)
mit 184 Marken über jsDelivr, ohne Anmeldung oder API-Schlüssel. Auch Schreibweisen
wie VW, Mercedes, Škoda und Citroën werden erkannt. Unbekannte Marken und
Ladefehler zeigen ein neutrales Fahrzeugsymbol.

Die Zuordnung liegt lokal in `Python/data/brand-logos/brands.json`; nur das Bild
wird vom Browser über den CDN geladen, ohne Referrer und ohne Fahrzeugdaten in
der URL. Katalog und Bild-URLs sind auf dieselbe feste Version gepinnt.
Quellen- und Lizenzhinweise stehen neben dem Katalog.

## Contributors

Lead Developer - [Red05Jack](https://github.com/Red05Jack)
