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
]
