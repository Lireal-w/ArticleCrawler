import json
import requests
from datetime import datetime

def load_data():
    with open('./outfile/bnldata.json', 'r', encoding='utf-8') as f:
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

def submit_data(data):
    # 处理时间字段
    publish_time = data.get('publish_time', '')
    formatted_time = convert_time(publish_time)

    # 构建请求参数
    payload = {
        'title': data.get('title', ''),
        'summary': data.get('summary', ''),
        'url': data.get('url', ''),
        'content': data.get('content', ''),
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
    for item in data_list:
        submit_data(item)
        break   # 仅测试第一条时取消注释