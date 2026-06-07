# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class ArticlecrawlerSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # matching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class ArticlecrawlerDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class CurlCffiMiddleware:
    """
    全局使用 curl_cffi 发送所有请求，替代 Scrapy 默认下载器。
    """

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signals.spider_opened)
        return middleware

    def spider_opened(self, spider):
        spider.logger.info("CurlCffiMiddleware enabled for ALL requests")

    async def process_request(self, request, spider):
        # 不再对域名进行判断，所有请求都处理

        # 构建请求头（转换 Scrapy Headers 格式）
        headers = {}
        for k, v in request.headers.items():
            key = k.decode('utf-8') if isinstance(k, bytes) else k
            if isinstance(v, list):
                value = v[0].decode('utf-8') if v else ''
            else:
                value = v.decode('utf-8') if isinstance(v, bytes) else v
            headers[key] = value

        # 从 request.meta 获取自定义参数（可选）
        impersonate = request.meta.get('impersonate', 'chrome120')
        timeout = request.meta.get('timeout', 30)
        method = request.method.upper()
        data = request.body

        spider.logger.debug(f"CurlCffiMiddleware: {method} {request.url}")

        try:
            async with curl_requests.AsyncSession() as session:
                # 根据请求方法选择
                if method == 'GET':
                    response = await session.get(
                        request.url,
                        headers=headers,
                        impersonate=impersonate,
                        timeout=timeout,
                        follow_redirects=True
                    )
                elif method == 'POST':
                    response = await session.post(
                        request.url,
                        headers=headers,
                        data=data,
                        impersonate=impersonate,
                        timeout=timeout,
                        follow_redirects=True
                    )
                else:
                    # 其他方法可自行扩展
                    raise ValueError(f"Unsupported method: {method}")

        except Exception as e:
            spider.logger.error(f"CurlCffiMiddleware request failed: {e}")
            # 因为所有请求都接管了，失败时直接返回错误响应或重新抛出异常
            raise

        # 构造 Scrapy Response
        return HtmlResponse(
            url=response.url,
            status=response.status_code,
            headers=dict(response.headers),
            body=response.content,
            encoding='utf-8',
            request=request
        )