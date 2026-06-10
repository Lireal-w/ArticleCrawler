from dateutil import parser
from datetime import timezone

def parse_time_to_timestamp(time_str):
    """
    将时间字符串转为 Unix 时间戳（秒，整数）
    支持多种格式，如 "2026-05-27T18:20:07+04:00", "May 27, 2026", "2026-06-05 14:53:28"
    """
    if not time_str:
        return None
    # 去除 \t \n
    time_str = time_str.replace('\t', '').replace('\n', '')
    try:
        # 使用 dateutil 解析，自动处理时区
        dt = parser.parse(time_str)
        # 如果解析后没有时区信息，则假设为 UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # 转为时间戳
        return int(dt.timestamp())
    except Exception as e:
        return None