# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import time
import posixpath
import scrapy
from urllib.parse import urlparse
from scrapy.exporters import JsonItemExporter
from itemadapter import ItemAdapter
import json

from db import DB, ts_to_datetime
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
        # 目录添加日期前缀
        output_dir = os.path.join(output_dir, time.strftime('%Y%m%d'))
        # 2. 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        # 3. 构造文件路径：目录/爬虫名称_时间戳.json
        # 生成时间戳（秒级）
        timestamp = int(time.time())
        file_path = os.path.join(output_dir, f"{spider.name}_{timestamp}.json")
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

class MySQLPipeline:
    """将爬取的文章数据提交到 MySQL 数据库的管道"""

    def open_spider(self, spider):
        """爬虫启动时连接数据库"""
        self.db = DB()
        try:
            self.db.connect()
            spider.logger.info("✅ MySQL 数据库连接成功")
        except Exception as e:
            spider.logger.error(f"❌ MySQL 数据库连接失败: {e}")
            raise

    def close_spider(self, spider):
        """爬虫关闭时断开数据库连接"""
        if self.db:
            self.db.close()
            spider.logger.info("✅ MySQL 数据库连接已关闭")

    def process_item(self, item, spider):
        """处理并插入数据"""
        # 1. 基础字段提取与校验
        url = item.get('url')
        if not url:
            raise DropItem("缺少唯一标识 url，丢弃该 Item")

        # 2. 处理 JSON 字段 (对应数据库中的 JSON 类型)
        image_urls = json.dumps(item.get('image_urls', []), ensure_ascii=False)
        images = json.dumps(item.get('images', []), ensure_ascii=False)

        # 3. 处理时间字段 (时间戳转为 Y-m-d H:i:s)
        publish_time = ts_to_datetime(item.get('publish_time'))
        modified_time = ts_to_datetime(item.get('modified_time'))

        # 4. 组装插入参数
        insert_kwargs = {
            "url": url,
            "title": item.get('title', ''),
            "summary": item.get('summary', ''),
            "author_name": item.get('author_name', ''),
            "author_avatar": item.get('author_avatar', ''),
            "publish_time": publish_time,
            "modified_time": modified_time,
            "read_time": item.get('read_time', 0),
            "content": item.get('content', ''),
            "image_urls": image_urls,
            "images": images,
            "cover_image": item.get('cover_image', ''),
            "is_published": 0  # 爬虫刚抓取的数据默认未发布
        }

        # 5. 执行插入
        try:
            self.db.insert(**insert_kwargs)
            spider.logger.info(f"✅ 文章入库成功: {item.get('title')}")
        except Exception as e:
            spider.logger.error(f"❌ 文章入库失败 [{url}]: {e}")
            raise DropItem(f"数据库插入失败: {e}")

        return item
