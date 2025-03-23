"""
=========================================
@Project ：AITestCase
@Date ：2025/3/22 上午9:39
@Author:Echoxiawan
@Comment:辅助工具模块，提供各种实用函数
=========================================
"""
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

def is_valid_url(url: str) -> bool:
    """
    检查URL是否有效
    
    Args:
        url (str): 要检查的URL
    
    Returns:
        bool: URL是否有效
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """
    安全加载JSON字符串
    
    Args:
        json_str (str): JSON字符串
    
    Returns:
        Dict[str, Any]: 解析后的JSON对象，失败则返回空字典
    """
    try:
        return json.loads(json_str)
    except Exception:
        return {}

def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不允许的字符
    
    Args:
        filename (str): 原始文件名
    
    Returns:
        str: 清理后的文件名
    """
    # 替换不允许的字符为下划线
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def ensure_dir_exists(directory: str) -> None:
    """
    确保目录存在，不存在则创建
    
    Args:
        directory (str): 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def extract_domain(url: str) -> str:
    """
    从URL中提取域名，返回值最前面加"."

    Args:
        url (str): URL

    Returns:
        str: 域名，带前导"."
    """
    if not url:
        return ""

    # 确保URL有协议前缀
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    try:
        parsed = urlparse(url)
        domain = parsed.netloc

        # 处理端口号
        if ':' in domain:
            domain = domain.split(':')[0]

        # 检查是否是IP地址
        if is_ip_address(domain):
            return '.' + domain

        # 处理子域名，返回主域名
        parts = domain.split('.')
        if len(parts) > 2:
            # 对于特殊的二级域名，如co.uk, com.cn等
            if len(parts[-2]) <= 3 and len(parts[-1]) <= 3 and len(parts) > 2:
                return '.' + '.'.join(parts[-3:])
            else:
                return '.' + '.'.join(parts[-2:])

        return '.' + domain
    except Exception as e:
        print(f"提取域名时出错: {e}")
        return ""
        
def is_ip_address(text: str) -> bool:
    """
    判断文本是否是IP地址
    
    Args:
        text (str): 要检查的文本
    
    Returns:
        bool: 是否是IP地址
    """
    pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    match = re.match(pattern, text)
    if not match:
        return False
    
    for i in range(1, 5):
        num = int(match.group(i))
        if num < 0 or num > 255:
            return False
    
    return True


def parse_cookies(url: str, cookie_str: str):
    # 解析 URL 获取 domain
    parsed_url = urlparse(url)
    domain = extract_domain(url)

    # 解析 Cookie 字符串
    cookies = []
    for item in cookie_str.split('; '):
        if '=' in item:
            name, value = item.split('=', 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": domain,
                "path": "/"
            })

    return cookies