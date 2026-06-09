import re
import math
from urllib.parse import urljoin
from lxml import etree
import scrapy
from ..items import ArticleItem
from ..utils.SunSpider import SunSpider


class AffpapaSpider(SunSpider):
    name = "affpapa"
    allowed_domains = ["affpapa.com"]
    start_urls = [
        "https://affpapa.com/category/top-news/",
        "https://affpapa.com/category/industry-news/",
        "https://affpapa.com/category/operator-news/",
        "https://affpapa.com/category/affiliate-news/",
        "https://affpapa.com/category/igaming-quarterly-reports/"
    ]

    # ------------------------------------------------------------------
    # 列表页处理：提取文章链接 + 翻页
    # ------------------------------------------------------------------
    def parse(self, response):
        """
        解析列表页，提取文章链接，跟进翻页
        """
        # 1. 提取所有文章链接（<article class="custompost"> 里的 h3 > a）
        article_links = response.css('article.custompost h3 a::attr(href)').getall()
        for link in article_links:
            absolute_url = response.urljoin(link)
            if self.is_seen_url(absolute_url):
                return
            yield scrapy.Request(url=absolute_url, callback=self.parse_article)
            self.mark_url_as_seen(absolute_url)

        # 2. 翻页：获取下一页的链接
        next_page = self.get_next_page_url(response)
        if next_page:
            yield scrapy.Request(url=next_page, callback=self.parse)

    def get_next_page_url(self, response):
        """
        提取下一页链接（支持显式按钮和 URL 构造两种方式）
        """
        # 方式1：寻找 <a class="next page-numbers">
        next_link = response.css('a.next.page-numbers::attr(href)').get()
        if next_link:
            return response.urljoin(next_link)

        # 方式2：基于 URL 模式构造（适用于 /category/xxx/pages/2/ 格式）
        # 当前 URL 可能类似 https://affpapa.com/category/top-news/pages/2/
        match = re.search(r'/pages/(\d+)/?$', response.url)
        if match:
            current_page = int(match.group(1))
            next_page_num = current_page + 1
            next_url = re.sub(r'/pages/\d+/', f'/pages/{next_page_num}/', response.url)
            return next_url
        else:
            # 第一页：/category/top-news/  -->  /category/top-news/pages/2/
            base = response.url.rstrip('/')
            return f"{base}/pages/2/"
    # ------------------------------------------------------------------
    # 详情页解析
    # ------------------------------------------------------------------
    def parse_article(self, response):
        item = ArticleItem()

        # ----- 标题 -----
        title = response.css('div.heading_custom h1::text').get()
        if title:
            item['title'] = title.strip()

        # ----- 摘要（优先从 meta description 获取）-----
        summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            item['summary'] = summary.strip()

        # ----- 网址 -----
        item['url'] = response.url

        # ----- 作者姓名与头像 -----
        # 作者姓名位于底部的 .author_by 区域
        author_name = response.css('div.author_by .author_name .author_url::text').get()
        if not author_name:
            author_name = response.css('div.author_by .author_name a::text').get()
        if author_name:
            item['author_name'] = author_name.strip()
        # 作者头像
        author_avatar = response.css('div.author__picture img::attr(src)').get()
        if author_avatar:
            item['author_avatar'] = response.urljoin(author_avatar)

        # ----- 发布时间 -----
        publish_time = response.css('div.new_meta time::attr(datetime)').get()
        if not publish_time:
            publish_time = response.css('div.new_meta .date time::text').get()
        if publish_time:
            item['publish_time'] = publish_time.strip()
        else:
            # 备用：从文章底部的 meta 时间提取
            item['publish_time'] = response.css('div.meta time::text').get(default='').strip()
        # 最后修改时间：页面未单独提供，复用发布时间
        item['modified_time'] = item.get('publish_time', '')

        # ----- 预计阅读时间 -----
        read_time = self.extract_read_time(response)
        item['read_time'] = read_time

        # ----- 正文 HTML 清洗与图片提取 -----
        content_html, image_urls = self.clean_and_extract(response)
        item['content'] = content_html
        item['image_urls'] = image_urls

        yield item

    # ------------------------------------------------------------------
    # 辅助方法：提取阅读时间
    # ------------------------------------------------------------------
    def extract_read_time(self, response):
        # 方法1：从 twitter:data2 获取（如 "3 minutes"）
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            match = re.search(r'(\d+)', read_time_str)
            if match:
                return match.group(1)
            else:
                return read_time_str.strip()

        # 方法2：基于正文纯文本长度估算（假设每分钟 300 字）
        # 先获取正文区域内的所有文本
        content_sel = response.css('div.theiaStickySidebars')
        if not content_sel:
            content_sel = response.css('div.contentss.box')
        if content_sel:
            text = ' '.join(content_sel.css('*::text').getall())
            word_count = len(text)
            read_time = max(1, math.ceil(word_count / 300))
            return str(read_time)

        return "1"

    # ------------------------------------------------------------------
    # 辅助方法：清洗正文 HTML 并提取图片 URL
    # ------------------------------------------------------------------
    def clean_and_extract(self, response):
        """
        返回 (cleaned_html, image_urls)
        cleaned_html: 清洗后的文章主体 HTML 字符串
        image_urls: 正文中所有图片的绝对 URL 列表
        """
        # 定位正文容器
        content_sel = response.css('div.theiaStickySidebars')
        if not content_sel:
            content_sel = response.css('div.contentss.box')
        if not content_sel:
            return '', []

        # 获取第一个匹配元素的 lxml 节点
        element = content_sel[0].root

        # 需要移除的无关区块（使用 XPath 选择器）
        remove_selectors = [
            './/div[contains(@class, "cats_footer")]',
            './/div[contains(@class, "tags__and_socials")]',
            './/div[contains(@class, "author_by")]',
            './/div[contains(@class, "news cont aff")]',
            './/div[contains(@class, "mobile")]',
            './/div[contains(@class, "email_subs_banner_wrapper")]',
            './/div[contains(@class, "top_operators")]',
            './/div[contains(@class, "latest_news")]',
            './/div[contains(@class, "mob_banners")]',
            './/style',          # 移除所有 <style> 标签
            './/script',         # 移除所有 <script> 标签
        ]

        for xpath in remove_selectors:
            for node in element.xpath(xpath):
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)

        # 提取清洗后的 HTML
        cleaned_html = etree.tostring(element, encoding='unicode', method='html')

        # 提取图片 URL（从清洗后的树中提取，避免重复或损坏的图片）
        image_urls = []
        for img in element.xpath('.//img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(response.url, src)
                if absolute_url not in image_urls:
                    image_urls.append(absolute_url)

        return cleaned_html, image_urls