import json
import requests
import mimetypes
import os
import tempfile
from datetime import datetime
from lxml import html, etree
# 导入并加载 .env 配置
from dotenv import load_dotenv
from typing import Optional
from requests.auth import HTTPBasicAuth
load_dotenv() 

# 从环境变量读取配置
WP_URL = os.getenv("WP_URL", "").rstrip('/')  # 移除末尾斜杠，确保与原注释逻辑一致
USERNAME = os.getenv("USERNAME", "")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
# 基础校验：防止未配置时程序继续运行引发难以排查的错误
if not WP_URL or not USERNAME or not APP_PASSWORD:
    raise ValueError("缺少必要的环境变量配置，请检查 .env 文件是否正确设置！")

PROXY_URL = 'http://127.0.0.1:7890'              # 代理（不需要可设为 None）
proxies = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None


def get_or_create_user_by_username(username: str,
                                   email: Optional[str] = None,
                                   password: Optional[str] = None,
                                   role: str = 'subscriber') -> Optional[int]:
    """
    通过用户名查询或创建 WordPress 用户（使用全局配置）
    :param username: 用户名，作为 slug 进行匹配
    :param email: 创建时使用的邮箱（若不提供且需创建用户，将拼接默认邮箱）
    :param password: 创建时使用的密码（若不提供且需创建用户，将生成随机密码）
    :param role: 创建用户时赋予的角色，默认为 'subscriber'
    :return: 用户 ID（成功）或 None（失败）
    """
    # 直接使用全局变量
    auth = HTTPBasicAuth(USERNAME, APP_PASSWORD.replace(" ", ""))
    users_endpoint = f"{WP_URL}/wp-json/wp/v2/users"

    # 1. 查询用户是否存在
    list_params = {
        'search': username,
        'context': 'edit',
        'per_page': 100
    }
    try:
        resp = requests.get(users_endpoint, auth=auth, params=list_params, timeout=10)
        if resp.status_code == 200:
            users = resp.json()
            for user in users:
                if user.get('slug') == username:
                    return user.get('id')
    except Exception as e:
        print(f"查询用户失败: {e}")

    # 2. 用户不存在，创建用户
    if not email:
        email = f"{username}@gmail.com"
    if not password:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(12))

    create_payload = {
        'username': username,
        'email': email,
        'password': password,
        'roles': [role]
    }
    try:
        resp = requests.post(users_endpoint, auth=auth, json=create_payload, timeout=15)
        if resp.status_code == 201:
            new_user = resp.json()
            return new_user.get('id')
        else:
            print(f"创建用户失败，HTTP {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"创建用户请求异常: {e}")
        return None


def get_auth():
    """返回 Basic 认证元组"""
    return (USERNAME, APP_PASSWORD.replace(" ", ""))

def download_image(url):
    """
    下载远程图片到临时文件，返回临时文件路径
    """
    try:
        resp = requests.get(url, proxies=proxies, timeout=30, stream=True)
        resp.raise_for_status()
        # 获取文件后缀（从 Content-Type 或 URL 中猜测）
        content_type = resp.headers.get('Content-Type', '')
        ext = mimetypes.guess_extension(content_type) or '.jpg'
        # 创建临时文件
        fd, tmp_path = tempfile.mkstemp(suffix=ext)
        os.close(fd)
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return tmp_path
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return None

def upload_image_to_wp(image_source):
    """
    上传图片到 WordPress 媒体库
    image_source: 可以是本地文件路径或远程 URL
    返回 (media_id, media_url)，失败返回 (None, None)
    """
    tmp_file = None
    local_path = image_source

    # 判断是否为 URL
    if image_source.startswith(('http://', 'https://')):
        print(f"检测到远程图片，正在下载：{image_source}")
        tmp_file = download_image(image_source)
        if not tmp_file:
            return None, None
        local_path = tmp_file

    if not os.path.exists(local_path):
        print(f"图片不存在：{local_path}")
        if tmp_file:
            os.unlink(tmp_file)
        return None, None

    filename = os.path.basename(local_path)
    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"

    try:
        with open(local_path, "rb") as f:
            response = requests.post(
                f"{WP_URL}/wp-json/wp/v2/media",
                auth=get_auth(),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": mime,
                },
                data=f,
                proxies=proxies,
                timeout=60,
            )
    finally:
        # 如果是临时文件，上传后删除
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)

    if response.status_code == 201:
        media_data = response.json()
        media_id = media_data.get("id")
        media_url = media_data.get("source_url")
        print(f"✓ 图片上传成功：{image_source} -> ID {media_id}")
        return media_id, media_url
    else:
        print(f"✗ 图片上传失败 [{image_source}]，HTTP {response.status_code}")
        print(response.text[:500])
        return None, None

