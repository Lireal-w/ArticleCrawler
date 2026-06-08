import scrapy
from urllib.parse import urljoin
import re
import math
from lxml import etree
from ..items import ArticleItem


class IgamingbusinessSpider(scrapy.Spider):
    name = "igamingbusiness"
    allowed_domains = ["igamingbusiness.com"]
    start_urls = ["https://igamingbusiness.com/search/?category=Sports%20betting"]  # 可换成任意列表页

    def parse(self, response):
        """
        列表页解析：提取所有文章链接，并处理翻页
        """
        # 1. 提取文章链接（匹配两种常见的卡片结构）
        # 选择器1：.c-card__title a 或 .qec-results__title-link
        article_links = response.css('article.c-card .c-card__title a::attr(href)').getall()
        if not article_links:
            article_links = response.css('.qec-results__title-link::attr(href)').getall()
        # 去重
        article_links = list(dict.fromkeys(article_links))
        
        self.logger.info(f"Found {len(article_links)} article links on {response.url}")
        
        for link in article_links:
            absolute_url = urljoin(response.url, link)
            yield scrapy.Request(url=absolute_url, callback=self.parse_article)
            break
        
        # 2. 翻页逻辑：查找“下一页”按钮
        next_page_url = self.get_next_page_url(response)
        if next_page_url:
            self.logger.info(f"Following next page: {next_page_url}")
            yield scrapy.Request(url=next_page_url, callback=self.parse)

    def get_next_page_url(self, response):
        """
        提取下一页URL，优先从显式的“下一页”按钮获取，否则尝试构造
        """
        if '?' in response.url:
            # 处理 ?page=2 形式
            match = re.search(r'[?&]page=(\d+)', response.url)
            if match:
                current = int(match.group(1))
                next_page_num = current + 1
                if next_page_num >= 3:
                    return None
                next_url = re.sub(r'([?&])page=\d+', rf'\1page={next_page_num}', response.url)
                return next_url
        else:
            return f"{response.url}&page=2"
        return None

    def parse_article(self, response):
        """
        解析文章详情页，填充所有 Item 字段
        """
        item = ArticleItem()
        title = response.css('h1.c-single-post-title::text').get()
        if title:
            item['title'] = title.strip()
        summary = response.css('div.c-single-post-excerpt strong::text').get()
        if not summary:
            summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            item['summary'] = summary.strip()
        item['url'] = response.url
        subtitle = response.css('div.c-single-post-subtitle::text').get()
        if subtitle:
            parts = subtitle.split('|')
            if len(parts) >= 1:
                date_str = parts[0].strip()
                item['publish_time'] = date_str
            if len(parts) >= 2:
                author_part = parts[1].strip()
                if author_part.startswith('By '):
                    author_part = author_part[3:]
                item['author_name'] = author_part
        item['author_avatar'] = ''
        item['modified_time'] = item.get('publish_time', '')
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            match = re.search(r'(\d+)', read_time_str)
            if match:
                read_time = match.group(1)
            else:
                read_time = read_time_str.strip()
        else:
            content_text = ' '.join(response.css('#post-* p::text').getall())
            word_count = len(content_text)
            read_time = str(max(1, math.ceil(word_count / 300)))
        item['read_time'] = read_time
        
        cover = response.css('.c-single-post-featured-image::attr(src)').get()
        if not cover:
            # 备选：查找文章开头的 <picture> 内的 img
            cover = response.css('picture img.wp-post-image::attr(src)').get()
        if not cover:
            # 再备选：任何 class 包含 wp-post-image 的 img
            cover = response.css('img.wp-post-image::attr(src)').get()
        if cover:
            item['cover_image'] = urljoin(response.url, cover)
        else:
            item['cover_image'] = ''
        content_div = response.css('div.u-user-content')
        if not content_div:
            content_div = response.css('article .entry-content')
        if content_div:
            content_el = content_div[0].root
            for ad in content_el.xpath('.//*[contains(@class, "c-ad-slot-item")]'):
                parent = ad.getparent()
                if parent is not None:
                    parent.remove(ad)
            for rec in content_el.xpath('.//*[contains(@class, "idio-recommendations")]'):
                parent = rec.getparent()
                if parent is not None:
                    parent.remove(rec)
            for author_info in content_el.xpath('.//*[contains(@class, "wp-block-qi-blocks-author-info")]'):
                parent = author_info.getparent()
                if parent is not None:
                    parent.remove(author_info)
            for script in content_el.xpath('.//script'):
                parent = script.getparent()
                if parent is not None:
                    parent.remove(script)
            for style in content_el.xpath('.//style'):
                parent = style.getparent()
                if parent is not None:
                    parent.remove(style)
            cleaned_html = etree.tostring(content_el, encoding='unicode', method='html')
            item['content'] = cleaned_html
            img_urls = []
            for img in content_el.xpath('.//img'):
                src = img.get('src')
                if src:
                    absolute_url = urljoin(response.url, src)
                    img_urls.append(absolute_url)
            item['image_urls'] = img_urls
        else:
            item['content'] = ''
            item['image_urls'] = []
        yield item