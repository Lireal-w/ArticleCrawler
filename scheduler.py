from apscheduler.schedulers.background import BackgroundScheduler
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from ArticleCrawler.spiders import spiders  # 假设 spiders 是一个爬虫类列表
import logging
import time

logging.basicConfig(level=logging.INFO)

def run_spider():
    """通过Scrapy API运行所有爬虫"""
    logging.info("开始执行定时爬虫任务")
    process = CrawlerProcess(get_project_settings())
    for spider_cls in spiders:
        logging.info(f"添加爬虫：{spider_cls.__name__}")
        process.crawl(spider_cls)
    # process.start() 会阻塞直到所有爬虫完成
    process.start()
    logging.info("所有爬虫执行完毕")

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    # 每天凌晨 0:00 执行一次
    scheduler.add_job(run_spider, 'cron', hour=0, minute=0)
    scheduler.start()
    logging.info("调度器已启动，每天0:00执行一次，按 Ctrl+C 退出")
    try:
        # 保持主线程运行，避免空循环消耗CPU
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logging.info("调度器已停止")