def publish_post_to_wp(title, content, excerpt="", status="draft", publish_date=None,
                       featured_media_id=None, read_time=None,author=None):
    """
    通过 WordPress REST API 发布文章
    """
    payload = {
        "title": title,
        "content": content,
        "status": status,
        "comment_status": "closed",
        "ping_status": "closed",
    }
    if author:
        payload["author"] = author
    if excerpt:
        payload["excerpt"] = excerpt
    if publish_date:
        # 确保格式为 Y-m-d\TH:i:s
        if ' ' in publish_date and 'T' not in publish_date:
            publish_date = publish_date.replace(' ', 'T')
        payload["date"] = publish_date
    if featured_media_id:
        payload["featured_media"] = featured_media_id
    if read_time is not None:
        payload["meta_input"] = {"read_time": read_time}

    response = requests.post(
        f"{WP_URL}/wp-json/wp/v2/posts",
        auth=get_auth(),
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

# ---------- 数据处理 ----------
def load_data():
    with open('./outfile/sbcnews.json', 'r', encoding='utf-8') as f:
        return json.load(f)

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

def process_and_submit(data, wp_status="draft"):
    """
    处理单条数据
    cover_image_source: 可以是本地路径或远程 URL
    """
    title = data.get('title', '无标题')
    raw_content = data.get('content', '')
    summary = data.get('summary', '')
    read_time = data.get('read_time', 0)
    publish_time_str = data.get('publish_time', '')
    formatted_time = convert_date_string(publish_time_str)
    cover_image_source = data.get('cover_image', '')
    # 1. 清洗 HTML
    tree = html.fromstring(raw_content)

    # 2. 处理内容中的图片（支持本地路径和远程 URL）
    img_srcs = tree.xpath('//img/@src')
    final_content = raw_content  # 后续替换
    for src in img_srcs:
        # 判断 src 是 URL 还是本地路径（以 ./images 开头或 / 开头等）
        if src.startswith(('http://', 'https://')):
            print(f"处理远程图片：{src}")
            _, wp_image_url = upload_image_to_wp(src)
            if wp_image_url:
                final_content = final_content.replace(src, wp_image_url)
            else:
                print(f"远程图片上传失败，保留原链接：{src}")
        else:
            # 本地路径：与旧脚本一致，拼接 ./images
            local_path = "./images" + src
            print(f"处理本地图片：{local_path}")
            _, wp_image_url = upload_image_to_wp(local_path)
            if wp_image_url:
                final_content = final_content.replace(src, wp_image_url)
            else:
                print(f"本地图片上传失败，保留原链接：{src}")

    # 3. 处理封面图
    featured_id = None
    if cover_image_source:
        print(f"处理封面图：{cover_image_source}")
        featured_id, _ = upload_image_to_wp(cover_image_source)

    # 4. 发布到 WordPress
    result = publish_post_to_wp(
        title=title,
        content=final_content,
        excerpt=summary,
        status=wp_status,
        publish_date=formatted_time,
        featured_media_id=featured_id,
        read_time=read_time,
        author= get_or_create_user_by_username(username=data.get('author_name', ''),role='author')
    )

    if result:
        print(f"✓ 文章发布成功：{title}")
        print(f"  文章ID：{result['id']}  链接：{result['link']}")
    else:
        print(f"✗ 文章发布失败：{title}")

if __name__ == '__main__':
    data_list = load_data()
    print(f"共加载 {len(data_list)} 条数据")

    # 测试第一条数据
    if data_list:
        first_data = data_list[5]
        # 封面图可以是本地路径或 URL，例如：
        # cover = "./images/cover.jpg"
        # cover = "https://example.com/cover.jpg"
        cover = None   # 没有封面图
        process_and_submit(first_data, wp_status="draft")

    # 批量处理（取消注释）
    # for item in data_list:
    #     process_and_submit(item, wp_status="draft", cover_image_source=None)