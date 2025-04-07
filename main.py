"""
=========================================
@Project ：AITestCase
@Date ：2025/3/22 上午9:39
@Author:Echoxiawan
@Comment:主程序入口
=========================================
"""
import argparse
import asyncio
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Set
import json
import tempfile

from core.web_explorer import WebExplorer
from core.test_generator import TestGenerator
from core.excel_exporter import ExcelExporter
from utils.logger import get_logger, console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rich_print
from rich.markdown import Markdown

# 获取日志记录器
logger = get_logger(__name__)

# 需要在内部逻辑中使用但不导出的字段列表
INTERNAL_FIELDS = ["test_area", "测试区域", "需求来源", "requirement_source"]


async def run_web_explorer_on_multiple_urls(
        urls: List[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
        captcha: Optional[str] = None,
        cookies: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    获取多个URL的页面信息

    Args:
        urls (List[str]): 要访问的网页URL列表
        username (Optional[str]): 用户名
        password (Optional[str]): 密码
        captcha (Optional[str]): 验证码
        cookies (Optional[str]): Cookies字符串

    Returns:
        Dict[str, Dict[str, Any]]: 多页面信息，以URL为键
    """
    all_results = {}

    for url in urls:
        console.print(f"[bold cyan]开始获取页面信息: {url}[/bold cyan]")
        result = await run_web_explorer(url, username, password, captcha, cookies)
        if result:
            all_results[url] = result

    return all_results


def run_web_explorer_on_multiple_urls_sync(
        urls: List[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
        captcha: Optional[str] = None,
        cookies: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    获取多个URL的页面信息(同步版本)

    Args:
        urls (List[str]): 要访问的网页URL列表
        username (Optional[str]): 用户名
        password (Optional[str]): 密码
        captcha (Optional[str]): 验证码
        cookies (Optional[str]): Cookies字符串

    Returns:
        Dict[str, Dict[str, Any]]: 多页面信息，以URL为键
    """
    # 使用asyncio.run执行异步函数
    return asyncio.run(run_web_explorer_on_multiple_urls(urls, username, password, captcha, cookies))


async def run_web_explorer(
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        captcha: Optional[str] = None,
        cookies: Optional[str] = None,
        use_ai_login: bool = False
) -> Dict[str, Any]:
    """
    获取指定URL的页面信息

    Args:
        url (str): 要访问的网页URL
        username (Optional[str]): 用户名
        password (Optional[str]): 密码
        captcha (Optional[str]): 验证码
        cookies (Optional[str]): Cookies字符串
        use_ai_login (bool): 是否使用AI智能识别登录元素

    Returns:
        Dict[str, Any]: 页面信息
    """
    explorer = WebExplorer()

    try:
        # 初始化浏览器
        await explorer.initialize()

        # 登录网页
        login_success = False
        if cookies:
            console.print("[bold yellow]使用Cookies登录...[/bold yellow]")
            login_success = await explorer.login_with_cookies(url, cookies)
        elif username and password:
            if use_ai_login:
                # 确定是否使用OpenAI API
                use_openai = os.getenv("OPENAI_API_KEY") is not None
                if use_openai:
                    console.print("[bold yellow]使用OpenAI API识别登录元素进行登录...[/bold yellow]")
                else:
                    console.print("[bold yellow]使用启发式规则识别登录元素进行登录...[/bold yellow]")

                login_success = await explorer.login_with_ai_recognition(url, username, password, captcha, use_openai=use_openai)
            else:
                console.print("[bold yellow]使用常规方法登录...[/bold yellow]")
                login_success = await explorer.login_with_credentials(url, username, password, captcha)
        else:
            # 如果没有提供登录信息，直接访问URL
            console.print("[bold yellow]无需登录，直接访问页面...[/bold yellow]")
            login_success = True

        if not login_success:
            console.print("[bold red]登录失败，无法继续获取页面信息[/bold red]")
            return {"error": "登录失败", "success": False}

        # 获取页面信息
        console.print(f"[bold green]开始获取页面信息...[/bold green]")
        page_result = await explorer.explore_page(url)

        # 检查是否成功
        if not page_result.get("success", False):
            error_msg = page_result.get("error", "未知错误")
            console.print(f"[bold red]获取页面信息失败: {error_msg}[/bold red]")
            return page_result

        return page_result

    except Exception as e:
        logger.error(f"获取页面信息过程中出错: {str(e)}")
        return {}
    finally:
        # 关闭浏览器
        await explorer.close()


def load_multiple_requirements(requirements_files: List[str]) -> Dict[str, str]:
    """
    加载多个需求文档文件，支持txt、docx和markdown格式，并将非markdown格式转换为markdown

    Args:
        requirements_files (List[str]): 需求文档文件路径列表

    Returns:
        Dict[str, str]: 以文件名为键，markdown内容为值的字典
    """
    requirements_dict = {}
    temp_dir = tempfile.mkdtemp(prefix="requirements_")
    logger.info(f"创建临时目录用于存储转换后的markdown文件: {temp_dir}")

    for file_path in requirements_files:
        try:
            filename = os.path.basename(file_path)
            file_extension = os.path.splitext(filename)[1].lower()
            
            # 获取不带扩展名的文件名
            base_filename = os.path.splitext(filename)[0]
            
            if file_extension == '.docx':
                try:
                    import docling
                    from docling.document_converter import DocumentConverter
                except ImportError:
                    console.print("[bold red]缺少docling库，正在安装...[/bold red]")
                    import subprocess
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "docling"])
                    import docling
                    from docling.document_converter import DocumentConverter
                
                # 转换文件为markdown
                console.print(f"[bold yellow]正在将docx文件转换为markdown: {filename}[/bold yellow]")
                
                # 创建markdown输出路径
                md_output_path = os.path.join(temp_dir, f"{base_filename}.md")
                
                # 使用DocumentConverter转换docx为markdown
                converter = DocumentConverter()
                result = converter.convert(file_path)
                markdown_content = result.document.export_to_markdown()
                
                # 保存markdown内容
                with open(md_output_path, "w", encoding="utf-8") as md_file:
                    md_file.write(markdown_content)
                
                # 将markdown内容添加到字典
                requirements_dict[filename] = markdown_content
                
                console.print(f"[bold green]已成功将docx文件转换为markdown: {filename}[/bold green]")
            elif file_extension in ['.md', '.txt']:
                # 对于txt或markdown文件，直接读取
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    requirements_dict[filename] = content
                
                console.print(f"[bold green]已成功读取文件: {filename}[/bold green]")
            else:
                console.print(f"[bold red]不支持的文件格式: {file_extension}，跳过该文件[/bold red]")
                continue
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
            console.print(f"[bold red]处理文件 {file_path} 时出错: {str(e)}[/bold red]")
    
    return requirements_dict


