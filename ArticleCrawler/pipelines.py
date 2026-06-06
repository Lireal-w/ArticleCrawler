# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import posixpath
import scrapy
from urllib.parse import urlparse
from scrapy.exporters import JsonItemExporter
from itemadapter import ItemAdapter

from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem

class ArticlecrawlerPipeline:
    def process_item(self, item, spider):
        return item

class JsonFilePipeline:
    """将 Item 导出为 JSON 文件，保存到指定目录"""

    def open_spider(self, spider):
        # 1. 获取输出目录（默认 /outfile，可在 settings 中修改）
        output_dir = spider.settings.get('JSON_OUTPUT_DIR', '/outfile')
        # 2. 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        # 3. 构造文件路径：目录/爬虫名称.json
        file_path = os.path.join(output_dir, f"{spider.name}.json")
        # 4. 打开文件并初始化 JsonItemExporter
        self.file = open(file_path, 'wb')
        self.exporter = JsonItemExporter(
            self.file,
            ensure_ascii=False,   # 支持中文
            indent=2              # 格式化输出
        )
        self.exporter.start_exporting()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item

    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.file.close()

class ArticleImagesPipeline(ImagesPipeline):
    """
    下载文章内的图片，并将 item['content'] 中的图片 URL 替换为本地路径
    """

    def get_media_requests(self, item, info):
        # 为每个图片 URL 生成下载请求
        for img_url in item.get('image_urls', []):
            yield scrapy.Request(img_url)

    def file_path(self, request, response=None, info=None, *, item=None):
        # 获取 URL 的路径部分（去掉域名和查询参数）
        parsed = urlparse(request.url)
        path = parsed.path
        if path.startswith('/'):
            path = path[1:]          # 去掉开头的 /
        # 使用 posixpath 规范化路径（保持 /）
        path = posixpath.normpath(path)
        return path

    def item_completed(self, results, item, info):
        # 构建 原始URL -> 本地路径 的映射
        url_to_path = {}
        for ok, res in results:
            if ok:
                url_to_path[res['url']] = res['path']

        # 替换正文中的图片链接
        if 'content' in item and url_to_path:
            content = item['content']
            for original_url, local_path in url_to_path.items():
                # 替换为去掉域名后的绝对路径（前面加 /）
                new_url = f'/{local_path}'
                content = content.replace(original_url, new_url)
            item['content'] = content

        # 清理临时字段
        item.pop('image_urls', None)
        return item