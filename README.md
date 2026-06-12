# ArticleCrawler - 定时文字爬虫

> 一个基于 Scrapy 和 APScheduler 的增量式新闻聚合爬虫，支持自动去重、图片本地化、代理与反反爬，并可通过 FastAPI 接口管理定时任务。

## ✨ 功能特性

- **增量爬取**：基于 `SunSpider` 基类实现 URL 去重，避免重复抓取与数据冗余
- **图片本地化**：通过 `ArticleImagesPipeline` 自动下载正文图片，并将 HTML 中的 URL 替换为本地路径
- **反反爬支持**：集成 `CurlCffiMiddleware`，使用 `curl_cffi` 模拟真实浏览器指纹绕过防护
- **定时调度**：支持独立脚本调度（`scheduler.py`）与 FastAPI 生命周期内调度（`app.py`），并且提供了 Web 界面，可以动态修改任务的执行时间
- **多数据源集成**：内置超过 10 个站点的爬虫模块，涵盖行业新闻、数据分析等多个领域
- **数据输出**：抓取结果自动导出为 JSON 文件，并支持一键发布至 WordPress 站点
- **MySQL 持久化**：支持将采集到的文章数据直接存储到 MySQL 数据库
- **文章伪原创**：通过 `Openai` 模块实现利用大模型进行正文内容的伪原创处理

## 🛠️ 技术栈

- **爬虫框架**：Scrapy, curl_cffi
- **任务调度**：APScheduler
- **Web 服务**：FastAPI, Uvicorn
- **数据处理**：lxml, Pillow (ImagesPipeline)
- **发布对接**：WordPress REST API
- **数据库**：MySQL

## 📁 项目结构

```
ArticleCrawler/
├── ArticleCrawler/
│   ├── spiders/              # 爬虫模块（支持多站点）
│   │   ├── __init__.py       # 爬虫注册（自动导入 all Spiders）
│   │   ├── affpapa.py
│   │   ├── bnldata.py
│   │   ├── envMedia.py
│   │   ├── focusgn.py
│   │   ├── gamblinginsider.py
│   │   ├── igamingbusiness.py
│   │   ├── intergameonline.py
│   │   ├── sbcnews.py
│   │   ├── sigma.py
│   │   └── lance.py
│   ├── utils/
│   │   ├── SunSpider.py      # 增量爬虫基类（URL 去重逻辑）
│   │   └── time.py           # 时间解析辅助函数
│   ├── items.py              # 数据结构定义
│   ├── middlewares.py        # 下载中间件（含 CurlCffiMiddleware）
│   ├── pipelines.py          # 数据管道（JSON 存储、图片下载替换、MySQL 存储）
│   ├── settings.py           # 全局配置（代理、并发、输出路径）
│   └── log_formatter.py      # 日志格式化（静默 Item 输出）
├── outfile/                  # JSON 数据与日志输出目录
├── images/                   # 图片本地存储目录
├── test/                     # 测试与发布脚本
│   ├── igamingbusiness.py    # 数据库提交测试
│   ├── ssubmi_from_db.py     # 从数据库批量提交
│   └── submit.py             # 数据提交测试
├── static/                   # 前端静态文件
│   └── index.html            # 定时任务管理界面
├── app.py                    # FastAPI + APScheduler 集成
├── scheduler.py              # 独立定时调度脚本
└── run.py                    # 爬虫批量启动入口
```

## 🚀 快速开始

### 1. 克隆项目并安装依赖

```bash
git clone https://gitee.com/Lireal-W/article-crawler
cd ArticleCrawler
pip install -r requirements.txt
```

### 2. 配置环境

在 `ArticleCrawler/settings.py` 中修改核心配置：

- **代理设置**：修改 `HTTP_PROXY` 与 `HTTPS_PROXY`（默认 `127.0.0.1:7890`）
- **并发控制**：调整 `CONCURRENT_REQUESTS_PER_DOMAIN` 与 `DOWNLOAD_DELAY`
- **输出路径**：修改 `JSON_OUTPUT_DIR` 与 `IMAGES_STORE`

### 3. 运行爬虫

**方式一：运行指定爬虫**

```bash
scrapy crawl sigma
```

**方式二：批量运行多个爬虫**

```bash
python run.py
```

### 4. 启动定时任务

#### 方式一：独立调度脚本

```bash
python scheduler.py
```

启动后，调度器会按预设的 Cron 规则（默认每天凌晨 0:00 执行）自动运行所有已注册的爬虫。