def generate_test_cases(page_data: Dict[str, Dict[str, Any]], requirements: Dict[str, str], include_old: bool = False) -> List[Dict[str, Any]]:
    """
    生成测试用例

    Args:
        page_data (Dict[str, Dict[str, Any]]): 页面数据，以URL为键
        requirements (Dict[str, str]): 需求文档内容，以文件名为键
        include_old (bool): 是否包含旧功能的测试用例

    Returns:
        List[Dict[str, Any]]: 生成的测试用例列表
    """
    generator = TestGenerator()
    
    # 生成测试用例
    test_cases = generator.generate_test_cases_from_multiple_sources(page_data, requirements, include_old)
    
    return test_cases


def export_to_excel(test_cases: List[Dict[str, Any]], urls: List[str], requirement_files: List[str], output_filename: Optional[str] = None, output_dir: Optional[str] = None) -> str:
    """
    将测试用例导出到Excel文件

    Args:
        test_cases (List[Dict[str, Any]]): 测试用例列表
        urls (List[str]): 页面URL列表
        requirement_files (List[str]): 需求文档文件路径列表
        output_filename (Optional[str]): 输出文件名
        output_dir (Optional[str]): 输出目录

    Returns:
        str: 导出的Excel文件路径
    """
    exporter = ExcelExporter(output_dir)
    
    # 准备元数据
    metadata = {
        "total_cases": len(test_cases),
        "urls": urls,
        "requirements": requirement_files
    }
    
    # 导出测试用例
    output_path = exporter.export_test_cases(test_cases, output_filename, metadata=metadata)
    
    console.print(f"[bold green]测试用例已导出为Excel文件: {output_path}[/bold green]")
    
    return output_path


