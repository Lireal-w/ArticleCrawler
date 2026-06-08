# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ArticlecrawlerItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class ArticleItem(scrapy.Item):
    # 文章标题
    title = scrapy.Field()
    
    # 文章摘要
    summary = scrapy.Field()
    
    # 文章网址（唯一标识）
    url = scrapy.Field()
    
    # 作者信息
    author_name = scrapy.Field()      # 作者姓名
    author_avatar = scrapy.Field()    # 作者头像URL
    
    # 时间信息
    publish_time = scrapy.Field()     # 发布时间
    modified_time = scrapy.Field()    # 最后修改时间
    
    # 预计阅读时间（可在爬虫中根据字数或随机生成，单位：分钟）
    read_time = scrapy.Field()
    
    content = scrapy.Field()      # 正文 HTML（图片替换后）
    image_urls = scrapy.Field()   # 临时存储图片 URL 列表
    images = scrapy.Field()       # ImagesPipeline 结果

    # 封面图 URL
    cover_image = scrapy.Field()