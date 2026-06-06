
# 📰 Scrapy + APScheduler 定时文章爬虫

一个基于 **Scrapy** 爬虫框架与 **APScheduler** 定时任务库的文章采集系统，支持定时自动抓取文章，并提取标题、摘要、作者信息、时间字段以及预估阅读时间。

## ✨ 功能特性

- 🕷️ **Scrapy 异步爬虫** – 高效稳定，支持并发请求与中间件扩展
- ⏰ **APScheduler 任务调度** – 支持 Cron 表达式、固定间隔、单次执行等灵活配置
- 📦 **结构化数据字段** – 包含标题、摘要、网址、作者姓名/头像、发布时间、修改时间、预估阅读时间
- 🔁 **独立调度脚本 / 项目内集成** 两种模式可选
- 🧩 **易于扩展** – 可无缝对接数据库（MySQL、MongoDB）、日志告警、代理池等

## 🛠️ 技术栈

| 组件            | 技术选型                         |
| --------------- | -------------------------------- |
| 爬虫框架        | Scrapy 2.11+                     |
| 定时调度        | APScheduler 3.10+                |
| 数据存储（示例）| JSON / CSV / 可扩展至 MySQL/ES   |
| 语言            | Python 3.9+                      |

## 📁 项目结构

```
article_crawler/
├── article_crawler/           # Scrapy 项目主目录
│   ├── spiders/               # 爬虫代码目录
│   │   └── example_spider.py  # 示例爬虫
│   ├── items.py               # 定义 Item 字段（见下方）
│   ├── middlewares.py
│   ├── pipelines.py
│   └── settings.py
├── run_scheduler.py           # 独立调度脚本（推荐）
├── requirements.txt           # 依赖清单
└── README.md
```

## 🚀 快速开始

### 1. 克隆项目并安装依赖

```bash
git clone https://github.com/yourname/article-crawler.git
cd article-crawler
pip install -r requirements.txt
```

`requirements.txt` 示例内容：

```
scrapy>=2.11.0
apscheduler>=3.10.0
```

### 2. 配置定时任务

本项目提供两种集成方式，推荐使用 **独立调度脚本**。

#### ✅ 方式一：独立调度脚本（简单可靠）

在项目根目录创建 `run_scheduler.py`：

```python
import subprocess
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

logging.basicConfig(level=logging.INFO)

def crawl_job():
    logging.info("启动爬虫任务...")
    result = subprocess.run(["scrapy", "crawl", "example"], capture_output=True, text=True)
    if result.returncode == 0:
        logging.info("爬虫执行成功")
    else:
        logging.error(f"执行失败: {result.stderr}")

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    # 每天 8:00 执行
    scheduler.add_job(crawl_job, "cron", hour=8, minute=0)
    # 或每 30 分钟执行一次
    # scheduler.add_job(crawl_job, "interval", minutes=30)
    scheduler.start()
```

运行：

```bash
python run_scheduler.py
```

#### ✅ 方式二：项目内集成（便于扩展）

直接在 Scrapy 项目中启动后台调度器，参见 `article_crawler/scheduler.py` 示例。

### 5. 保存数据

Scrapy 支持多种输出格式，例如：

```bash
# 输出为 JSON 文件
scrapy crawl example -o articles.json

# 输出为 CSV
scrapy crawl example -o articles.csv
```

如需持久化到数据库，可编写 Pipeline 并开启 `ITEM_PIPELINES`。

## ⚙️ 高级配置

### 定时触发器

| 触发器      | 示例                                      | 说明               |
| ----------- | ----------------------------------------- | ------------------ |
| `cron`      | `hour=8, minute=30`                       | 每天 8:30 执行     |
| `cron`      | `day_of_week='mon-fri', hour=9`           | 工作日 9:00 执行   |
| `interval`  | `minutes=15`                              | 每隔 15 分钟执行   |
| `date`      | `run_date='2025-01-01 00:00:00'`          | 单次执行           |

### 生成预计阅读时间

建议在爬虫中动态计算：

```python
import random
import math

text_content = "".join(article.css("div.content *::text").getall())
word_count = len(text_content)
read_time = max(1, math.ceil(word_count / 600))  # 假设 600字/分钟
item["read_time"] = str(read_time)
# 或随机生成
item["read_time"] = str(random.randint(3, 10))
```

## 🔧 常见问题

**Q：如何避免爬虫任务重叠？**  
A：可在调度函数开头添加锁文件或检查进程是否已在运行。

**Q：调度器关闭后任务会丢失吗？**  
A：APScheduler 默认内存存储，重启会丢失。如需持久化可使用 `SQLAlchemyJobStore`。

**Q：Scrapy 和 APScheduler 日志冲突？**  
A：统一使用 Python `logging` 配置即可，两者均兼容。

## 📄 开源许可

[MIT License](LICENSE)

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request。如有定制化需求，可参考 [Scrapy 官方文档](https://docs.scrapy.org/) 与 [APScheduler 文档](https://apscheduler.readthedocs.io/)。
