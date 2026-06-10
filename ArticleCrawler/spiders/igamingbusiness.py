import scrapy
import json
from urllib.parse import urljoin
import re
import math
from lxml import etree

from ..items import ArticleItem
from ..utils.SunSpider import SunSpider
from ..utils.time import parse_time_to_timestamp

class IgamingbusinessSpider(SunSpider):
    name = "igamingbusiness"
    allowed_domains = None

    api_url = "https://clus1-dcs1.synotiosearch.net/api/as/v1/engines/igamingbusiness-com/search.json"
    api_headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'authorization': 'Bearer search-2t8y4cc8ej9yh9cufhujes9v',
        'content-type': 'application/json',
        'origin': 'https://igamingbusiness.com',
        'referer': 'https://igamingbusiness.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        'x-elastic-client-meta': 'ent=8.5.1-legacy,js=browser,t=8.5.1-legacy,ft=universal',
        'x-swiftype-client': 'elastic-app-search-javascript',
        'x-swiftype-client-version': '8.5.1',
    }

    async def start(self):
        json_data = {
            'query': '',
            'page': {'size': 20, 'current': 1},
            'filters': {
                'all': [
                    {'blog_id': '1'},
                    {'object_type': ['post', 'brand_view', 'company_news', 'content_os']},
                    {'is_visible': 'true'},
                    {'is_private': 'false'},
                ],
            },
            'facets': {
                'category': {'type': 'value', 'size': 100},
                'content_type': {'type': 'value', 'size': 100},
                'region': {'type': 'value', 'size': 100},
                'post_tag': {'type': 'value', 'size': 100},
            },
            'sort': {'timestamp': 'desc'},
        }
        yield scrapy.Request(
            url=self.api_url,
            method='POST',
            headers=self.api_headers,
            body=json.dumps(json_data),
            callback=self.parse,
            meta={'json_data': json_data},
        )

    def parse(self, response):
        data = response.json()
        results = data.get('results', [])
        for result in results:
            # 从 API 提取已有字段
            api_data = {
                'title': result.get('title', {}).get('raw'),
                'summary': result.get('excerpt', {}).get('raw'),
                'url': result.get('url', {}).get('raw'),
                'publish_time': result.get('timestamp', {}).get('raw'),
                'modified_time': result.get('last_modified_date', {}).get('raw'),
                'cover_image': result.get('image_url', {}).get('raw'),  # 缩略图
            }
            article_url = api_data['url']
            if article_url:
                if self.is_seen_url(article_url):continue
                yield scrapy.Request(
                    url=article_url,
                    callback=self.parse_article,
                    meta={'api_data': api_data},
                )
                self.mark_url_as_seen(article_url)

        # 翻页
        page_info = data.get('meta', {}).get('page', {})
        current = page_info.get('current', 1)
        total_pages = page_info.get('total_pages', 1)
        if current < total_pages:
            next_json = response.meta['json_data'].copy()
            next_json['page']['current'] = current + 1
            yield scrapy.Request(
                url=self.api_url,
                method='POST',
                headers=self.api_headers,
                body=json.dumps(next_json),
                callback=self.parse,
                meta={'json_data': next_json},
            )

    def parse_article(self, response):
        item = ArticleItem()
        api_data = response.meta.get('api_data', {})

        # ----- 优先使用 API 数据 -----
        item['title'] = api_data.get('title') or ''
        item['summary'] = api_data.get('summary') or ''
        item['url'] = api_data.get('url') or response.url
        item['publish_time'] = parse_time_to_timestamp(api_data.get('publish_time'))
        item['modified_time'] = parse_time_to_timestamp(api_data.get('modified_time'))
        item['cover_image'] = api_data.get('cover_image') or ''

        # ----- 以下字段 API 未提供，需从 HTML 解析 -----
        # 作者姓名
        author_name = response.css('div.c-single-post-subtitle::text').get()
        if author_name and '|' in author_name:
            parts = author_name.split('|')
            if len(parts) >= 2:
                author_part = parts[1].strip()
                if author_part.startswith('By '):
                    author_part = author_part[3:]
                item['author_name'] = author_part
        else:
            item['author_name'] = ''

        # 作者头像（页面无提供，保持空）
        item['author_avatar'] = ''

        # 预计阅读时间
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

        # 正文 HTML 清洗和图片提取
        content_div = response.css('div.u-user-content')
        if not content_div:
            content_div = response.css('article .entry-content')
        if content_div:
            content_el = content_div[0].root
            # 移除广告、推荐、脚本等
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