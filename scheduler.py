from apscheduler.schedulers.background import BackgroundScheduler
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from ArticleCrawler.spiders import spiders  # 假设 spiders 是一个爬虫类列表
import logging
import time
import os
import json

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

def clean_empty_json_files(directory='./outfile'):
    """
    遍历指定目录及其子目录，清理空的 JSON 文件。
    空文件定义：文件内容为空，或解析后的数据为空（如 [] 或 {}）。
    """
    if not os.path.exists(directory):
        print(f"目录 {directory} 不存在。")
        return

    deleted_count = 0
    
    # os.walk 用于递归遍历所有文件夹
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.json'):
                filepath = os.path.join(root, filename)
                
                try:
                    # 检查文件大小，如果为0字节直接判定为空
                    if os.path.getsize(filepath) == 0:
                        is_empty = True
                    else:
                        # 读取并尝试解析 JSON
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        # 判断解析后的数据是否为空列表、空字典或空字符串
                        is_empty = not data 
                    
                    # 如果判定为空，则执行删除
                    if is_empty:
                        os.remove(filepath)
                        deleted_count += 1
                        print(f"已删除空文件: {filepath}")
                        
                except (json.JSONDecodeError, Exception) as e:
                    # 如果 JSON 格式损坏无法解析，这里选择跳过（您也可以根据需求直接删除损坏的文件）
                    print(f"解析文件 {filepath} 时出错，已跳过: {e}")
                    
    print(f"清理完成！共删除 {deleted_count} 个空 JSON 文件。")

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