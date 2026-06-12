from apscheduler.schedulers.background import BackgroundScheduler
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from ArticleCrawler.spiders import spiders  # 假设 spiders 是一个爬虫类列表
import logging
import time
import os
import json
from db import DB
from utils.wordpress import process_and_submit

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

def submit_active_to_site():
    db = DB()
    db.connect()
    
    try:
        # ================= 1. 单独处理 goldmedalhand (39篇) =================
        goldmedalhand_config = {
            "url": "https://goldmedalhand.com", 
            "username": "admin", 
            "app_password": "NX1z XQDz nHjF i1OC aBU7 xkpP"
        }
        gold_limit = 39
        gold_success = 0
        
        print(f"\n==== 开始处理站点: {goldmedalhand_config['url']} (目标: {gold_limit}篇) ====")
        articles = db.get_unpublished_articles(limit=gold_limit, lance=True)
        
        for article in articles:
            if gold_success >= gold_limit:
                break
            article_url = article.get('url')
            print(f"正在发布文章: {article.get('title')}")
            
            res = process_and_submit(
                goldmedalhand_config["url"], 
                goldmedalhand_config["username"], 
                goldmedalhand_config["app_password"], 
                article, 
                wp_status="draft"
            )
            
            if res:
                db.mark_article_published(article_url)
                print(f"✅ 发布成功并已标记: {article_url}")
                gold_success += 1
            elif res is None and not article.get("content"):
                print(f"❌ 发布失败: {article_url}，内容为空")
                db.mark_article_published(article_url)
            else:
                print(f"❌ 发布失败: {article_url}")
                
        print(f"==== 站点 {goldmedalhand_config['url']} 处理完毕，成功发布 {gold_success} 篇 ====\n")

        # ================= 2. 处理数据库中的其他站点 (每个20篇) =================
        sites = db.get_all_sites()
        site_limit = 20
        
        for site in sites:
            wp_url = site["url"].rstrip('/')
            username = site["username"]
            app_password = site["app_password"]
            
            # 跳过已单独处理的 goldmedalhand
            if wp_url == goldmedalhand_config["url"].rstrip('/'):
                continue
                
            print(f"\n==== 开始处理站点: {wp_url} (目标: {site_limit}篇) ====")
            articles_to_publish = db.get_unpublished_articles(limit=site_limit)
            success_count = 0
            
            while success_count < site_limit:
                for article in articles_to_publish:
                    if success_count >= site_limit:
                        break
                        
                    article_url = article.get('url')
                    print(f"[{wp_url}] 正在发布文章: {article.get('title')}")
                    
                    # 处理 JSON 字段反序列化
                    if isinstance(article.get('image_urls'), str):
                        article['image_urls'] = json.loads(article['image_urls'])
                    if isinstance(article.get('images'), str):
                        article['images'] = json.loads(article['images'])
                        
                    res = process_and_submit(wp_url, username, app_password, article, wp_status="draft")
                    
                    if res:
                        success_count += 1
                        db.mark_article_published(article_url)
                        print(f"✅ 发布成功并已标记: {article_url}")
                    elif res is None and not article.get("content"):
                        print(f"❌ 发布失败: {article_url}，内容为空")
                        db.mark_article_published(article_url)
                    else:
                        print(f"❌ 发布失败: {article_url}")
                        
                # 如果一轮没凑够，再拉取剩余所需篇数
                if success_count < site_limit:
                    articles_to_publish = db.get_unpublished_articles(limit=site_limit - success_count)
                    if not articles_to_publish:
                        print("数据库中无更多未发布文章，跳出当前站点循环。")
                        break
                        
            print(f"==== 站点 {wp_url} 处理完毕，成功发布 {success_count} 篇 ====")
            
    except Exception as e:
        print(f"执行异常: {e}")
    finally:
        db.close()


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