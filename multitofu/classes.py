"""Map a class name from a window title to an icon slug in assets/skin."""
import unicodedata

SLUGS = {
    "feca", "osamodas", "enutrof", "sram", "xelor", "ecaflip", "eniripsa",
    "iop", "cra", "sadida", "sacrieur", "pandawa", "roublard", "zobal",
    "steamer", "eliotrope", "huppermage", "ouginak", "forgelance",
}

# English / Spanish client names -> French slug used by the upstream artwork
ALIASES = {
    "sacrier": "sacrieur",
    "rogue": "roublard",
    "masqueraider": "zobal",
    "foggernaut": "steamer",
    "srambad": "sram",
    "enutrofo": "enutrof",
    "ocra": "cra",
    "crâ": "cra",
    "craa": "cra",
    "zurcarak": "zobal",
    "yopuka": "iop",
    "steamerz": "steamer",
    "eliatrope": "eliotrope",
}


def normalize(text):
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch for ch in text.lower() if ch.isalnum())


def to_slug(class_name):
    """Return an icon slug, or None when the class is not recognised."""
    key = normalize(class_name)
    if not key:
        return None
    if key in SLUGS:
        return key
    if key in ALIASES:
        return ALIASES[key]
    for slug in SLUGS:
        if key.startswith(slug) or slug.startswith(key):
            return slug
    return None
