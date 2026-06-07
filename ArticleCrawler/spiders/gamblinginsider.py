import scrapy


class GamblinginsiderSpider(scrapy.Spider):
    name = "gamblinginsider"
    allowed_domains = ["gamblinginsider.com"]
    start_urls = ["https://gamblinginsider.com"]

    def parse(self, response):
        pass
