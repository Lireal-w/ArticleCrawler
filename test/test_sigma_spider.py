from curl_cffi import requests

def test_sigma_spider():
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'if-modified-since': '',
        'if-none-match': '',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Chromium";v="148", "Microsoft Edge";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-full-version': '"148.0.3967.96"',
        'sec-ch-ua-full-version-list': '"Chromium";v="148.0.7778.217", "Microsoft Edge";v="148.0.3967.96", "Not/A)Brand";v="99.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"19.0.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
    }

    # 使用 curl_cffi 发送请求，impersonate 模拟 Edge 浏览器（版本可选 edge99/edge101/edge110）
    # 这里选择 edge101，因为 curl_cffi 没有 Edge 148 的精确指纹，但 edge101 足以绕过大部分 Cloudflare
    response = requests.get(
        'https://sigma.world/latest-news/online/',
        headers=headers,
        impersonate="chrome120",
        timeout=30
    )

    print(response.status_code)
    print(response.text[:500])  # 打印前500字符验证是否正常


if __name__ == "__main__":
    # test_sigma_spider()
    for imp in ['edge101', 'chrome120', 'safari15_5', 'firefox102']:
        try:
            resp = requests.get('https://sigma.world/latest-news/online/', impersonate=imp, timeout=30)
            print(f"{imp}: {resp.status_code}")
            if resp.status_code == 200:
                print("Success!")
                break
        except:
            print(f"{imp} error")