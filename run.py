import os

if __name__ == "__main__":
    # 执行爬虫
    spiders = ["gamblinginsider","igamingbusiness","intergameonline","sbcnews","sigma"]
    for cmd in ["scrapy crawl " + i for i in spiders]:
        os.system(cmd)