#### 方式二：FastAPI 集成调度

```bash
python app.py
# 或
uvicorn app:app --host 0.0.0.0 --port 8000
```

启动后，可以通过 Web 界面（访问 `http://localhost:8000/static`）查看和修改定时任务时间。

> **注意**：`app.py` 启动时使用 Lifespan 生命周期管理调度器，并将前端静态页面挂载到 `/static` 路径下。

## ⚙️ 高级配置

### 增量爬虫基类

所有继承 `SunSpider` 的爬虫自动具备增量抓取能力：

- 爬虫启动时，从 `./crawled_articles/<spider_name>.json` 加载已爬取的 URL 记录
- 爬虫关闭时，将新增的 URL 持久化到同一文件
- 通过 `is_seen_url(url)` 判断是否已处理，`mark_url_as_seen(url)` 标记已处理
- 每累积 100 条新记录自动保存一次，防止数据丢失

```python
# 示例：继承 SunSpider 后直接使用去重逻辑
class MySpider(SunSpider):
    def parse(self, response):
        for link in response.css('a::attr(href)').getall():
            if self.is_seen_url(link):
                continue
            self.mark_url_as_seen(link)
            yield scrapy.Request(link, callback=self.parse_article)
```

### 图片下载与替换

`ArticleImagesPipeline` 继承自 Scrapy 的 `ImagesPipeline`：

- 自动下载 `item['image_urls']` 中的所有图片到 `./images` 目录
- 根据原始 URL 的路径结构在本地保持相同的目录层级
- 自动将 `item['content']` HTML 中的原始图片 URL 替换为本地相对路径

```python
# 使用示例：爬虫中提取图片 URL
def parse_article(self, response):
    item['image_urls'] = response.css('img::attr(src)').getall()
    item['content'] = response.css('article').get()
    yield item
```

### WordPress 自动发布

使用 `test/submit.py` 可将抓取的 JSON 数据自动发布至 WordPress 站点：

```bash
cd test
python submit.py
```

发布前需要修改脚本中的 WordPress REST API 地址和认证信息。

### MySQL 数据存储

在 `settings.py` 中启用 `MySQLPipeline`（默认已启用），爬虫会自动将文章数据写入 MySQL 数据库：

```python
ITEM_PIPELINES = {
    "ArticleCrawler.pipelines.ArticleImagesPipeline": 100,
    "ArticleCrawler.pipelines.MySQLPipeline": 200,
    "ArticleCrawler.pipelines.JsonFilePipeline": 300,
}
```

数据库连接配置在 `db.py` 中（项目根目录），支持以下表结构：
- 标题、摘要、正文内容
- 作者名称、作者头像
- 发布时间、URL、阅读时长

## ❓ 常见问题

### 为何部分网站抓取失败？

部分站点具有严格的反爬机制，项目默认启用了 `CurlCffiMiddleware` 模拟真实浏览器指纹。如果仍然失败，可以尝试在 `test/` 目录下运行指纹测试脚本。

### 如何添加新的爬虫？

建议继承 `SunSpider`，实现以下三个核心方法：

```python
from ..utils.SunSpider import SunSpider

class MyNewSpider(SunSpider):
    name = "my_new_spider"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com/category/news/"]

    def parse(self, response):
        """解析列表页：提取文章链接 + 翻页"""
        # 1. 提取文章链接，标记已处理并跟进详情页
        # 2. 调用 get_next_page_url(response) 获取下一页链接
        pass

    def get_next_page_url(self, response):
        """提取下一页链接（支持显式按钮和 URL 构造两种方式）"""
        pass

    def parse_article(self, response):
        """解析详情页：填充 ArticleItem"""
        item = ArticleItem()
        # 提取标题、正文、发布时间、作者等信息
        return item
```

### 如何调整定时任务的执行频率？

- **独立调度脚本（scheduler.py）**：修改 `scheduler.add_job()` 中的 Cron 表达式
- **FastAPI 集成（app.py）**：通过 Web 界面动态修改，或直接修改 `scheduler.add_job()` 的参数

## 📄 许可证

本项目仅供学习交流使用，请遵守目标网站的 `robots.txt` 协议及相关法律法规。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

- 发现 Bug 或有问题需要帮助 → 提交 [Issue](https://github.com/Lireal-w/ArticleCrawler/issues)
- 希望增加新的站点爬虫 → Fork 后添加并提交 PR
- 有任何改进建议 → 欢迎随时沟通
