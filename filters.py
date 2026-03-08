"""
Blocklist-based filtering for plant alerts.

Disabled by default — set FILTERS_ENABLED=true in your .env to activate.
Add words to BLOCKED_KEYWORDS or family names to BLOCKED_FAMILIES to suppress them.
"""

BLOCKED_KEYWORDS: list[str] = [
    # Example: "easy care", "common", "pothos"
]

BLOCKED_FAMILIES: list[str] = [
    # Example: "Orchidaceae"
]

# Maps plant family → list of genera in that family.
# Used when BLOCKED_FAMILIES is set — any genus in a blocked family is suppressed.
FAMILY_GENERA: dict[str, list[str]] = {
    "Orchidaceae": [
        "Acanthophippium", "Acropera", "Ada", "Aerides", "Agapetes", "Anacheilium",
        "Angraecum", "Anguloa", "Appendicula", "Arachnis", "Arpophyllum", "Aspasia",
        "Barbosella", "Barkeria", "Bifrenaria", "Bletilla", "Bothriochilus",
        "Brachtia", "Brassavola", "Brassia", "Bulbophyllum", "Cadetia", "Calanthe",
        "Cattleya", "Ceratostylis", "Chelonistele", "Chondrorhyncha", "Cirrhopetalum",
        "Cischweinfia", "Cleisostoma", "Cochlioda", "Coelia", "Coelogyne", "Constantia",
        "Cryptophoranthus", "Cryptopus", "Cymbidium", "Cynorkis", "Cyrtochilum",
        "Dendrobium", "Dendrochilum", "Diplocaulobium", "Dracula", "Dryadella",
        "Elleanthus", "Encyclia", "Epidendrum", "Epigeneium", "Eria", "Gastrochilus",
        "Gomesa", "Gongora", "Holcoglossum", "Huntleya", "Isabelia", "Isochilus",
        "Jacquiniella", "Jumellea", "Kefersteinia", "Laelia", "Lemboglossum",
        "Lepanthes", "Leptotes", "Liparis", "Lockhartia", "Lycaste", "Malaxis",
        "Masdevallia", "Maxillaria", "Mediocalcar", "Megaclinium", "Mesospinidium",
        "Miltonia", "Miltonioides", "Miltoniopsis", "Myoxanthus", "Nanodes",
        "Neobenthamia", "Neofinetia", "Neolauchea", "Nidema", "Oberonia", "Octomeria",
        "Odontoglossum", "Oerstedella", "Oncidium", "Ornithocephalus", "Osmoglossum",
        "Paphinia", "Paphiopedilum", "Papilionanthe", "Pholidota", "Phymatidium",
        "Physosiphon", "Platystele", "Pleione", "Pleurothallis", "Plocoglottis",
        "Podochilus", "Polystachya", "Ponera", "Porroglossum", "Psychilis", "Racinaea",
        "Reldia", "Restrepia", "Restrepiella", "Restrepiopsis", "Rodriguezia",
        "Rudolfiella", "Saccolabium", "Sarcochilus", "Scaphosepalum", "Scaphyglottis",
        "Schoenorchis", "Schomburgkia", "Scuticaria", "Sedirea", "Sigmatostalix",
        "Smitinandia", "Sobralia", "Sophronitelia", "Spathoglottis", "Sphyrospermum",
        "Spiranthes", "Stelis", "Stenia", "Stenoglottis", "Stereochilus", "Sunipia",
        "Symphyglossum", "Thelasis", "Thrixspermum", "Tolumnia", "Trichoceros",
        "Trichoglottis", "Trichosalpinx", "Trichotosia", "Trigonidium", "Trisetella",
        "Tuberolabium", "Vanda", "Zootrophion", "Zygopetalum",
    ],
    "Gesneriaceae": [
        "Achimenes", "Aeschynanthus", "Alsobia", "Chirita", "Codonanthe",
        "Codonatanthus", "Columnea", "Drymonia", "Episcia", "Kohleria", "Nematanthus",
        "Petrocosmea", "Primulina", "Saintpaulia", "Sinningia", "Streptocarpella",
        "Streptocarpus",
    ],
    "Araceae": [
        "Aglaonema", "Alocasia", "Amorphophallus", "Anthurium", "Caladium",
        "Colocasia", "Dieffenbachia", "Epipremnum", "Monstera", "Philodendron",
        "Pothos", "Rhaphidophora", "Scindapsus", "Spathiphyllum", "Syngonium",
        "Xanthosoma", "Zamioculcas",
    ],
    "Begoniaceae": ["Begonia"],
    "Bromeliaceae": [
        "Aechmea", "Billbergia", "Cryptanthus", "Dyckia", "Guzmania", "Neoregelia",
        "Nidularium", "Pitcairnia", "Puya", "Racinaea", "Tillandsia", "Vriesea",
        "Werauhia",
    ],
}

# Flattened reverse-lookup: genus → family (built once at import)
_GENUS_TO_FAMILY: dict[str, str] = {
    genus: family
    for family, genera in FAMILY_GENERA.items()
    for genus in genera
}


def apply_filters(products: list, enabled: bool) -> list:
    """
    Filter out products matching the blocklist rules.
    If enabled=False, returns the list unchanged.
    """
    if not enabled:
        return products

    result = []
    for p in products:
        name_lower = p["name"].lower()

        # Keyword blocklist
        if any(kw.lower() in name_lower for kw in BLOCKED_KEYWORDS):
            continue

        # Family blocklist — check first word of name as genus
        genus = p["name"].split()[0]
        family = _GENUS_TO_FAMILY.get(genus)
        if family and family in BLOCKED_FAMILIES:
            continue

        result.append(p)

    return result
