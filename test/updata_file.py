import requests
import mimetypes
import os
import tempfile
import argparse
from dotenv import load_dotenv

load_dotenv()

# 代理配置
PROXY_URL = 'http://127.0.0.1:7890'
proxies = {'http': PROXY_URL, 'https': PROXY_URL} if PROXY_URL else None

# 多站点配置列表
SITES = [
    {"url": "https://goldmedalhand.com", "username": "admin", "app_password": "NX1z XQDz nHjF i1OC aBU7 xkpP"},
    # 按需取消注释或添加其他站点
    {"url": "https://gamblerheart.com", "username": "admin", "app_password": "pmmF 0Tgb I5TO rags kIIf AWfS"},
]

def get_auth(username, app_password):
    """返回 Basic 认证元组"""
    return (username, app_password.replace(" ", ""))

def download_file(url):
    """下载远程文件到临时目录"""
    try:
        resp = requests.get(url, proxies=proxies, timeout=30, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', '')
        ext = mimetypes.guess_extension(content_type) or '.bin'
        
        # 尝试从URL中提取更准确的文件名
        from urllib.parse import urlparse, unquote
        url_path = unquote(urlparse(url).path)
        filename = os.path.basename(url_path)
        if not filename:
            filename = f"downloaded_file{ext}"
            
        fd, tmp_path = tempfile.mkstemp(suffix=f"_{filename}")
        os.close(fd)
        
        with open(tmp_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return tmp_path
    except Exception as e:
        print(f"✗ 下载远程文件失败 {url}: {e}")
        return None

def upload_file_to_wp(wp_url, username, app_password, file_source):
    """
    核心功能：上传文件到 WordPress 媒体库
    :param file_source: 本地文件路径 或 远程文件URL
    :return: (media_id, media_url) 上传成功返回元组，失败返回
    """
    tmp_file = None
    local_path = file_source

    # 1. 如果是远程URL，先下载到本地
    if file_source.startswith(('http://', 'https://')):
        print(f"  ⬇ 检测到远程文件，正在下载: {file_source}")
        tmp_file = download_file(file_source)
        if not tmp_file:
            return None, None
        local_path = tmp_file

    # 2. 检查本地文件是否存在
    if not os.path.exists(local_path):
        print(f"✗ 本地文件不存在: {local_path}")
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)
        return None, None

    # 3. 准备上传
    filename = os.path.basename(local_path)
    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"

    try:
        with open(local_path, "rb") as f:
            print(f"  ⬆ 正在上传文件: {filename} ({mime})")
            response = requests.post(
                f"{wp_url}/wp-json/wp/v2/media",
                auth=get_auth(username, app_password),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": mime,
                },
                data=f,
                proxies=proxies,
                timeout=120,  # 大文件上传适当增加超时时间
            )
    except Exception as e:
        print(f"✗ 上传请求异常: {e}")
        return None, None
    finally:
        # 清理临时文件
        if tmp_file and os.path.exists(tmp_file):
            os.unlink(tmp_file)

    # 4. 处理响应
    if response.status_code == 201:
        media_data = response.json()
        media_id = media_data.get("id")
        media_url = media_data.get("source_url")
        print(f"  ✔ 上传成功! ID: {media_id}, URL: {media_url}")
        return media_id, media_url
    else:
        print(f"✗ 文件上传失败 [{file_source}]，HTTP {response.status_code}")
        print(f"  响应内容: {response.text[:500]}")
        return None, None

def batch_upload_to_sites(file_path):
    """将同一个文件批量上传到配置的所有站点"""
    for site in SITES:
        wp_url = site["url"].rstrip('/')
        username = site["username"]
        app_password = site["app_password"]
        
        print(f"\n==== 开始处理站点: {wp_url} ====")
        upload_file_to_wp(wp_url, username, app_password, file_path)
        print(f"==== 站点 {wp_url} 处理完毕 ====")

if __name__ == '__main__':

    source_file = "https://lncimg.lance.com.br/cdn-cgi/image/width=950,quality=75,fit=pad,format=webp/uploads/2026/06/WhatsApp-Image-2026-06-09-at-18.15.11-2-aspect-ratio-512-320.jpeg"
    print(f"准备上传的文件源: {source_file}")
    
    # 执行批量上传
    batch_upload_to_sites(source_file)
