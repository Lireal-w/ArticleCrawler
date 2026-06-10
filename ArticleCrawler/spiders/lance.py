import scrapy
import re
from datetime import datetime
from urllib.parse import urljoin
from ..items import ArticleItem

from ..utils.SunSpider import SunSpider

class LanceSpider(SunSpider):
    name = "lance"
    allowed_domains = ["lance.com.br"]
    start_urls = ["https://www.lance.com.br/mais-noticias"]

    def parse(self, response):
        """
        解析新闻列表页，提取文章链接并生成详情页请求。
        如果遇到2025年之前的文章，则停止当前页解析且不再翻页。
        """
        article_cards = response.css('section.flex.gap-4.relative')
        stop_crawling = False

        for card in article_cards:
            # 提取卡片中的发布时间（第一个 <time> 标签）
            time_text = card.css('time::text').get()
            if time_text:
                # 日期格式如 "09/06/2026" (日/月/年)
                try:
                    day, month, year = map(int, time_text.strip().split('/'))
                    if year < 2025:
                        # 发现2025年之前的文章，停止处理当前页及翻页
                        stop_crawling = True
                        break
                except (ValueError, AttributeError):
                    # 日期解析失败则忽略，继续处理
                    pass

            # 获取文章详情页链接
            relative_url = card.css('a.absolute.size-full.top-0.left-0::attr(href)').get()
            if relative_url:
                # if self.is_seen_url(relative_url):
                #     return
                article_url = response.urljoin(relative_url)
                yield scrapy.Request(url=article_url, callback=self.parse_article)
                self.mark_url_as_seen(relative_url)

        # 如果没有遇到旧文章，且存在下一页，则继续翻页
        if not stop_crawling:
            next_page = response.xpath('(//nav/ul/li[last()]/a/@href)[2]').get()
            print(f"Processing next page: {next_page}")
            if next_page:
                next_page_url = response.urljoin(next_page)
                yield scrapy.Request(url=next_page_url, callback=self.parse)
        else:
            print(f"Stopped crawling at {response.url} due to old articles.")

    def parse_article(self, response):
        """
        解析文章详情页，提取所需字段并生成ArticleItem，同时将时间字符串转为时间戳。
        """
        item = ArticleItem()

        # 基础信息
        item['title'] = self._extract_title(response)
        item['summary'] = self._extract_summary(response)
        item['url'] = response.url
        item['author_name'], item['author_avatar'] = self._extract_author_info(response)
        item['cover_image'] = self._extract_cover_image(response)

        # 时间信息（字符串格式）
        publish_str = self._extract_publish_time(response)
        modified_str = publish_str  # 页面未单独提供修改时间，暂用发布时间
        item['publish_time'] = self._datetime_to_timestamp(publish_str) if publish_str else None
        item['modified_time'] = self._datetime_to_timestamp(modified_str) if modified_str else None

        # 正文处理
        content_html, image_urls = self._process_content(response)
        item['content'] = content_html
        item['image_urls'] = image_urls

        # 预计阅读时间（根据正文纯文本长度估算）
        item['read_time'] = self._estimate_read_time(content_html)

        yield item

    # ---------- 辅助方法 ----------
    def _extract_title(self, response):
        title = response.css('h1::text').get()
        return title.strip() if title else None

    def _extract_summary(self, response):
        summary = response.css('h2.text-base.md\\:text-lg::text').get()
        return summary.strip() if summary else None

    def _extract_author_info(self, response):
        author_name = response.xpath('//a[starts-with(@href, "/autor/")]/text()').get()
        author_name = author_name.strip() if author_name else None
        author_avatar = None  # 页面未提供头像
        return author_name, author_avatar

    def _extract_publish_time(self, response):
        """返回格式如 '09/06/2026 16:55' 的字符串"""
        time_spans = response.xpath('//div[contains(@class, "text-[12px]") and contains(@class, "text-[#7A7D7F]")]//span/text()').getall()
        if len(time_spans) >= 2:
            date_part = time_spans[0].strip()
            time_part = time_spans[1].strip()
            return f"{date_part} {time_part}"
        return None

    def _extract_cover_image(self, response):
        cover_url = response.css('figure.w-full.mb-6.flex.flex-col.items-center img::attr(src)').get()
        return response.urljoin(cover_url) if cover_url else None

    def _process_content(self, response):
        content_selector = response.css('.paywall-content')
        if not content_selector:
            return "", []

        html_str = content_selector.get()
        # 移除广告区块（包含 "continua após a publicidade" 的 section）
        ad_pattern = r'<section[^>]*>.*?continua após a publicidade.*?</section>'
        html_str = re.sub(ad_pattern, '', html_str, flags=re.DOTALL)
        # 移除推荐区域（id="suggested-news" 的整个 section）
        html_str = re.sub(r'<section[^>]*id="suggested-news".*?</section>', '', html_str, flags=re.DOTALL)

        # 转换图片链接为绝对URL并收集
        from scrapy.selector import Selector
        temp_sel = Selector(text=html_str)
        image_urls = []
        for img in temp_sel.css('img'):
            src = img.attrib.get('src')
            if src:
                abs_url = response.urljoin(src)
                image_urls.append(abs_url)
                html_str = html_str.replace(f'src="{src}"', f'src="{abs_url}"')
        return html_str, image_urls

    def _estimate_read_time(self, html_content):
        if not html_content:
            return 1
        text = re.sub(r'<[^>]+>', '', html_content)
        char_count = len(text)
        minutes = max(1, (char_count + 299) // 300)  # 每分钟300字符
        return minutes

    def _datetime_to_timestamp(self, datetime_str):
        """
        将 "dd/mm/yyyy HH:MM" 格式的字符串转为 Unix 时间戳（秒）
        例如 "09/06/2026 16:55" -> 秒级时间戳
        """
        try:
            # 注意格式：日/月/年 时:分
            dt = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
            # 返回本地时间的时间戳（假设无时区信息）
            return int(dt.timestamp())
        except (ValueError, TypeError):
            return None