def get_user_input() -> Tuple[List[str], Optional[str], Optional[str], Optional[str], Optional[str], Dict[str, str], bool, bool]:
    """
    交互式获取用户输入

    Returns:
        Tuple: 包含URLs、用户名、密码、验证码、Cookies、需求文档、是否包含旧功能、是否使用AI登录的元组
    """
    # 获取URLs
    urls_input = Prompt.ask("请输入要测试的页面URL（多个URL用逗号分隔）")
    urls = [url.strip() for url in urls_input.split(",") if url.strip()]
    
    # 选择登录方式
    login_method = Prompt.ask("请选择登录方式", choices=["无需登录", "使用账号密码登录", "使用AI智能登录", "使用Cookies登录"], default="无需登录")
    
    # 根据登录方式获取登录信息
    username = None
    password = None
    captcha = None
    cookies = None
    use_ai_login = False
    
    if login_method == "使用账号密码登录":
        username = Prompt.ask("请输入用户名")
        password = Prompt.ask("请输入密码", password=True)
        captcha_needed = Confirm.ask("是否需要验证码?", default=False)
        if captcha_needed:
            captcha = Prompt.ask("请输入验证码")
    elif login_method == "使用AI智能登录":
        username = Prompt.ask("请输入用户名")
        password = Prompt.ask("请输入密码", password=True)
        captcha_needed = Confirm.ask("是否需要验证码?", default=False)
        if captcha_needed:
            captcha = Prompt.ask("请输入验证码")
        use_ai_login = True
    elif login_method == "使用Cookies登录":
        cookies = Prompt.ask("请输入Cookies字符串（例如：name1=value1; name2=value2）")
    
    # 获取需求文档
    requirements = {}
    has_requirements = Confirm.ask("是否有需求文档?", default=False)
    if has_requirements:
        paths_input = Prompt.ask("请输入需求文档路径（多个文件用逗号分隔，支持.txt、.md、.docx格式）")
        requirement_files = [path.strip() for path in paths_input.split(",") if path.strip()]
        if requirement_files:
            requirements = load_multiple_requirements(requirement_files)
    
    # 是否包含旧功能的测试用例
    include_old = Confirm.ask("是否包含旧功能的测试用例?", default=False)
    
    return urls, username, password, captcha, cookies, requirements, include_old, use_ai_login


async def main_async(
    urls: List[str],
    username: Optional[str] = None,
    password: Optional[str] = None,
    captcha: Optional[str] = None,
    cookies: Optional[str] = None,
    requirements: Dict[str, str] = None,
    include_old: bool = False,
    api_key: Optional[str] = None,
    output_filename: Optional[str] = None,
    output_dir: Optional[str] = None,
    show_browser: bool = False,
    use_ai_login: bool = False
) -> None:
    """
    主异步函数

    Args:
        urls (List[str]): 要测试的页面URL列表
        username (Optional[str], optional): 用户名. Defaults to None.
        password (Optional[str], optional): 密码. Defaults to None.
        captcha (Optional[str], optional): 验证码. Defaults to None.
        cookies (Optional[str], optional): Cookies字符串. Defaults to None.
        requirements (Dict[str, str], optional): 需求文档内容，以文件名为键. Defaults to None.
        include_old (bool, optional): 是否包含旧功能的测试用例. Defaults to False.
        api_key (Optional[str], optional): OpenAI API密钥. Defaults to None.
        output_filename (Optional[str], optional): 输出文件名. Defaults to None.
        output_dir (Optional[str], optional): 输出目录. Defaults to None.
        show_browser (bool, optional): 是否显示浏览器. Defaults to False.
        use_ai_login (bool, optional): 是否使用AI智能识别登录元素. Defaults to False.
    """
    # 如果提供了API密钥，设置环境变量
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    # 如果设置了显示浏览器，设置环境变量
    if show_browser:
        os.environ["HEADLESS"] = "false"
    
    # 获取页面信息
    page_data = await run_web_explorer_on_multiple_urls(
        urls,
        username=username,
        password=password,
        captcha=captcha,
        cookies=cookies
    )
    
    if not page_data:
        console.print("[bold red]没有获取到任何页面信息，无法生成测试用例[/bold red]")
        return
    
    # 生成测试用例
    if requirements is None:
        requirements = {}
    
    console.print("[bold green]正在生成测试用例...[/bold green]")
    test_cases = generate_test_cases(page_data, requirements, include_old)
    
    if not test_cases:
        console.print("[bold red]未能生成任何测试用例[/bold red]")
        return
    
    console.print(f"[bold green]成功生成 {len(test_cases)} 个测试用例[/bold green]")
    
    # 导出为Excel
    requirement_files = list(requirements.keys()) if requirements else []
    export_to_excel(test_cases, urls, requirement_files, output_filename, output_dir)


