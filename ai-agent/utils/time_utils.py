"""
时间工具 - MVP版本
"""
import time
from datetime import datetime, timezone

def now() -> datetime:
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)

def now_ms() -> int:
    """获取当前毫秒时间戳"""
    return int(time.time() * 1000)