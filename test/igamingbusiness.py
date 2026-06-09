import requests

headers = {
    'accept': '*/*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'authorization': 'Bearer search-2t8y4cc8ej9yh9cufhujes9v',
    'content-type': 'application/json',
    'origin': 'https://igamingbusiness.com',
    'priority': 'u=1, i',
    'referer': 'https://igamingbusiness.com/',
    'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-storage-access': 'active',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'x-elastic-client-meta': 'ent=8.5.1-legacy,js=browser,t=8.5.1-legacy,ft=universal',
    'x-swiftype-client': 'elastic-app-search-javascript',
    'x-swiftype-client-version': '8.5.1',
}

json_data = {
    'query': '',
    'page': {
        'size': 12,
        'current': 2,
    },
    'filters': {
        'all': [
            {
                'blog_id': '1',
            },
            {
                'object_type': [
                    'post',
                    'brand_view',
                    'company_news',
                    'content_os',
                ],
            },
            {
                'is_visible': 'true',
            },
            {
                'is_private': 'false',
            },
            {
                'category': [
                    'Sports betting',
                ],
            },
        ],
    },
    'facets': {
        'category': {
            'type': 'value',
            'size': 100,
        },
        'content_type': {
            'type': 'value',
            'size': 100,
        },
        'region': {
            'type': 'value',
            'size': 100,
        },
        'post_tag': {
            'type': 'value',
            'size': 100,
        },
    },
    'sort': {
        'timestamp': 'desc',
    },
}
proxy_url = 'http://127.0.0.1:7890'
proxies = {'http': proxy_url, 'https': proxy_url}
response = requests.post(
    'https://clus1-dcs1.synotiosearch.net/api/as/v1/engines/igamingbusiness-com/search.json',
    headers=headers,
    json=json_data,
    proxies=proxies
)
print(response.text)