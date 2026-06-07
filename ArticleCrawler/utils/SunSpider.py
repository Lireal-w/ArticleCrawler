import scrapy
import json
import os

class SunSpider(scrapy.Spider):
    """基于 URL 去重的增量爬虫基类"""
    name = "sun"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 用于在内存中存储已爬取过的 URL 集合，提供 O(1) 的查询效率
        self.seen_urls = set()
        self.count = 0  # 计数器
        # 初始化时加载历史记录
        self.load_seen_urls()
    
    def load_seen_urls(self):
        """从本地磁盘加载已爬取 URL 的记录"""
        file_path = f'./crawled_articles/{self.name}.json'
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                self.seen_urls = set(json.load(f))

    def save_seen_urls(self):
        """将内存中的已爬取 URL 记录持久化到本地磁盘"""
        file_path = f'./crawled_articles/{self.name}.json'
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(list(self.seen_urls), f, ensure_ascii=False, indent=2)
        
    def is_seen_url(self, url):
        """判断 URL 是否已经被爬取过"""
        return url in self.seen_urls
    
    def mark_url_as_seen(self, url):
        """将 URL 标记为已爬取"""
        self.seen_urls.add(url)
        self.count += 1
        # 每新增 100 条记录就保存一次，防止崩溃丢失
        if self.count % 100 == 0:
            self.save_seen_urls()

    def closed(self, reason):
        """爬虫关闭时的回调函数，用于保存状态"""
        self.save_seen_urls()
