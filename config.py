import json
import os

CONFIG_FILE = "./outfile/config.json"

def load_config():
    """加载配置，如果文件不存在则初始化默认配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 默认配置
    default_config = {"proxy_url": "http://127.0.0.1:7890", "cron_hour": 8}
    save_config(default_config)
    return default_config

def save_config(config_data):
    """保存配置到文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

config = load_config()