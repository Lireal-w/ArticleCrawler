from scrapy import Request
from urllib.parse import urljoin
from lxml import etree
import re
import math

from ..items import ArticleItem
from ..utils.SunSpider import SunSpider

class SbcnewsSpider(SunSpider):
    name = "sbcnews"
    allowed_domains = ["sbcnews.co.uk"]
    start_urls = ["https://sbcnews.co.uk/category/sportsbook/"]

    def parse(self, response):
        """
        解析列表页：提取文章详情链接 + 处理翻页
        """
        # 1. 提取所有文章卡片中的详情页链接
        article_links = response.css('div.category-post a.sbc-article-card::attr(href)').getall()
        for link in article_links:
            absolute_url = urljoin(response.url, link)
            if self.is_seen_url(absolute_url):
                return # 当遇到已抓取过的链接，直接返回
            yield Request(absolute_url, callback=self.parse_article)

        # 2. 翻页逻辑：寻找“下一页”按钮
        next_page = response.css('div.sbc-pagination a.next.page-numbers::attr(href)').get()
        if next_page:
            absolute_next = urljoin(response.url, next_page)
            self.logger.info(f"Following next page: {absolute_next}")
            yield Request(absolute_next, callback=self.parse)

    def parse_article(self, response):
        """
        解析文章详情页，提取所有字段
        """
        item = ArticleItem()

        # ----- 标题 -----
        title = response.css('h1.post__title::text').get()
        if title:
            item['title'] = title.strip()

        # ----- 摘要（优先使用meta description）-----
        summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            item['summary'] = summary.strip()

        # ----- 网址 -----
        item['url'] = response.url

        # ----- 作者信息 -----
        author_name = response.css('div.post-author__name::text').get()
        if not author_name:
            author_name = response.css('a.post-author__inner .post-author__name::text').get()
        if author_name:
            item['author_name'] = author_name.strip()

        author_avatar = response.css('div.post-author__avatar img::attr(src)').get()
        if author_avatar:
            item['author_avatar'] = urljoin(response.url, author_avatar)

        # ----- 发布时间 -----
        publish_time = response.css('span.post-date::text').get()
        if publish_time:
            item['publish_time'] = publish_time.strip()
        # 最后修改时间未单独提供，暂与发布时间相同
        item['modified_time'] = item.get('publish_time', '')

        # ----- 预计阅读时间 -----
        # 方式1：从 .post__reading-time 获取（如 "Time to read: 3 min"）
        read_time_str = response.css('div.post__reading-time::text').get()
        if read_time_str:
            match = re.search(r'(\d+)', read_time_str)
            if match:
                read_time = match.group(1)
            else:
                read_time = read_time_str.strip()
        else:
            # 方式2：基于正文长度估算（每分钟300字）
            content_text = ' '.join(response.css('div.post__content-inner *::text').getall())
            word_count = len(content_text)
            read_time = str(max(1, math.ceil(word_count / 300)))
        item['read_time'] = read_time

        # ----- 正文HTML处理（清洗广告、脚本等）-----
        content_selector = 'div.post__content-inner'
        content_div = response.css(content_selector)
        if not content_div:
            item['content'] = ''
            item['image_urls'] = []
            yield item
            return

        # 获取 lxml 元素
        content_element = content_div[0].root

        # 删除所有 advertisment 广告块
        for ad in content_element.xpath('.//*[contains(@class, "advertisment")]'):
            parent = ad.getparent()
            if parent is not None:
                parent.remove(ad)

        # 删除所有 script 标签
        for script in content_element.xpath('.//script'):
            parent = script.getparent()
            if parent is not None:
                parent.remove(script)

        # 将清洗后的HTML转为字符串
        cleaned_html = etree.tostring(content_element, encoding='unicode', method='html')
        item['content'] = cleaned_html

        # ----- 提取图片URL列表（用于ImagesPipeline）-----
        img_urls = []
        for img in content_element.xpath('.//img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(response.url, src)
                img_urls.append(absolute_url)
        item['image_urls'] = img_urls

        yield item