"""
=========================================
@Project ：AITestCase
@Date ：2025/3/22 上午9:39
@Author:Echoxiawan
@Comment:配置文件，包含项目的主要配置参数
=========================================

"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# OpenAI配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")  # 使用的OpenAI模型
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))  # 创意性参数
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")

# Playwright配置
BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")  # 可选: chromium, firefox, webkit
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"  # 是否使用无头模式
SLOW_MO = int(os.getenv("SLOW_MO", "100"))  # 慢速执行的毫秒数
TIMEOUT = int(os.getenv("TIMEOUT", "30000"))  # 超时时间（毫秒）

# 输出配置
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")  # 输出目录
DEFAULT_EXCEL_FILENAME = os.getenv("DEFAULT_EXCEL_FILENAME", "测试用例.xlsx")  # 默认Excel文件名

# 探索配置
EXPLORE_DEPTH = int(os.getenv("EXPLORE_DEPTH", "0"))  # 页面探索深度，0表示只访问当前页面，不进行探索 