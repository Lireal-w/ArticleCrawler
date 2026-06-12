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

# 导入数据库操作模块及工具函数
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import DB, ts_to_datetime

from config import config

load_dotenv() 

PROXY_URL = config.get('proxy', None)
proxies = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None

def get_auth(username, app_password):
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
                headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime},
                data=f, proxies=proxies, timeout=60,
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
    payload = {"title": title, "content": content, "status": status, "comment_status": "closed", "ping_status": "closed"}
    if excerpt: payload["excerpt"] = excerpt
    if publish_date:
        publish_date = str(publish_date).strip()
        if publish_date.isdigit() and len(publish_date) >= 10:
            try:
                dt = datetime.fromtimestamp(int(publish_date[:10]))
                publish_date = dt.strftime('%Y-%m-%dT%H:%M:%S')
            except ValueError: pass
        elif ' ' in publish_date and 'T' not in publish_date:
            publish_date = publish_date.replace(' ', 'T')
        payload["date"] = publish_date
    if featured_media_id: payload["featured_media"] = featured_media_id
    if read_time is not None: payload["meta_input"] = {"read_time": read_time}

    response = requests.post(f"{wp_url}/wp-json/wp/v2/posts", auth=get_auth(username, app_password), json=payload, proxies=proxies, timeout=30)
    if response.status_code == 201:
        return response.json()
    else:
        print(f"✗ 文章发布失败，HTTP {response.status_code}")
        print(response.text[:800])
        return None

def convert_date_string(date_str):
    if not date_str: return ''
    try:
        dt = datetime.strptime(date_str, "%B %d, %Y")
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except Exception:
        return date_str

def process_and_submit(wp_url, username, app_password, data, wp_status="draft"):
    title = data.get('title', '无标题')
    raw_content = data.get('content', '')
    summary = data.get('summary', '')
    read_time = data.get('read_time', 0)
    formatted_time = convert_date_string(data.get('publish_time', ''))
    cover_image_source = data.get('cover_image', '')
    if not raw_content: return None
    tree = html.fromstring(raw_content)
    img_srcs = tree.xpath('//img/@src')
    final_content = raw_content
    
    for src in img_srcs:
        if not isinstance(src, str): continue
        src = str(src).strip()
        if not src: continue
        if src.startswith(('http://', 'https://')):
            _, wp_image_url = upload_image_to_wp(wp_url, username, app_password, src)
            if wp_image_url: final_content = final_content.replace(src, wp_image_url)
        else:
            local_path = "./images" + src
            _, wp_image_url = upload_image_to_wp(wp_url, username, app_password, local_path)
            if wp_image_url: final_content = final_content.replace(src, wp_image_url)

    featured_id = None
    if cover_image_source:
        featured_id, _ = upload_image_to_wp(wp_url, username, app_password, cover_image_source)

    result = publish_post_to_wp(wp_url=wp_url, username=username, app_password=app_password, title=title, content=final_content, excerpt=summary, status=wp_status, publish_date=formatted_time, featured_media_id=featured_id, read_time=read_time)
    return result is not None

def submit_goldmedalhand(db):
    articles_to_publish = db.get_unpublished_articles(30,lance=True)
    success_count = 0
    while success_count < 30:
        for article in articles_to_publish:
            article_url = article.get('url')
            print(f"正在发布文章: {article.get('title')}")
            res = process_and_submit("https://goldmedalhand.com", "admin", "NX1z XQDz nHjF i1OC aBU7 xkpP", article, wp_status="draft")
            if res:
                db.mark_article_published(article_url)
                print(f"发布成功并已标记: {article_url},{res}")
                success_count += 1
            elif res is None:
                if not article["content"]:
                    print(f"发布失败: {article_url}，内容为空")
                    db.mark_article_published(article_url)
            else:
                print(f"发布失败: {article_url}")
        print("==== 处理完毕 ====")
    return True
