import json
import requests
import mimetypes
import os
import tempfile
from datetime import datetime
from lxml import html
from dotenv import load_dotenv
from typing import Optional
from requests.auth import HTTPBasicAuth

load_dotenv() 

PROXY_URL = 'http://127.0.0.1:7890'
proxies = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None

# 多站点配置列表
SITES = [
    # {"url": "https://wealthtide.vip", "username": "admin", "app_password": "jly9 DEzT qi1G Uq4u xArU XDAF"},
    # {"url": "https://lucksystar.vip", "username": "admin", "app_password": "Q7aF qJxJ bw9x pJ3o cr2i CqrO"},
    # {"url": "https://bettingtableshadow.com", "username": "admin", "app_password": "ffF7 HqDV UsZO 7KCY 5KSF iixx"},
    # {"url": "https://betgodwind.com", "username": "admin", "app_password": "yvmA JAu6 KX2Q 4tnr DrGr SJwz"},
    # {"url": "https://colorballfly.com", "username": "admin", "app_password": "eF6o UdXE w4Ed lrqz D3n5 nb3D"},
    # {"url": "https://cardgamedream.com", "username": "admin", "app_password": "0itx i5io nIy9 eO3c vQhj xXw4"},
    {"url": "https://goldmedalhand.com", "username": "admin", "app_password": "NX1z XQDz nHjF i1OC aBU7 xkpP"},
    # {"url": "https://gamblerheart.com", "username": "admin", "app_password": "pmmF 0Tgb I5TO rags kIIf AWfS"},
    # {"url": "https://winlosehand.com", "username": "admin", "app_password": "jLxn 7LFw gFAY VWVE j745 3aMj"},
    # {"url": "https://winhappy.vip", "username": "admin", "app_password": "dzpm vjZp HlGN ReHb 5JH8 BtYL"},
]

def get_auth(username, app_password):
    """返回 Basic 认证元组"""
    return (username, app_password.replace(" ", ""))

def download_image(url):
    try:
        resp = requests.get(url, proxies=proxies, timeout=30, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', '')
        ext = mimetypes.guess_extension(content_type) or '.jpg'
        fd, tmp_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return tmp_path
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return None

def upload_image_to_wp(wp_url, username, app_password, image_source):
    tmp_file = None
    local_path = image_source

    if image_source.startswith(('http://', 'https://')):
        tmp_file = download_image(image_source)
        if not tmp_file:
            return None, None
        local_path = tmp_file

    if not os.path.exists(local_path):
        if tmp_file:
            os.unlink(tmp_file)
        return None, None

    filename = os.path.basename(local_path)
    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"

    try:
        with open(local_path, "rb") as f:
            response = requests.post(
                f"{wp_url}/wp-json/wp/v2/media",
                auth=get_auth(username, app_password),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": mime,
                },
                data=f,
                proxies=proxies,
                timeout=60,
            )
    finally:
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)

    if response.status_code == 201:
        media_data = response.json()
        return media_data.get("id"), media_data.get("source_url")
    else:
        print(f"✗ 图片上传失败 [{image_source}]，HTTP {response.json()}")
        return None, None

def publish_post_to_wp(wp_url, username, app_password, title, content, excerpt="", status="draft", publish_date=None, featured_media_id=None, read_time=None):
    payload = {
        "title": title,
        "content": content,
        "status": status,
        "comment_status": "closed",
        "ping_status": "closed",
    }
    if excerpt:
        payload["excerpt"] = excerpt
    if publish_date:
        # 🚀 修复：强制转为字符串，并判断是否为纯数字时间戳
        publish_date = str(publish_date).strip()
        if publish_date.isdigit() and len(publish_date) >= 10:
            # 如果是秒级时间戳，转为 WordPress 要求的 ISO 8601 格式
            try:
                dt = datetime.fromtimestamp(int(publish_date[:10]))
                publish_date = dt.strftime('%Y-%m-%dT%H:%M:%S')
            except ValueError:
                pass
        elif ' ' in publish_date and 'T' not in publish_date:
            publish_date = publish_date.replace(' ', 'T')
        payload["date"] = publish_date
    if featured_media_id:
        payload["featured_media"] = featured_media_id
    if read_time is not None:
        payload["meta_input"] = {"read_time": read_time}

    response = requests.post(
        f"{wp_url}/wp-json/wp/v2/posts",
        auth=get_auth(username, app_password),
        json=payload,
        proxies=proxies,
        timeout=30,
    )

    if response.status_code == 201:
        return response.json()
    else:
        print(f"✗ 文章发布失败，HTTP {response.status_code}")
        print(response.text[:800])
        return None
