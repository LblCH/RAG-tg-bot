import scrapy
from trafilatura import extract

class SiteSpider(scrapy.Spider):
    name = "SFN"
    allowed_domains = ["sfn-am.ru"]  # замените на ваш домен
    start_urls = ["https://sfn-am.ru"]

    def parse(self, response):
        # Извлекаем HTML
        html = response.text
        # Используем trafilatura для чистки текста
        text = extract(html, include_comments=False, include_tables=True)

        if text:
            yield {
                "url": response.url,
                "text": text.strip()
            }

        # Переходим по ссылкам на этом сайте
        for href in response.css("a::attr(href)").getall():
            yield response.follow(href, self.parse)