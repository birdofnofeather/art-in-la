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
from .venues.hauser_wirth import Scraper as HauserWirth
from .venues.hauser_wirth_weho import Scraper as HauserWirthWeHo
from .venues.david_kordansky import Scraper as DavidKordansky
from .venues.regen_projects import Scraper as RegenProjects
from .venues.self_help_graphics import Scraper as SelfHelpGraphics
from .venues.craft_contemporary import Scraper as CraftContemporary
from .venues.redcat import Scraper as REDCAT
from .venues.ica_la import Scraper as ICALA
from .venues.lace import Scraper as LACE
from .venues.vielmetter import Scraper as Vielmetter
from .venues.night_gallery import Scraper as NightGallery
from .venues.the_pit import Scraper as ThePit
from .venues.blum import Scraper as BLUM
from .venues.gagosian_bh import Scraper as GagosianBH
from .venues.eighteenth_street import Scraper as EighteenthStreet
from .venues.human_resources_la import Scraper as HumanResources
from .venues.francois_ghebaly import Scraper as FrancoisGhebaly
from .venues.commonwealth_council import Scraper as CommonwealthCouncil
from .venues.anat_ebgi import Scraper as AnatEbgi

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
from .venues.lehmann_maupin_la import Scraper as LehmannMaupinLA
from .venues.roberts_projects import Scraper as RobertsProjects
from .venues.zwirner_la import Scraper as ZwirnerLA
from .venues.usc_fisher import Scraper as USCFisher
from .venues.sprueth_magers import Scraper as SpruethMagers
from .venues.parrasch_heijnen import Scraper as ParraschHeijnen
from .venues.chateau_shatto import Scraper as ChateauShatto
from .venues.moran_moran import Scraper as MoranMoran
from .venues.nicodim import Scraper as Nicodim

# --- Session 2: gallery expansion ---
from .venues.diane_rosenstein import Scraper as DianeRosenstein
from .venues.luis_de_jesus import Scraper as LuisDeJesus
from .venues.cirrus_gallery import Scraper as CirrusGallery
from .venues.luhring_augustine_la import Scraper as LuhringAugustineLA
from .venues.harpers_la import Scraper as HarpersLA
from .venues.rosegallery import Scraper as RoseGallery
from .venues.wilding_cran import Scraper as WildingCran
from .venues.philip_martin import Scraper as PhilipMartin
from .venues.sebastian_gladstone import Scraper as SebastianGladstone
from .venues.nonaka_hill import Scraper as NonakaHill
from .venues.tanya_bonakdar import Scraper as TanyaBonakdar
from .venues.various_small_fires import Scraper as VariousSmallFires
from .venues.angels_gate import Scraper as AngelsGate
from .venues.avenue_50 import Scraper as Avenue50
from .venues.gallery_luisotti import Scraper as GalleryLuisotti
from .venues.karma_la import Scraper as KarmaLA
from .venues.richard_heller import Scraper as RichardHeller
from .venues.craig_krull import Scraper as CraigKrull
from .venues.charlie_james import Scraper as CharlieJames
from .venues.over_the_influence import Scraper as OverTheInfluence
from .venues.las_fotos_project import Scraper as LasFotosProject

# --- Session 3: gallery & institution expansion ---
from .venues.peter_fetterman import Scraper as PeterFetterman
from .venues.shulamit_nazarian import Scraper as ShulamitNazarian
from .venues.track_16 import Scraper as Track16
from .venues.parker_gallery import Scraper as ParkerGallery
from .venues.ochi import Scraper as Ochi
from .venues.william_turner import Scraper as WilliamTurner
from .venues.edward_cella import Scraper as EdwardCella
from .venues.lbma import Scraper as LBMA
from .venues.joan import Scraper as JOAN
from .venues.pace_la import Scraper as PaceLA
from .venues.lisson_la import Scraper as LissonLA
from .venues.kohn_gallery import Scraper as KohnGallery

# --- Session 4: museum coverage ---
from .venues.moca_geffen import Scraper as MOCAGeffen
from .venues.skirball import Scraper as Skirball
from .venues.benton import Scraper as Benton
from .venues.torrance_art_museum import Scraper as TorranceArtMuseum
from .venues.forest_lawn import Scraper as ForestLawn
from .venues.brand_library import Scraper as BrandLibrary

# --- Session 5: gallery expansion ---
from .venues.matthew_marks import Scraper as MatthewMarks
from .venues.hannah_hoffman import Scraper as HannahHoffman
from .venues.make_room import Scraper as MakeRoom
from .venues.hashimoto import Scraper as Hashimoto
from .venues.marian_goodman import Scraper as MarianGoodman
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

SCRAPERS = [
    LACMA,
    Hammer,
    MOCA,
    TheBroad,
    Getty,
    NortonSimon,
    Huntington,
    HauserWirth,
    HauserWirthWeHo,
    DavidKordansky,
    RegenProjects,
    SelfHelpGraphics,
    CraftContemporary,
    REDCAT,
    ICALA,
    LACE,
    Vielmetter,
    NightGallery,
    ThePit,
    BLUM,
    GagosianBH,
    EighteenthStreet,
    HumanResources,
    FrancoisGhebaly,
    CommonwealthCouncil,
    AnatEbgi,
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
    LehmannMaupinLA,
    RobertsProjects,
    ZwirnerLA,
    USCFisher,
    SpruethMagers,
    ParraschHeijnen,
    ChateauShatto,
    MoranMoran,
    Nicodim,
    # Session 2
    DianeRosenstein,
    LuisDeJesus,
    CirrusGallery,
    LuhringAugustineLA,
    HarpersLA,
    RoseGallery,
    WildingCran,
    PhilipMartin,
    SebastianGladstone,
    NonakaHill,
    TanyaBonakdar,
    VariousSmallFires,
    AngelsGate,
    Avenue50,
    GalleryLuisotti,
    KarmaLA,
    RichardHeller,
    CraigKrull,
    CharlieJames,
    OverTheInfluence,
    LasFotosProject,
    # Session 3
    PeterFetterman,
    ShulamitNazarian,
    Track16,
    ParkerGallery,
    Ochi,
    WilliamTurner,
    EdwardCella,
    LBMA,
    JOAN,
    PaceLA,
    LissonLA,
    KohnGallery,
    # Session 4: museums
    MOCAGeffen,
    Skirball,
    Benton,
    TorranceArtMuseum,
    ForestLawn,
    BrandLibrary,
    # Session 5: gallery expansion
    MatthewMarks,
    HannahHoffman,
    MakeRoom,
    Hashimoto,
    MarianGoodman,
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
]
