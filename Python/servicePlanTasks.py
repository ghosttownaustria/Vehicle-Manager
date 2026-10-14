"""Standard work checklists that can be added to a printed service plan."""

SERVICE_PLAN_CHECK_GROUPS = [
    (
        "vehicle_check",
        "Fahrzeugcheck",
        [
            "Ölstand prüfen",
            "Kühlmittelstand und Frostschutz prüfen",
            "Bremsflüssigkeitsstand prüfen",
            "Scheibenwaschwasser auffüllen",
            "Beleuchtung und Blinker prüfen",
            "Scheibenwischer und Wischerblätter prüfen",
            "Reifenzustand, Profiltiefe und Luftdruck prüfen",
            "Batterie und Polklemmen prüfen",
            "Riemen, Schläuche und Leitungen auf Risse prüfen",
            "Motor, Getriebe und Achsen auf Undichtigkeiten prüfen",
            "Auspuffanlage prüfen",
            "Fahrwerk, Spurstangen und Gelenke auf Spiel prüfen",
            "Fehlerspeicher auslesen",
            "Probefahrt",
        ],
    ),
    (
        "oil_service",
        "Ölservice",
        [
            "Motor warmfahren, Öl ablassen",
            "Ölfilter wechseln",
            "Ablassschraube mit neuem Dichtring montieren",
            "Motoröl einfüllen und Ölstand prüfen",
            "Service-Anzeige zurücksetzen",
            "Dichtheit nach Probelauf prüfen",
        ],
    ),
    (
        "wheel_change",
        "Räderwechsel",
        [
            "Räder demontieren und beschriften",
            "Bremsen und Reifen beim Wechsel sichtprüfen",
            "Radnaben reinigen",
            "Räder montieren und mit Drehmoment anziehen",
            "Reifenluftdruck einstellen",
            "Radmuttern nach 50 km nachziehen",
        ],
    ),
    (
        "brake_check",
        "Bremsencheck",
        [
            "Bremsbeläge vorne: Restdicke messen",
            "Bremsbeläge hinten: Restdicke messen",
            "Bremsscheiben auf Verschleiß und Riefen prüfen",
            "Bremsschläuche und Bremsleitungen prüfen",
            "Handbremse prüfen und einstellen",
        ],
    ),
    (
        "pre_inspection",
        "Vorbereitung §57a / Pickerl",
        [
            "Beleuchtungsanlage inklusive Scheinwerfereinstellung prüfen",
            "Bremsanlage prüfen",
            "Lenkung und Fahrwerk prüfen",
            "Reifen und Räder prüfen",
            "Abgasanlage und Abgaswerte prüfen",
            "Sicherheitsgurte, Hupe und Spiegel prüfen",
            "Fahrzeugpapiere und Warnausrüstung prüfen",
        ],
    ),
]


EXTRA_GROUP_KEY = "extra"
EXTRA_GROUP_TITLE = "Zusätzliche Arbeiten"

# Standard works and categories a finished checklist group implies in the history.
GROUP_WORKS = {
    "oil_service": ["engine_oil", "oil_filter"],
    "wheel_change": ["wheel_change"],
    "pre_inspection": ["inspection"],
}
GROUP_CATEGORIES = {
    "wheel_change": "tires",
    "pre_inspection": "inspection",
}


def servicePlanTaskKey(groupKey, index):
    return f"{groupKey}:{index}"


def servicePlanCatalogue():
    """Return {taskKey: (groupKey, groupTitle, taskText)} for all standard tasks."""
    return {
        servicePlanTaskKey(groupKey, index): (groupKey, title, task)
        for groupKey, title, tasks in SERVICE_PLAN_CHECK_GROUPS
        for index, task in enumerate(tasks)
    }
