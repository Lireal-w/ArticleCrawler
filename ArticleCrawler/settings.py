# Scrapy settings for ArticleCrawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "ArticleCrawler"

SPIDER_MODULES = ["ArticleCrawler.spiders"]
NEWSPIDER_MODULE = "ArticleCrawler.spiders"

ADDONS = {}

TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "ArticleCrawler (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concurrency and throttling settings
#CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "ArticleCrawler.middlewares.ArticlecrawlerSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# ArticleCrawler/settings.py
DOWNLOADER_MIDDLEWARES = {
    'ArticleCrawler.middlewares.CurlCffiMiddleware': 543,
    'scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware': None,  # 新增此行
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scrapy_ua_rotator.middleware.RandomUserAgentMiddleware': None,
    'scrapy_ua_rotator.middleware.RetryUserAgentMiddleware': None,
}


# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# USERAGENT_PROVIDERS = [
#     'scrapy_ua_rotator.providers.FakeUserAgentProvider',
#     'scrapy_ua_rotator.providers.FakerProvider',
#     'scrapy_ua_rotator.providers.FixedUserAgentProvider',
# ]


# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
#    "ArticleCrawler.pipelines.ArticlecrawlerPipeline": 300,
    "ArticleCrawler.pipelines.ArticleImagesPipeline": 100,
    "ArticleCrawler.pipelines.JsonFilePipeline": 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
JSON_OUTPUT_DIR = './outfile'
IMAGES_STORE = './images'

DOWNLOAD_HANDLERS = {
    "http": None,
    "https": None,
}