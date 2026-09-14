# Vehicle-Manager

Vehicle Manager

## Servicehistorie im Python-Projekt

Auf jeder Fahrzeugseite zeigt die Servicehistorie eine Kurve mit Datum und
Kilometerstand. Beim Überfahren oder Fokussieren eines Punkts erscheinen Kurzinfos;
ein Klick oder Antippen öffnet die vollständige Beschreibung, Arbeiten und
verknüpften Aufträge. Dicht beieinanderliegende Einträge werden als Punkt mit
Anzahl zusammengefasst und lassen sich gemeinsam öffnen. Über **Neuer
Historieneintrag** können Techniker und Admins mehrere Kategorien (z. B. Service
und Reparatur oder Fahrzeugkauf), Standardarbeiten und offene oder geschlossene Aufträge desselben
Fahrzeugs auswählen. Kategorien haben eigene Farben und Symbole. Einträge lassen
sich anschließend bearbeiten oder löschen; verknüpfte Aufträge bleiben erhalten.
Kunden können die Historie ihrer zugewiesenen Fahrzeuge ansehen.

Über **Servicehistorie drucken** öffnet sich eine Druckansicht mit der Grafik am
Anfang und anschließend allen Einträgen vom ältesten zum neuesten, jeweils mit
vollständigen Details und sichtbaren verknüpften Aufträgen. Die Ausgabe enthält
immer die gesamte Historie, unabhängig von Filtern. **Drucken / als PDF speichern**
öffnet den Druckdialog des Browsers. Für die Grafik muss JavaScript aktiviert sein.

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

## Tankbuch und Spritverbrauch im Python-Projekt

Auf jeder Fahrzeugseite gibt es unter der Servicehistorie den Bereich
**Spritverbrauch** mit Tankbuch. Techniker und Admins können Tankungen hinzufügen,
bearbeiten und löschen; Kunden sehen die Tankdaten ihrer zugewiesenen Fahrzeuge.
Pflichtangaben sind **Menge in Litern** und **Datum**. Optional sind der absolute
**Kilometerstand**, der **Gesamtpreis in Euro** (nicht der Literpreis) und die
Markierung **Volltankung**. Dezimalzahlen können mit Komma oder Punkt eingegeben
werden, ohne Tausendertrennzeichen. Liter erlauben drei, Preise zwei Nachkommastellen.

Die erste Volltankung mit Kilometerstand dient als Ausgangspunkt. Bis zur
nächsten Volltankung mit Kilometerstand werden alle danach getankten Liter
einschließlich der abschließenden Volltankung addiert. Teilfüllungen und
Volltankungen ohne Kilometerstand zählen dabei mit. Die Liter der ersten
Volltankung gehören nicht zum Verbrauchsintervall. Beispiel: Nach der Volltankung
bei 100.000 km werden 20 Liter nachgefüllt und bei 100.500 km nochmals 30 Liter
vollgetankt. Daraus ergeben sich 50 Liter auf 500 km, also **10 l/100 km**.

Die Tabelle zeigt pro Tankung die Eingaben und bei abgeschlossenen Intervallen
Liter, Strecke, l/100 km und ct/km. Der Durchschnittsverbrauch wird über die
Gesamtstrecke der gültigen Intervalle gewichtet. Fehlende Preise ergeben keinen
Kostenwert pro Kilometer; der durchschnittliche Literpreis berücksichtigt nur
Tankungen mit bekanntem Gesamtpreis. Die Übersicht zeigt außerdem alle getankten
Liter, die bekannten Gesamtkosten und die ausgewertete Strecke.

Offene Intervalle zählen noch nicht zum Durchschnittsverbrauch. Bei gleichem Datum
gilt die Reihenfolge der Erfassung. Bei sinkenden Kilometerständen oder einer
Intervallstrecke von null wird kein Verbrauch berechnet; die nächste Volltankung
mit Kilometerstand dient als neuer Ausgangspunkt. Nach Bearbeiten oder Löschen
werden alle Werte automatisch neu berechnet.

Die Tankbuchtabelle wird beim nächsten Start automatisch angelegt; vorhandene
Daten bleiben erhalten. Das Tankbuch ist im JSON-Export und -Import enthalten.
Ältere Sicherungen ohne Tankbuch lassen sich weiterhin importieren.

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
