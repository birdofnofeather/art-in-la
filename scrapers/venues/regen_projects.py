from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "regen_projects"
    events_url = "https://www.regenprojects.com/exhibitions"
    source_label = "regenprojects.com"
