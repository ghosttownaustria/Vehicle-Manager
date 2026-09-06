"""Resolve brand logos from a pinned public catalogue, without server requests."""

import json
from pathlib import Path
import unicodedata


LOGO_REVISION = "3f0929e70e0a9a2a502063edc4b3e5c0146cba74"
LOGO_BASE_URL = f"https://cdn.jsdelivr.net/gh/vehiclespecs/brand-logos@{LOGO_REVISION}/"


def normalizeBrand(brand):
    normalized = unicodedata.normalize("NFKD", brand or "").casefold()
    return "".join(character for character in normalized if character.isalnum())


with (Path(__file__).resolve().parent / "data/brand-logos/brands.json").open(
    encoding="utf-8"
) as catalogue:
    BRAND_FILES = {normalizeBrand(brand): filename for brand, filename in json.load(catalogue).items()}

BRAND_ALIASES = {
    "vw": "volkswagen",
    "mercedes": "mercedesbenz",
    "benz": "mercedesbenz",
    "mb": "mercedesbenz",
    "mercedesamg": "mercedesbenz",
    "dsautomobiles": "ds",
    "chevy": "chevrolet",
    "alfaromeoautomobiles": "alfaromeo",
}


def brandLogoUrl(brand):
    key = normalizeBrand(brand)
    filename = BRAND_FILES.get(BRAND_ALIASES.get(key, key))
    return LOGO_BASE_URL + filename if filename else None
