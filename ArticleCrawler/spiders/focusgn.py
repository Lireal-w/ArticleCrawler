import scrapy
from urllib.parse import urljoin
from lxml import etree
import re
import math
import datetime

from ..items import ArticleItem
from ..utils.SunSpider import SunSpider


class FocusgnSpider(SunSpider):
    name = "focusgn"
    allowed_domains = ["focusgn.com"]
    start_urls = ["https://focusgn.com/category/sportsbetting-news"]

    def parse(self, response):
        """
        解析新闻列表页，提取文章详情链接并生成请求，同时处理翻页
        """
        article_links = response.css('.news-grid .grid-article a::attr(href)').getall()
        for link in article_links:
            absolute_url = response.urljoin(link)
            if self.is_seen_url(absolute_url):continue
            yield scrapy.Request(url=absolute_url, callback=self.parse_article)
            self.mark_url_as_seen(absolute_url)

        next_page = self.get_next_page_url(response)
        if next_page:
            self.logger.info(f"Follow next page: {next_page}")
            yield scrapy.Request(url=next_page, callback=self.parse)

    def get_next_page_url(self, response):
        """
        提取分页中的“下一页”链接
        根据HTML：<a class="next page-numbers" href="...">Next</a>
        """
        next_link = response.css('a.next.page-numbers::attr(href)').get()
        if next_link:
            return response.urljoin(next_link)
        if '/page/' in response.url:
            current_page = int(re.search(r'/page/(\d+)/', response.url).group(1))
            next_page_num = current_page + 1
            next_url = re.sub(r'/page/\d+/', f'/page/{next_page_num}/', response.url)
            return next_url
        else:
            base = response.url.rstrip('/')
            return f"{base}/page/2/"

    def parse_article(self, response):
        """
        提取文章标题、摘要、作者、时间、阅读时间、正文HTML及图片
        """
        item = ArticleItem()
        title = response.css('h1.entry-title::text').get()
        if title:
            item['title'] = title.strip()

        summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            item['summary'] = summary.strip()

        item['url'] = response.url

        author_name = response.css('.article-author::text').get()
        if author_name:
            match = re.search(r'by\s+(.+)', author_name)
            if match:
                item['author_name'] = match.group(1).strip()
            else:
                item['author_name'] = author_name.strip()
        item['author_avatar'] = ''

        publish_time = response.css('.article-date::text').get()
        if publish_time:
            # item['publish_time'] = publish_time.strip()
            # 将发布日期"05/07/26"转为秒级时间戳
            publish_time = datetime.datetime.strptime(publish_time, "%m/%d/%y")
            item['publish_time'] = publish_time.timestamp()
        # 修改时间：页面未单独提供，暂与发布时间相同
        item['modified_time'] = item.get('publish_time', '')

        # ----- 预计阅读时间 -----
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            # 提取数字，如 "3分钟"
            digits = re.findall(r'\d+', read_time_str)
            if digits:
                read_time = digits[0]
            else:
                read_time = read_time_str
        else:
            content_text = self.extract_text_from_content(response)
            word_count = len(content_text)
            read_time = str(max(1, math.ceil(word_count / 300)))
        item['read_time'] = read_time

        content_div = response.css('.article-content')
        if not content_div:
            item['content'] = ''
            item['image_urls'] = []
            yield item
            return
        content_element = content_div[0].root

        for bad in content_element.xpath('.//div[@id="see-also-container"]'):
            parent = bad.getparent()
            if parent is not None:
                parent.remove(bad)
        for bad in content_element.xpath('.//div[contains(@class, "related-article")]'):
            parent = bad.getparent()
            if parent is not None:
                parent.remove(bad)
        for ad in content_element.xpath('.//*[contains(@class, "fgn_adzone")]'):
            parent = ad.getparent()
            if parent is not None:
                parent.remove(ad)
        for script in content_element.xpath('.//script'):
            parent = script.getparent()
            if parent is not None:
                parent.remove(script)
        cleaned_html = etree.tostring(content_element, encoding='unicode', method='html')
        item['content'] = cleaned_html

        img_urls = []
        for img in content_element.xpath('.//img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(response.url, src)
                img_urls.append(absolute_url)
        item['image_urls'] = img_urls

        yield item

    def extract_text_from_content(self, response):
        """
        辅助方法：从文章正文中提取纯文本，用于字数统计
        """
        content_div = response.css('.article-content')
        if content_div:
            # 简单拼接所有文本
            texts = content_div.css('*::text').getall()
            return ' '.join(texts)
        return ''