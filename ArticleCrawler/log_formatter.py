from scrapy.logformatter import LogFormatter

class QuietLogFormatter(LogFormatter):
    def scraped(self, item, response, spider):
        # 返回 None 表示不输出该条 item 的日志
        return None
