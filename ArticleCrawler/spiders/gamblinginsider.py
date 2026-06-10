import scrapy
from urllib.parse import urljoin
import re
import math
from lxml import etree
from ..items import ArticleItem
from ..utils.SunSpider import SunSpider
from ..utils.time import parse_time_to_timestamp

class GamblinginsiderSpider(SunSpider):
    name = "gamblinginsider"
    allowed_domains = ["gamblinginsider.com"]
    start_urls = ["https://www.gamblinginsider.com/news"]

    def parse(self, response):
        """
        解析新闻列表页，提取文章链接和翻页链接
        """
        # 1. 提取所有文章链接
        article_links = response.css('ul.posts-archive-listing li.post__item a.post__item--title::attr(href)').getall()
        if not article_links:
            # 备用选择器
            article_links = response.css('li.post__item a.post__item--thumb::attr(href)').getall()

        self.logger.info(f"Found {len(article_links)} article links on {response.url}")

        for link in article_links:
            absolute_url = response.urljoin(link)
            if self.is_seen_url(absolute_url):continue
            yield scrapy.Request(url=absolute_url, callback=self.parse_article)
            self.mark_url_as_seen(absolute_url)
        # 2. 翻页逻辑：查找下一页链接
        next_page = self.get_next_page_url(response)
        if next_page:
            self.logger.info(f"Following next page: {next_page}")
            yield scrapy.Request(url=next_page, callback=self.parse)

    def get_next_page_url(self, response):
        """
        提取下一页 URL
        """
        # 方法1：从分页导航中提取 a.next.page-numbers 的 href
        next_link = response.css('nav.gi-pagination a.next.page-numbers::attr(href)').get()
        if next_link:
            return response.urljoin(next_link)

        # 方法2：基于 URL 模式构造
        # 当前 URL 可能是 /news 或 /news/page/2
        if '/page/' in response.url:
            # 提取当前页码并加1
            match = re.search(r'/page/(\d+)', response.url)
            if match:
                current_page = int(match.group(1))
                next_page_num = current_page + 1
                # 替换页码部分
                next_url = re.sub(r'/page/\d+', f'/page/{next_page_num}', response.url)
                return next_url
        else:
            # 第一页：/news -> /news/page/2
            base_url = response.url.rstrip('/')
            return f"{base_url}/page/2"
        return None

    def parse_article(self, response):
        """
        解析文章详情页，提取所有需要的字段
        """
        

        item = ArticleItem()

        # ----- 标题 -----
        title = response.css('.post-title h1::text').get()
        if title:
            item['title'] = title.strip()

        # ----- 摘要（优先使用 post-intro，其次 meta description）-----
        summary = response.css('p.post-intro em::text').get()
        if not summary:
            summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            item['summary'] = summary.strip()

        # ----- 文章网址 -----
        item['url'] = response.url

        # ----- 作者信息 -----
        author_name = response.css('.byline-author__name::text').get()
        if author_name:
            item['author_name'] = author_name.strip()
        author_avatar = response.css('.byline-author__avatar img::attr(src)').get()
        if author_avatar:
            item['author_avatar'] = response.urljoin(author_avatar)

        # ----- 时间信息 -----
        # 取 "Updated on" 后面的日期
        publish_time = response.css('.post-byline__item-date::text').get()
        if publish_time:
            item['publish_time'] = parse_time_to_timestamp(publish_time.strip())
        # 没有单独的修改时间，复用发布时间
        item['modified_time'] = item.get('publish_time', '')

        # ----- 预计阅读时间 -----
        # 优先从 twitter:data2 获取（如 "3分钟"）
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            match = re.search(r'(\d+)', read_time_str)
            if match:
                read_time = match.group(1)
            else:
                read_time = read_time_str.strip()
        else:
            # 基于正文估算：每分钟阅读 600 字（中英文混合情况）
            # 正文位置在 .the__content 内，待清洗后计算
            # 先临时获取所有文本
            content_text = ' '.join(response.css('.the__content *::text').getall())
            char_count = len(content_text)
            read_time = str(max(1, math.ceil(char_count / 600)))
        item['read_time'] = read_time

        # ----- 正文 HTML 处理（清洗无关模块，保留文章主体）-----
        content_selector = '.the__content'
        content_div = response.css(content_selector)
        if not content_div:
            item['content'] = ''
            item['image_urls'] = []
            yield item
            return

        # 获取 lxml 元素
        container_element = content_div[0].root

        # 移除不需要的模块（广告、推荐阅读、作者简介等）
        # 这些模块通常有特定的 class
        selectors_to_remove = [
            '.post-categories',
            '.stay-updated',
            '.author-bio',
            '.post-editorial',
            '.social-sharing',
            '.post-hero-image-caption',
            '.yoast_breadcrumb'
        ]
        for sel in selectors_to_remove:
            for elem in container_element.xpath(f'.//*[contains(@class, "{sel.lstrip('.')}")]'):
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)

        # 额外移除任何包含特定 id 或 class 的广告区块（可根据实际情况增加）
        for ad in container_element.xpath('.//div[contains(@class, "ad")]'):
            parent = ad.getparent()
            if parent is not None:
                parent.remove(ad)

        # 移除所有 script 和 style 标签
        for script in container_element.xpath('.//script|.//style'):
            parent = script.getparent()
            if parent is not None:
                parent.remove(script)

        # 获取清洗后的 HTML 字符串
        cleaned_html = etree.tostring(container_element, encoding='unicode', method='html')
        item['content'] = cleaned_html

        # ----- 提取图片 URL（从清洗后的容器中）-----
        img_urls = []
        for img in container_element.xpath('.//img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(response.url, src)
                if absolute_url.startswith('http'):
                    img_urls.append(absolute_url)
        item['image_urls'] = img_urls
        item["cover_image"] = img_urls[0] if img_urls else None
        yield item