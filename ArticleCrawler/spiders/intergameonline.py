import scrapy
import re
import math
from urllib.parse import urljoin
from lxml import etree

from ..items import ArticleItem
from ..utils.SunSpider import SunSpider
from ..utils.time import parse_time_to_timestamp


class IntergameonlineSpider(SunSpider):
    name = "intergameonline"
    allowed_domains = ["intergameonline.com"]
    start_urls = ["https://www.intergameonline.com/sports-betting/news"]  # 新闻列表起始页

    def parse(self, response):
        """
        解析列表页：提取所有文章链接，并处理翻页
        """
        # 1. 提取文章链接（两种卡片布局）
        # 第一种：row-cols-2 row-cols-lg-4 内的卡片
        article_links = response.css('div.row-cols-2.row-cols-lg-4 a.card::attr(href)').getall()
        # 第二种：第二个 row-cols-2 row-cols-md-3 row-cols-lg-4 内的卡片
        article_links += response.css('div.row-cols-2.row-cols-md-3.row-cols-lg-4 a.card::attr(href)').getall()

        # 去重并转为绝对URL
        for link in set(article_links):
            absolute_url = response.urljoin(link)
            if self.is_seen_url(absolute_url):continue
            yield scrapy.Request(url=absolute_url, callback=self.parse_article)
            self.mark_url_as_seen(absolute_url)

        # 2. 翻页逻辑：寻找“Next page”按钮
        next_page = response.css('a.btn[aria-label="Next page"]::attr(href)').get()
        if next_page:
            next_url = response.urljoin(next_page)
            self.logger.info(f"Following next page: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_article(self, response):
        """
        解析文章详情页，提取所需字段
        """
        item = ArticleItem()

        # ----- 基础信息 -----
        # 标题
        title = response.css('h1.heading-large::text').get()
        if title:
            item['title'] = title.strip()
        # 摘要（从副标题获取）
        summary = response.css('h2.text-lead::text').get()
        if summary:
            item['summary'] = summary.strip()
        # 网址
        item['url'] = response.url

        # ----- 作者信息 -----
        # 作者姓名：位于 "by" 后面的链接文本
        author_name = response.css('div.text-byline a:contains("by") ~ a::text').get()
        if not author_name:
            # 备选：直接找作者链接
            author_name = response.css('div.text-byline a[href*="about"]::text').get()
        if author_name:
            item['author_name'] = author_name.strip()
        # 作者头像：当前页面未提供，留空
        item['author_avatar'] = ''

        # ----- 时间信息 -----
        # 发布时间：例如 "May 27, 2026"
        publish_time = response.css('div.text-byline .text-uppercase::text').get()
        if publish_time:
            item['publish_time'] = parse_time_to_timestamp(publish_time.strip())
        else:
            # 备选：从卡片头部提取
            item['publish_time'] = ''
        # 最后修改时间：页面未单独提供，与发布时间相同
        item['modified_time'] = item['publish_time']

        # ----- 正文容器处理（清洗 + 图片提取）-----
        # 正文所在的容器：article.card-headline 下的 .col 中，不包含右侧图片浮动的部分
        # 使用 XPath 定位：排除包含 .float-end 的父级？更简单：取所有 .card-body 下面的 .col 中非浮动列
        content_div = response.xpath('//article[contains(@class, "headline-card")]//div[contains(@class, "card-body")]/div[contains(@class, "col")][not(contains(@class, "float-end"))]')
        if not content_div:
            # 备用选择器：直接取 .card-body 内的最后一个 .col（正文区域）
            content_div = response.css('.card-body .col:last-child')

        if content_div:
            # 获取第一个匹配元素的 root (lxml element)
            container = content_div[0].root
            # 移除广告、推荐阅读等无关元素（根据实际HTML结构调整）
            # 示例：移除 class 包含 "adbanner" 的元素
            for ad in container.xpath('.//*[contains(@class, "adbanner")]'):
                parent = ad.getparent()
                if parent is not None:
                    parent.remove(ad)
            # 移除脚本
            for script in container.xpath('.//script'):
                parent = script.getparent()
                if parent is not None:
                    parent.remove(script)

            # 将清洗后的 HTML 转为字符串
            cleaned_html = etree.tostring(container, encoding='unicode', method='html')
            item['content'] = cleaned_html

            # 提取图片 URL（从清洗后的容器中）
            image_urls = []
            for img in container.xpath('.//img'):
                src = img.get('src')
                if src:
                    absolute_url = urljoin(response.url, src)
                    image_urls.append(absolute_url)
            item['image_urls'] = image_urls
        else:
            item['content'] = ''
            item['image_urls'] = []

        # ----- 预计阅读时间 -----
        # 优先从 meta 标签获取（如 twitter:data2）
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            match = re.search(r'(\d+)', read_time_str)
            if match:
                read_time = match.group(1)
            else:
                read_time = read_time_str.strip()
        else:
            # 基于正文纯文本长度估算（假设 600 字/分钟）
            if item.get('content'):
                # 从清理后的 HTML 提取纯文本
                text_content = ' '.join(etree.HTML(item['content']).xpath('//text()'))
                char_count = len(text_content.strip())
                read_time = str(max(1, math.ceil(char_count / 600)))
            else:
                read_time = '1'
        item['read_time'] = read_time

        # ----- 封面图片 -----
        # 从详情页主图获取（.card-category-image img 的 src）
        cover_img = response.css('.card-category-image img::attr(src)').get()
        if cover_img:
            item['cover_image'] = urljoin(response.url, cover_img)
        else:
            item['cover_image'] = ''

        # ImagesPipeline 需要 images 字段（由 pipeline 自动填充），初始为空
        item['images'] = []

        yield item