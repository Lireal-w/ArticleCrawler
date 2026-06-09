import scrapy
from urllib.parse import urljoin
import re
import math
from lxml import etree

from ..items import ArticleItem


class EnvmediaSpider(scrapy.Spider):
    name = "envMedia"
    allowed_domains = ["env.media"]
    # 建议实际使用时改为 "https://env.media/press-release/" 或保留首页
    start_urls = ["https://env.media"]

    def parse(self, response):
        """
        第一步 & 第二步 & 第三步：解析列表页，提取文章链接，并处理翻页
        """
        # 1. 找出所有文章卡片
        article_cards = response.css('div.gb-grid-column.gb-query-loop-item')
        if not article_cards:
            self.logger.warning(f"未找到文章卡片，请检查选择器或URL: {response.url}")
            return

        for card in article_cards:
            # 提取文章详情页链接
            link = card.css('h2.gb-headline a::attr(href)').get()
            if not link:
                continue
            article_url = response.urljoin(link)

            # 提取作者头像（列表页存在，详情页没有，需要通过meta传递）
            avatar = card.css('figure.gb-block-image img.avatar::attr(src)').get()
            if avatar:
                avatar_url = response.urljoin(avatar)
            else:
                avatar_url = None

            # 发起详情请求，将头像URL暂存于meta
            yield scrapy.Request(
                url=article_url,
                callback=self.parse_article,
                meta={'author_avatar': avatar_url}
            )

        # 3. 翻页逻辑
        next_url = self.get_next_page_url(response)
        if next_url:
            self.logger.info(f"发现下一页: {next_url}")
            yield scrapy.Request(url=next_url, callback=self.parse)

    def get_next_page_url(self, response):
        """
        提取下一页链接，优先使用显式分页按钮，否则按URL模式构造
        """
        # 方式1: 查找 class 包含 'next' 的分页链接
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            return response.urljoin(next_page)

        # 方式2: 根据URL模式构造（例如 /page/2/）
        # 匹配当前URL中是否有 '/page/数字/'
        match = re.search(r'/page/(\d+)/?$', response.url)
        if match:
            current = int(match.group(1))
            next_num = current + 1
            next_url = re.sub(r'/page/\d+/', f'/page/{next_num}/', response.url)
            return next_url
        else:
            # 第一页的情况：如 /press-release/  -> /press-release/page/2/
            if not response.url.endswith('/page/1/') and '/page/' not in response.url:
                base = response.url.rstrip('/')
                return f"{base}/page/2/"
        return None

    def parse_article(self, response):
        """
        第四步：解析文章详情页，填充所有Item字段
        """
        item = ArticleItem()

        # 从meta获取列表页传递的作者头像
        author_avatar = response.meta.get('author_avatar')
        if author_avatar:
            item['author_avatar'] = author_avatar

        # ----- 标题 -----
        title = response.css('h1.entry-title::text').get()
        if title:
            item['title'] = title.strip()

        # ----- 摘要（优先使用meta description）-----
        summary = response.css('meta[name="description"]::attr(content)').get()
        if summary:
            item['summary'] = summary.strip()
        else:
            # 后备：取正文前150字
            first_paragraph = response.css('.entry-content p:first-child::text').get()
            if first_paragraph:
                item['summary'] = first_paragraph.strip()[:200]

        # ----- 网址 -----
        item['url'] = response.url

        # ----- 作者姓名 -----
        author_name = response.css('.wp-block-post-author-name a::text').get()
        if not author_name:
            author_name = response.css('.wp-block-post-author-name::text').get()
        if author_name:
            item['author_name'] = author_name.strip()

        # ----- 发布时间 -----
        pub_time = response.css('.wp-block-post-date time::attr(datetime)').get()
        if not pub_time:
            pub_time = response.css('.wp-block-post-date time::text').get()
        if pub_time:
            item['publish_time'] = pub_time.strip()
        item['modified_time'] = item.get('publish_time', '')

        # ----- 预计阅读时间 -----
        read_time = self.get_read_time(response)
        item['read_time'] = read_time

        # ----- 正文HTML清洗 + 图片提取 -----
        content_html, img_urls, cover_image = self.extract_content_and_images(response)
        item['content'] = content_html
        item['image_urls'] = img_urls
        if cover_image:
            item['cover_image'] = cover_image

        yield item

    def get_read_time(self, response):
        """
        预计阅读时间：优先从twitter:data2获取，否则按字数估算（每分钟300字）
        """
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            # 提取数字，例如 "3分钟" -> "3"
            match = re.search(r'(\d+)', read_time_str)
            if match:
                return match.group(1)
            else:
                return read_time_str.strip()

        # 按字数估算
        text = ' '.join(response.css('.entry-content *::text').getall())
        word_count = len(text)
        minutes = max(1, math.ceil(word_count / 300))
        return str(minutes)

    def extract_content_and_images(self, response):
        """
        从 .entry-content 提取正文HTML，清洗无关元素，提取图片URL和封面图
        返回 (cleaned_html, image_urls, cover_image_url)
        """
        content_sel = response.css('.entry-content')
        if not content_sel:
            return '', [], None

        # 获取第一个元素的lxml节点
        content_node = content_sel[0].root
        # 深拷贝，避免影响原始响应
        from copy import deepcopy
        tree = deepcopy(content_node)

        # 需要移除的元素（保留文章主体，去除干扰）
        to_remove = [
            './/div[contains(@class, "wp-block-post-date")]',
            './/div[contains(@class, "wp-block-post-author-name")]',
            './/p[contains(@class, "wpml-ls")]',          # 语言切换提示
            './/div[contains(@class, "sharedaddy")]',     # 分享按钮
            './/div[contains(@class, "jp-relatedposts")]', # 相关文章
            './/script',
            './/iframe',
            './/*[contains(@class, "advertisement")]',
            './/*[contains(@class, "recommended")]',
        ]
        for xpath_expr in to_remove:
            for elem in tree.xpath(xpath_expr):
                parent = elem.getparent()
                if parent is not None:
                    parent.remove(elem)

        # 提取所有图片URL（包括封面图）
        img_urls = []
        cover_image = None

        # 封面图（特色图片）单独处理
        featured_img = response.css('figure.wp-block-post-featured-image img::attr(src)').get()
        if featured_img:
            cover_image = urljoin(response.url, featured_img)
            # 封面图也加入图片列表
            img_urls.append(cover_image)

        # 正文中的图片
        for img in tree.xpath('.//img'):
            src = img.get('src')
            if src:
                abs_url = urljoin(response.url, src)
                img_urls.append(abs_url)

        # 将清洗后的HTML转为字符串
        cleaned_html = etree.tostring(tree, encoding='unicode', method='html')
        return cleaned_html, img_urls, cover_image