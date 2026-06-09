根据提供的代码结构和原始README信息，我来生成一个优化后的README文档：

# 📰 ArticleCrawler

基于 Scrapy 与 APScheduler 的增量式新闻聚合爬虫，支持自动去重、图片本地化、代理与反反爬，并可通过 FastAPI 接口管理定时任务。

## ✨ 功能特性

- **增量爬取**：基于 `SunSpider` 基类实现 URL 去重，避免重复抓取与数据冗余
- **多源适配**：内置 9 个博彩/游戏行业新闻源爬虫（sigma, sbcnews, bnldata, igamingbusiness, gamblinginsider, intergameonline, focusgn, envMedia, affpapa）
- **图片本地化**：通过 `ArticleImagesPipeline` 自动下载正文图片，并将 HTML 中的 URL 替换为本地路径
- **反反爬支持**：集成 `CurlCffiMiddleware`，使用 `curl_cffi` 模拟真实浏览器指纹绕过防护
- **定时调度**：支持独立脚本调度（`scheduler.py`）与 FastAPI 生命周期内调度（`app.py`）
- **数据输出**：抓取结果自动导出为 JSON 文件，并支持一键发布至 WordPress 站点

## 🛠️ 技术栈

- **爬虫框架**：Scrapy, curl_cffi
- **任务调度**：APScheduler
- **Web 服务**：FastAPI, Uvicorn
- **数据处理**：lxml, Pillow (ImagesPipeline)
- **发布对接**：WordPress REST API

## 📁 项目结构

```
ArticleCrawler/
├── ArticleCrawler/
│   ├── spiders/              # 爬虫模块
│   │   ├── sigma.py         # 基础爬虫示例
│   │   ├── bnldata.py       # 支持AJAX分页的爬虫
│   │   ├── igamingbusiness.py # 基于API接口的爬虫
│   │   ├── focusgn.py       # 继承scrapy.Spider的基础爬虫
│   │   └── ...              # 其他均继承自SunSpider
│   ├── utils/
│   │   └── SunSpider.py     # 增量爬虫基类（URL去重逻辑）
│   ├── items.py             # 数据结构定义
│   ├── middlewares.py       # 下载中间件（含CurlCffiMiddleware）
│   ├── pipelines.py          # 数据管道（JSON存储与图片下载替换）
│   ├── settings.py          # 全局配置（代理、并发、输出路径）
│   └── log_formatter.py     # 日志格式化（静默Item输出）
├── outfile/                 # JSON数据与日志输出目录
├── images/                  # 图片本地存储目录
├── test/                    # 测试与发布脚本
│   ├── test_sigma_spider.py # 指纹模拟测试
│   ├── submit.py            # 数据提交测试
│   └── wplist_publish.py    # WordPress批量发布
├── app.py                   # FastAPI + APScheduler 集成
├── scheduler.py             # 独立定时调度脚本
└── run.py                   # 爬虫批量启动入口
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

#### 方式二：FastAPI 集成调度
```bash
python app.py
# 或
uvicorn app:app --host 0.0.0.0 --port 8000
```

## ⚙️ 高级配置

### 增量爬虫基类

所有继承 `SunSpider` 的爬虫自动具备增量抓取能力。基类在爬虫启动时从本地加载已爬取 URL 记录，关闭时持久化，通过 `is_seen_url` 过滤重复请求。

### 图片下载与替换

`ArticleImagesPipeline` 继承自 Scrapy 的 `ImagesPipeline`。它不仅将图片下载至 `./images`，还会自动将 `item['content']` HTML 中的原始图片 URL 替换为本地相对路径。

### WordPress 自动发布

使用 `test/wplist_publish.py` 可将抓取的 JSON 数据自动发布至多个 WordPress 站点。

## 🔧 常见问题

- **为何部分网站抓取失败？**  
  部分站点具有严格的反爬机制，项目默认启用了 `CurlCffiMiddleware` 模拟真实浏览器指纹。如仍失败，可尝试在 `test/` 目录下运行指纹测试脚本。

- **如何添加新的爬虫？**  
  建议继承 `SunSpider`，实现 `parse`（列表页）、`parse_article`（详情页）及 `get_next_page_url`（分页逻辑）即可。

## 📄 许可证

本项目仅供学习交流使用，请遵守目标网站的 robots.txt 协议及相关法律法规。