def main():
    # 如果命令行参数中包含 --web，则启动Web界面
    if '--web' in sys.argv:
        try:
            from app import app
            app.run(host='0.0.0.0', port=5000, debug=True)
            return
        except ImportError as e:
            logger.error(f"启动Web界面失败: {str(e)}")
            logger.error("请确保已安装Flask: pip install flask")
            return
    
    # 常规命令行模式
    # 获取用户输入参数
    try:
        # 命令行参数解析
        parser = argparse.ArgumentParser(description='AI辅助测试用例生成工具')
        parser.add_argument('--url', type=str, help='网页URL')
        parser.add_argument('--username', type=str, help='登录用户名')
        parser.add_argument('--password', type=str, help='登录密码')
        parser.add_argument('--captcha', type=str, help='验证码')
        parser.add_argument('--cookies', type=str, help='Cookie字符串')
        parser.add_argument('--requirements', type=str, help='需求文档路径，多个文件以逗号分隔')
        parser.add_argument('--output', type=str, help='输出Excel文件名')
        parser.add_argument('--output-dir', type=str, help='输出目录')
        parser.add_argument('--api-key', type=str, help='OpenAI API密钥')
        parser.add_argument('--include-old', action='store_true', help='包含旧特性')
        parser.add_argument('--interactive', action='store_true', help='交互模式')
        parser.add_argument('--show', type=str, choices=['true', 'false'], help='是否显示浏览器操作过程')
        parser.add_argument('--login-url', type=str, help='登录页面URL')
        parser.add_argument('--use-ai-login', action='store_true', help='使用AI识别登录元素')
        parser.add_argument('--web', action='store_true', help='启动Web界面')
        args = parser.parse_args()
        
        # 检查是否提供了URL参数
        if not args.url and not args.interactive:
            parser.print_help()
            print("\n请提供网页URL或使用--interactive参数进入交互模式")
            return
        
        # 如果是交互式模式，获取用户输入
        if args.interactive:
            urls, username, password, captcha, cookies, requirements, include_old, use_ai_login = get_user_input()
        else:
            # 从命令行参数获取
            urls = [args.url] if args.url else []
            username = args.username
            password = args.password
            captcha = args.captcha
            cookies = args.cookies
            use_ai_login = args.use_ai_login
            
            # 解析需求文档路径
            if args.requirements:
                requirements = {}
                requirement_files = args.requirements.split(',')
                if requirement_files:
                    requirements = load_multiple_requirements(requirement_files)
            else:
                requirements = {}
            
            include_old = args.include_old
        
        # 运行异步主函数
        asyncio.run(main_async(
            urls=urls,
            username=username,
            password=password,
            captcha=captcha,
            cookies=cookies,
            requirements=requirements,
            include_old=include_old,
            api_key=args.api_key,
            output_filename=args.output,
            output_dir=args.output_dir,
            show_browser=args.show == 'true' if args.show else False,
            use_ai_login=use_ai_login
        ))
    
    except Exception as e:
        logger.error(f"程序运行过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