def convert_date_string(date_str):
    if not date_str:
        return ''
    try:
        # 解析 "June 3, 2026"
        dt = datetime.strptime(date_str, "%B %d, %Y")
        # 默认时间为 00:00:00
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except Exception:
        # 如果解析失败，返回原字符串（或尝试其他常见格式）
        return date_str
    
def process_and_submit(wp_url, username, app_password, data, wp_status="draft"):
    title = data.get('title', '无标题')
    raw_content = data.get('content', '')
    summary = data.get('summary', '')
    read_time = data.get('read_time', 0)
    formatted_time = convert_date_string(data.get('publish_time', ''))
    cover_image_source = data.get('cover_image', '')

    # 此处为了批量提交效率，跳过内容图片的遍历替换，如需处理可取消注释
    # 1. 清洗 HTML
    tree = html.fromstring(raw_content)

    # 2. 处理内容中的图片（支持本地路径和远程 URL）
        # 2. 处理内容中的图片（支持本地路径和远程 URL）
    img_srcs = tree.xpath('//img/@src')
    final_content = raw_content  # 后续替换
    for src in img_srcs:
        # 判断 src 是 URL 还是本地路径（以 ./images 开头或 / 开头等）
        if not isinstance(src, str):
            continue
        src = str(src).strip()
        if not src:
            continue
        if src.startswith(('http://', 'https://')):
            # print(f"处理远程图片：{src}")
            _, wp_image_url = upload_image_to_wp(wp_url, username, app_password, src)
            if wp_image_url:
                final_content = final_content.replace(src, wp_image_url)
            else:
                print(f"远程图片上传失败，保留原链接：{src}")
        else:
            # 本地路径：与旧脚本一致，拼接 ./images
            local_path = "./images" + src
            # print(f"处理本地图片：{local_path}")
            _, wp_image_url = upload_image_to_wp(wp_url, username, app_password, local_path)
            if wp_image_url:
                final_content = final_content.replace(src, wp_image_url)
            else:
                print(f"本地图片上传失败，保留原链接：{src}")

    # 3. 处理封面图
    featured_id = None
    if cover_image_source:
        # print(f"处理封面图：{cover_image_source}")
        featured_id, _ = upload_image_to_wp(wp_url, username, app_password, cover_image_source)

    result = publish_post_to_wp(
        wp_url=wp_url,
        username=username,
        app_password=app_password,
        title=title,
        content=final_content,
        excerpt=summary,
        status=wp_status,
        publish_date=formatted_time,
        featured_media_id=featured_id,
        read_time=read_time
    )

    return result is not None
def load_data():
    with open('./outfile/20260610/lance_1781090633.json', 'r', encoding='utf-8') as f:
        return json.load(f)
if __name__ == '__main__':
    # 生成 20 篇文章数据
    articles_to_publish = load_data()
    current = 0
    for site in SITES:
        wp_url = site["url"].rstrip('/')
        username = site["username"]
        app_password = site["app_password"]
        
        print(f"\n==== 开始处理站点: {wp_url} ====")
        success_count = 0
        
        # for index, article in enumerate(articles_to_publish, 1):
        #     print(f"[{wp_url}] 正在发布第 {index}/20 篇文章...")
        #     if process_and_submit(wp_url, username, app_password, article, wp_status="draft"):
        #         success_count += 1
        # try:
        for i in range(30):
            if process_and_submit(wp_url, username, app_password, articles_to_publish[current], wp_status="draft"):
                success_count += 1
            current += 1
        # except Exception as e:
        #     print(f"发生错误: {e}")
            
                
        print(f"==== 站点 {wp_url} 处理完毕，成功发布 {success_count}/20 篇 ====")
