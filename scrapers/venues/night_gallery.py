from ..base import BaseScraper


class Scraper(BaseScraper):
    venue_id = "night_gallery"
    events_url = "https://nightgallery.ca/exhibitions"
    source_label = "nightgallery.ca"
