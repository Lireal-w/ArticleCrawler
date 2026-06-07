import json
import requests
from datetime import datetime
from lxml import html,etree 

def load_data():
    with open('./outfile/bnldata1.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def convert_time(iso_time):
    """将 ISO 8601 时间字符串转换为 Y-m-d H:i:s 格式"""
    if not iso_time:
        return ''
    try:
        # 解析带时区的 ISO 格式（如 2026-06-05T19:25:55+00:00）
        dt = datetime.fromisoformat(iso_time)
        # 转换为本地时间（如果希望保留 UTC，可去掉下面这行）
        # dt = dt.astimezone()  # 转换为系统本地时区
        # 返回无时区的字符串
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        # 如果解析失败，返回原字符串（或空）
        return iso_time

def upload(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        files = {
            "file": (file_path.split("/")[-1], f, "image/jpeg")
        }
        proxy_url = 'http://127.0.0.1:7890'

        proxies = {'http': proxy_url, 'https': proxy_url}

        response = requests.post(
            'https://wk.itheihai.com/api/common/upload',
        proxies=proxies, files=files).json()
        return response.get("data").get("fullurl")

def submit_data(data):
    # 处理时间字段
    publish_time = data.get('publish_time', '')
    formatted_time = convert_time(publish_time)
    # 匹配content中的图片链接
    tree = html.fromstring(data.get('content', ''))
    # 执行过滤
    for fig in tree.xpath('.//figure[contains(@class, "wp-caption")]'):
        parent = fig.getparent()
        if parent is not None:
            parent.remove(fig)
            
    for ad in tree.xpath('.//*[contains(@class, "sync-adwrapper")]'):
        parent = ad.getparent()
        if parent is not None:
            parent.remove(ad)
            
    for div in tree.xpath('.//div[contains(@class, "single-header__info")]'):
        parent = div.getparent()
        if parent is not None:
            parent.remove(div)
            
    for script in tree.xpath('.//script'):
        parent = script.getparent()
        if parent is not None:
            parent.remove(script)
    data['content'] = etree.tostring(tree, encoding='unicode')
    # 提取所有 img 标签的 src 属性
    img_srcs = tree.xpath('//img/@src')

    if img_srcs:
        for src in img_srcs:
            # 上传文件
            url = upload("./images" + src)
            # 替换 content 中的图片链接
            data['content'] = data['content'].replace(src, url)
    # # 获取处理后的content
    # content = data.get('content', '')
    # # 保存为html
    # with open('./outfile/content.html', 'w', encoding='utf-8') as f:
    #     f.write(content)
    # 构建请求参数
    payload = {
        'title': data.get('title', ''),
        'summary': data.get('summary', ''),
        'url': data.get('url', ''),
        'content': data['content'],
        'author_name': data.get('author_name', ''),
        'author_avatar': data.get('author_avatar', ''),
        'publishtime': formatted_time,      # 使用转换后的时间
        'read_time': data.get('read_time', 0),
    }
    # 移除值为空字符串的字段（可选）
    payload = {k: v for k, v in payload.items() if v != ''}

    # 代理设置
    proxy_url = 'http://127.0.0.1:7890'
    proxies = {'http': proxy_url, 'https': proxy_url}

    try:
        response = requests.post(
            'https://wk.itheihai.com/api/article/submit',
            json=payload,
            proxies=proxies,
            timeout=30
        )
        print(f"提交成功：{data.get('title')} -> {response.status_code}")
        print(f"响应内容：{response.text}")
    except Exception as e:
        print(f"提交失败：{data.get('title')}，错误：{e}")

if __name__ == '__main__':
    data_list = load_data()
    guo = False
    for item in data_list:
        if item.get("title") == "Nova York inaugura primeiro cassino completo e movimenta US$ 17,6 bi em investimentos":
            guo = True
        else: 
            if guo:submit_data(item)
        # break   # 仅测试第一条时取消注释