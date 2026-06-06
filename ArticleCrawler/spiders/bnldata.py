import re
import json
import scrapy
from scrapy import Request
from urllib.parse import urljoin
from lxml import etree
import math
from ..items import ArticleItem  # 导入你定义的Item类

def extract_text_and_images(element):
    """
    递归提取文本和 img 标签，去除所有其他标签。
    """
    parts = []
    # 使用 XPath 选择所有文本节点和 img 元素（按文档顺序）
    for node in element.xpath('.//text() | .//img'):
        if isinstance(node, etree._Element):
            # 是 img 标签，保留其原始 HTML
            parts.append(etree.tostring(node, encoding='unicode'))
        else:
            # 是文本节点
            text = node
            if text.strip():  # 只保留非空文本，可以根据需要调整
                parts.append(text)
    return ''.join(parts)

class BnldataSpider(scrapy.Spider):
    name = "bnldata"
    allowed_domains = ["bnldata.com.br"]
    start_urls = ["https://bnldata.com.br/editorias/"]
    
    def parse(self, response):
        """
        1. 解析起始页面，提取security值，并获取当前页面已有的文章
        """
        pattern = r"security':\s*'([a-f0-9]+)'"
        security_match = re.search(pattern, response.text, re.DOTALL)
        
        if security_match:
            self.security_token = security_match.group(1)
            self.logger.info(f"成功提取 security 值: {self.security_token}")
        else:
            self.logger.error("未找到 security 值，请检查正则表达式或页面内容")
            self.security_token = None
            # 若无法提取，可考虑停止爬取或使用默认值（不推荐）
            return
        
        self.logger.info(f"成功提取 security 值: {self.security_token}")
        
        articles = response.css('div#cards-area > article.card')
        for article in articles:
            article_url = article.css('div.card__image a::attr(href)').get()
            if article_url:
                yield scrapy.Request(url=article_url, callback=self.parse_article)
        
        current_page = 1
        next_page = current_page + 1

        ajax_url = "https://bnldata.com.br/wp-admin/admin-ajax.php"
        ajax_data = {
            'action': 'load_posts_by_ajax',
            'page': str(next_page),
            'security': self.security_token
        }
        
        yield scrapy.FormRequest(
            url=ajax_url,
            formdata=ajax_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}, 
            callback=self.parse_ajax_posts,
            meta={'current_page': next_page}
        )
    
    def parse_ajax_posts(self, response):
        """
        处理通过AJAX加载的更多文章列表
        响应内容通常是HTML片段，直接包含 article 标签
        """
        articles = response.css('article.card')
        for article in articles:
            article_url = article.css('div.card__image a::attr(href)').get()
            if article_url:
                yield scrapy.Request(url=article_url, callback=self.parse_article)
        
        if response.text.strip():
            current_page = response.meta.get('current_page', 1)
            next_page = current_page + 1
            if next_page > 8:
                return
            ajax_url = response.url
            ajax_data = {
                'action': 'load_posts_by_ajax',
                'page': str(next_page),
                'security': self.security_token
            }
            yield scrapy.FormRequest(
                url=ajax_url,
                formdata=ajax_data,
                headers={'X-Requested-With': 'XMLHttpRequest'},
                callback=self.parse_ajax_posts,
                meta={'current_page': next_page}
            )
    
    def parse_article(self, response):
        """
        解析文章详情页，提取所有需要的字段。
        """
  

        item = ArticleItem()

        # ----- 标题 -----
        # 优先使用 h1 标签（class 为 fs-24 lh-36 fw-medium）
        title = response.css('h1.fs-24.lh-36.fw-medium::text').get()
        if not title:
            title = response.css('h1::text').get()
        item['title'] = title.strip() if title else 'N/A'

        # ----- 摘要 -----
        # 优先使用 meta description
        summary = response.css('meta[name="description"]::attr(content)').get()
        if not summary:
            # 尝试从文章开头的 figcaption 或第一个段落提取
            summary = response.css('figure.wp-caption figcaption::text').get()
            if not summary:
                first_p = response.css('div.single-editor p:first-child::text').get()
                if first_p:
                    summary = first_p.strip()[:200] + '...'
                else:
                    summary = 'N/A'
        item['summary'] = summary.strip()

        # ----- 网址 -----
        # 使用 canonical 链接或当前 URL
        canonical = response.css('link[rel="canonical"]::attr(href)').get()
        item['url'] = canonical if canonical else response.url

        # ----- 作者信息 -----
        # 作者姓名：从页面结构 "按：马尼奥·何塞" 或 JSON-LD 中提取
        author_name = response.css('div.single-header__info strong:contains("按：") + ::text').get()
        if author_name:
            author_name = author_name.strip()
        else:
            # 尝试从 Yoast JSON-LD 提取
            json_ld = response.css('script[type="application/ld+json"]::text').get()
            if json_ld:
                try:
                    data = json.loads(json_ld)
                    # 查找 author 节点
                    for graph in data.get('@graph', []):
                        if graph.get('@type') == 'Article' and 'author' in graph:
                            author_name = graph['author'].get('name')
                            break
                except:
                    pass
        item['author_name'] = author_name if author_name else 'N/A'

        # 作者头像：本页面未提供，留空（可尝试从 JSON-LD 扩展）
        item['author_avatar'] = ''

        # ----- 时间信息 -----
        # 发布时间：meta property="article:published_time"
        publish_time = response.css('meta[property="article:published_time"]::attr(content)').get()
        if not publish_time:
            # 尝试从 JSON-LD 获取 datePublished
            json_ld = response.css('script[type="application/ld+json"]::text').get()
            if json_ld:
                try:
                    data = json.loads(json_ld)
                    for graph in data.get('@graph', []):
                        if graph.get('@type') == 'Article' and 'datePublished' in graph:
                            publish_time = graph['datePublished']
                            break
                except:
                    pass
        item['publish_time'] = publish_time if publish_time else 'N/A'

        # 最后修改时间：本页面没有明确的 modified_time，使用发布时间代替
        modified_time = response.css('meta[property="article:modified_time"]::attr(content)').get()
        if not modified_time:
            modified_time = publish_time  # 回退
        item['modified_time'] = modified_time if modified_time else 'N/A'

        # ----- 预计阅读时间 -----
        # 方法1：从 twitter:data2 获取（如 "3分钟"）
        read_time_str = response.css('meta[name="twitter:data2"]::attr(content)').get()
        if read_time_str:
            # 提取数字，例如 "3分钟" -> 3
            match = re.search(r'(\d+)', read_time_str)
            if match:
                read_time = match.group(1)
            else:
                read_time = read_time_str.strip()
        else:
            # 方法2：基于字数估算（假设每分钟300字）
            # 获取文章正文内容（可自行扩展选择器）
            content_text = ' '.join(response.css('div.single-editor p::text').getall())
            word_count = len(content_text)
            read_time = str(max(1, math.ceil(word_count / 300)))
        item['read_time'] = read_time
        # 获取正文容器
        editor_sel = response.css('div.single-editor')
        if not editor_sel:
            item['content'] = ''
            item['image_urls'] = []
            yield item
            return
        editor_element = editor_sel[0].root
        for fig in editor_element.xpath('.//figure[contains(@class, "wp-caption")]'):
            parent = fig.getparent()
            if parent is not None:
                parent.remove(fig)
        for ad in editor_element.xpath('.//*[contains(@class, "sync-adwrapper")]'):
            parent = ad.getparent()
            if parent is not None:
                parent.remove(ad)
        cleaned_html = etree.tostring(editor_element, encoding='unicode')
        item['content'] = cleaned_html

        img_urls = []
        for img in editor_element.xpath('.//img'):
            src = img.get('src')
            if src:
                absolute_url = urljoin(response.url, src)
                img_urls.append(absolute_url)
        item['image_urls'] = img_urls
        # item['content'] = extract_text_and_images(editor_element)
        yield item