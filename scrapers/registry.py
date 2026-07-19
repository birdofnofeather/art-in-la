"""Lists the active scrapers. Import-based so adding one is a single line.

When you add a new venue scraper:

1. Drop it in `scrapers/venues/` as a module exporting a `Scraper` subclass.
2. Append its `Scraper` class to `SCRAPERS` below.
3. Make sure its `venue_id` matches an entry in `public/data/venues.json`.

That's it — the runner picks it up automatically.
"""
from __future__ import annotations

from .venues.lacma import Scraper as LACMA
from .venues.hammer import Scraper as Hammer
from .venues.moca import Scraper as MOCA
from .venues.the_broad import Scraper as TheBroad
from .venues.getty import Scraper as Getty
from .venues.norton_simon import Scraper as NortonSimon
from .venues.huntington import Scraper as Huntington
from .venues.self_help_graphics import Scraper as SelfHelpGraphics
from .venues.craft_contemporary import Scraper as CraftContemporary
from .venues.redcat import Scraper as REDCAT
from .venues.ica_la import Scraper as ICALA
from .venues.lace import Scraper as LACE
from .venues.eighteenth_street import Scraper as EighteenthStreet
from .venues.human_resources_la import Scraper as HumanResources

# --- Session 1: museum/institution expansion ---
from .venues.wende import Scraper as Wende
from .venues.vincent_price import Scraper as VincentPrice
from .venues.pvac import Scraper as PVAC
from .venues.molaa import Scraper as MOLAA
from .venues.mak_center import Scraper as MAKCenter
from .venues.marciano import Scraper as Marciano
from .venues.armory_pasadena import Scraper as ArmoryPasadena
from .venues.janm import Scraper as JANM
from .venues.autry import Scraper as Autry
from .venues.fowler import Scraper as Fowler
from .venues.academy_museum import Scraper as AcademyMuseum
from .venues.usc_fisher import Scraper as USCFisher

# --- Session 2: gallery expansion ---
from .venues.angels_gate import Scraper as AngelsGate
from .venues.avenue_50 import Scraper as Avenue50
from .venues.las_fotos_project import Scraper as LasFotosProject

# --- Session 3: gallery & institution expansion ---
from .venues.lbma import Scraper as LBMA
from .venues.joan import Scraper as JOAN

# --- Session 4: museum coverage ---
from .venues.moca_geffen import Scraper as MOCAGeffen
from .venues.skirball import Scraper as Skirball
from .venues.benton import Scraper as Benton
from .venues.torrance_art_museum import Scraper as TorranceArtMuseum
from .venues.forest_lawn import Scraper as ForestLawn
from .venues.brand_library import Scraper as BrandLibrary

# --- Session 5: gallery expansion ---
from .venues.pieter import Scraper as Pieter

# --- Session 6: museum coverage ---
from .venues.museum_of_tolerance import Scraper as MuseumOfTolerance
from .venues.pacific_asia_museum import Scraper as PacificAsiaMuseum

# --- Session 7: institution expansion ---
from .venues.art_practice import Scraper as ArtPractice
from .venues.calarts import Scraper as CalArts
from .venues.lamag import Scraper as LAMAG

# --- Session 8: institution expansion ---
from .venues.sciarc import Scraper as SciArc
from .venues.sparc import Scraper as SPARC
from .venues.beyond_baroque import BeyondBaroqueScraper as BeyondBaroque
from .venues.corita_art_center import CoritaArtCenterScraper as CoritaArtCenter
from .venues.la_plaza import LaPlazaScraper as LaPlaza
from .venues.clockshop import Scraper as Clockshop

# --- Round 8: CAAM (Eventbrite), MOAH (Eventbrite collection), Laband (LMU) ---
from .venues.caam import Scraper as CAAM
from .venues.moah import Scraper as MOAH
from .venues.laband import Scraper as Laband

# --- Round 9: ESMoA, Luckman, JACCC, ArtCenter ---
from .venues.esmoa import Scraper as ESMoA
from .venues.luckman import Scraper as Luckman
from .venues.jaccc import Scraper as JACCC
from .venues.artcenter import Scraper as ArtCenter

SCRAPERS = [
    LACMA,
    Hammer,
    MOCA,
    TheBroad,
    Getty,
    NortonSimon,
    Huntington,
    SelfHelpGraphics,
    CraftContemporary,
    REDCAT,
    ICALA,
    LACE,
    EighteenthStreet,
    HumanResources,
    # Session 1
    Wende,
    VincentPrice,
    PVAC,
    MOLAA,
    MAKCenter,
    Marciano,
    ArmoryPasadena,
    JANM,
    Autry,
    Fowler,
    AcademyMuseum,
    USCFisher,
    # Session 2
    AngelsGate,
    Avenue50,
    LasFotosProject,
    # Session 3
    LBMA,
    JOAN,
    # Session 4: museums
    MOCAGeffen,
    Skirball,
    Benton,
    TorranceArtMuseum,
    ForestLawn,
    BrandLibrary,
    # Session 5: gallery expansion
    Pieter,
    # Session 6: museum coverage
    MuseumOfTolerance,
    PacificAsiaMuseum,
    # Session 7: institution expansion
    ArtPractice,
    CalArts,
    LAMAG,
    # Session 8: institution expansion
    SciArc,
    SPARC,
    # Session 9: community / literary spaces
    BeyondBaroque,
    CoritaArtCenter,
    LaPlaza,
    Clockshop,
    CAAM,
    MOAH,
    Laband,
    ESMoA,
    Luckman,
    JACCC,
    ArtCenter,
]
