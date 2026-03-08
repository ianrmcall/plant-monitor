from .ecuagenera import EcuageneraScraper
from .ecuageneraus import EcuageneraUSScraper
from .kartuz import KartuzScraper
from .andysorchids import AndysOrchidsScraper
from .lyndonlyon import LyndonLyonScraper

SCRAPERS = [
    EcuageneraScraper(),
    EcuageneraUSScraper(),
    KartuzScraper(),
    AndysOrchidsScraper(),
    LyndonLyonScraper(),
]
