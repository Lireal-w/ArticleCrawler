import re
import math
import scrapy
from lxml import etree
from urllib.parse import urljoin
from ..items import ArticleItem
from ..utils.SunSpider import SunSpider

class SigmaSpider(SunSpider):
    name = "sigma"
    allowed_domains = ["sigma.world"]
    start_urls = ["https://sigma.world/latest-news/online/"]

    def parse(self, response):
        """
        解析列表页，提取文章链接并跟进分页
        """
        # 1. 提取所有文章链接（两种卡片）
        # 大卡片（.news-big-article-card）中的链接
        big_article_links = response.css('div.news-big-article-card a.featured-link::attr(href)').getall()
        # 普通卡片（.news-article-card）中的链接
        normal_article_links = response.css('div.news-article-card a.post-title-link::attr(href)').getall()
        
        all_links = big_article_links + normal_article_links
        self.logger.info(f"Found {len(all_links)} article links on {response.url}")

        for link in all_links:
            # 确保链接是绝对路径
            absolute_url = response.urljoin(link)
            if self.is_seen_url(absolute_url):continue
            yield scrapy.Request(url=absolute_url, callback=self.parse_article,
                                 meta={'source_url': response.url})
            self.mark_url_as_seen(absolute_url)

        # 2. 翻页逻辑：寻找下一页链接
        next_page = self.get_next_page_url(response)
        if next_page:
            self.logger.info(f"Following next page: {next_page}")
            yield scrapy.Request(url=next_page, callback=self.parse,
                                 meta={'source_url': response.url})

    def get_next_page_url(self, response):
        """
        分页逻辑
        """
        next_page = response.css('a.next.page-numbers:not(.prev)::attr(href)').get()
        if next_page:
            return urljoin(response.url, next_page)
        if '/page/' in response.url:
            current_page = int(re.search(r'/page/(\d+)/', response.url).group(1))
            next_page_num = current_page + 1
            return re.sub(r'/page/\d+/', f'/page/{next_page_num}/', response.url)
        else:
            # 处理第一页: 当前 URL 是 /online/，则下一页是 /online/page/2/
            return f"{response.url.rstrip('/')}/page/2/"

    def parse_article(self, response):
        item = ArticleItem()

        # ----- 标题 -----
        title = response.css('h1.news-title::text').get()
        if title:
            item['title'] = title.strip()

        # ----- 摘要 -----
        summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            item['summary'] = summary.strip()

        # ----- 网址 -----
        item['url'] = response.url

        # ----- 作者姓名 -----
        author_name = response.css('.news-meta-wrapper a[href*="/authors/"]::text').get()
        if author_name:
            item['author_name'] = author_name.strip()

        # ----- 作者头像 -----
        author_avatar = response.css('.news-meta-wrapper img.rounded-full::attr(src)').get()
        if author_avatar:
            item['author_avatar'] = response.urljoin(author_avatar)

        # ----- 发布时间 -----
        publish_time = response.css('.post-date::text').get()
        if publish_time:
            item['publish_time'] = publish_time.strip()
        item['modified_time'] = item.get('publish_time', '')

        # ----- 预计阅读时间 -----
        # 方法1：从 twitter:data2 获取（如 "3分钟"）
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            match = re.search(r'(\d+)', read_time_str)
            if match:
                read_time = match.group(1)
            else:
                read_time = read_time_str.strip()
        else:
            # 方法2：基于正文长度估算（每分钟 600 字）
            content_text = ' '.join(response.css('.styled-content-wrapper *::text').getall())
            word_count = len(content_text)
            read_time = str(max(1, math.ceil(word_count / 600)))
        item['read_time'] = read_time

        # ----- 正文 HTML 处理（保留原始 HTML，移除 .wp-block-columns 等无关元素）-----
        container_sel = response.css('.styled-content-wrapper')
        if not container_sel:
            item['content'] = ''
            item['image_urls'] = []
            yield item
            return

        # 获取 lxml 元素（使用 .root）
        container_element = container_sel[0].root

        # 移除所有 class 包含 'wp-block-columns' 的元素（推荐阅读等板块）
        for bad_elem in container_element.xpath('.//*[contains(@class, "wp-block-columns")]'):
            parent = bad_elem.getparent()
            if parent is not None:
                parent.remove(bad_elem)

        # 可选：移除广告容器（参考原有风格）
        for ad in container_element.xpath('.//*[contains(@class, "sync-adwrapper")]'):
            parent = ad.getparent()
            if parent is not None:
                parent.remove(ad)

        # 移除所有 script 标签
        for script in container_element.xpath('.//script'):
            parent = script.getparent()
            if parent is not None:
                parent.remove(script)

        # 将清理后的 HTML 转为字符串
        cleaned_html = etree.tostring(container_element, encoding='unicode')
        item['content'] = cleaned_html

        # ----- 提取图片 URL -----
        img_urls = []
        for img in container_element.xpath('.//img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(response.url, src)
                img_urls.append(absolute_url)
        item['image_urls'] = img_urls

        yield item