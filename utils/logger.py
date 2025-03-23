"""
=========================================
@Project ：AITestCase
@Date ：2025/3/22 上午9:39
@Author:Echoxiawan
@Comment:日志工具模块，提供全局日志记录功能
=========================================
"""
import logging
from rich.console import Console
from rich.logging import RichHandler
import os
from datetime import datetime

# 创建日志目录
os.makedirs("logs", exist_ok=True)

# 获取当前时间作为日志文件名
log_filename = f"logs/ai_testcase_{datetime.now().strftime('%Y%m%d')}.log"

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler(log_filename)
    ]
)

# 创建控制台对象，用于美化输出
console = Console()

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name (str): 日志记录器名称
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return logging.getLogger(name) 