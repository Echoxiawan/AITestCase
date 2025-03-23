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
        cookies: Optional[str] = None,
        device_type: str = "desktop"
) -> Dict[str, Dict[str, Any]]:
    """
    获取多个URL的页面信息

    Args:
        urls (List[str]): 要访问的网页URL列表
        username (Optional[str]): 用户名
        password (Optional[str]): 密码
        captcha (Optional[str]): 验证码
        cookies (Optional[str]): Cookies字符串
        device_type (str): 设备类型，可选值为 "desktop", "mobile", "tablet"

    Returns:
        Dict[str, Dict[str, Any]]: 多页面信息，以URL为键
    """
    all_results = {}

    for url in urls:
        console.print(f"[bold cyan]开始获取页面信息: {url} (设备类型: {device_type})[/bold cyan]")
        result = await run_web_explorer(url, username, password, captcha, cookies, device_type)
        if result:
            all_results[url] = result

    return all_results


async def run_web_explorer(
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        captcha: Optional[str] = None,
        cookies: Optional[str] = None,
        device_type: str = "desktop",
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
        device_type (str): 设备类型，可选值为 "desktop", "mobile", "tablet"
        use_ai_login (bool): 是否使用AI智能识别登录元素

    Returns:
        Dict[str, Any]: 页面信息
    """
    explorer = WebExplorer()

    try:
        # 初始化浏览器
        await explorer.initialize(device_type=device_type)

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
        console.print(f"[bold green]开始获取页面信息... (设备类型: {device_type})[/bold green]")
        page_result = await explorer.explore_page(url, device_type=device_type)

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
    加载多个需求文档文件

    Args:
        requirements_files (List[str]): 需求文档文件路径列表

    Returns:
        Dict[str, str]: 以文件名为键，内容为值的字典
    """
    requirements_dict = {}

    for file_path in requirements_files:
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                requirements_dict[filename] = content
            console.print(f"[bold green]已加载需求文档: {filename}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]读取文件 {file_path} 失败: {str(e)}[/bold red]")

    return requirements_dict


def generate_test_cases(
        page_data: Dict[str, Dict[str, Any]],
        new_requirements: Optional[Dict[str, str]] = None,
        include_old_features: bool = False,
        api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    生成测试用例

    Args:
        page_data (Dict[str, Dict[str, Any]]): 多页面探索数据，以URL为键
        new_requirements (Optional[Dict[str, str]]): 新需求文档字典，以文件名为键
        include_old_features (bool): 是否包含旧功能的测试用例
        api_key (Optional[str]): OpenAI API密钥

    Returns:
        List[Dict[str, Any]]: 测试用例列表
    """
    try:
        generator = TestGenerator(api_key=api_key)
        console.print("[bold green]开始生成测试用例...[/bold green]")
        test_cases = generator.generate_test_cases_from_multiple_sources(
            page_data,
            new_requirements=new_requirements,
            include_old_features=include_old_features
        )
        return test_cases
    except Exception as e:
        logger.error(f"生成测试用例时出错: {str(e)}")
        return []


def export_to_excel(
        test_cases: List[Dict[str, Any]],
        page_urls: List[str],
        requirement_files: List[str],
        filename: Optional[str] = None,
        output_dir: Optional[str] = None
) -> str:
    """
    导出测试用例为Excel文件

    Args:
        test_cases (List[Dict[str, Any]]): 测试用例列表
        page_urls (List[str]): 页面URL列表
        requirement_files (List[str]): 需求文档文件列表
        filename (Optional[str]): 输出文件名
        output_dir (Optional[str]): 输出目录

    Returns:
        str: 输出文件的完整路径
    """
    try:
        exporter = ExcelExporter(output_dir=output_dir)
        console.print("[bold green]开始导出测试用例...[/bold green]")

        # 添加元数据
        metadata = {
            "urls": page_urls,
            "requirements": requirement_files,
            "total_cases": len(test_cases)
        }

        output_path = exporter.export_test_cases(
            test_cases,
            filename=filename,
            metadata=metadata
        )
        return output_path
    except Exception as e:
        logger.error(f"导出测试用例时出错: {str(e)}")
        return ""


def get_user_input() -> Tuple[List[str], Optional[str], Optional[str], Optional[str], Optional[str], Dict[str, str], bool, str, bool]:
    """
    获取用户输入

    Returns:
        Tuple[List[str], Optional[str], Optional[str], Optional[str], Optional[str], Dict[str, str], bool, str, bool]:
        (URL列表, 用户名, 密码, 验证码, Cookies, 新需求文档字典, 是否包含旧功能, 设备类型, 是否使用AI识别登录)
    """
    rich_print(Panel.fit(
        Markdown("# Web测试用例生成工具\n\n"
                "此工具帮助您生成Web应用的测试用例，只需提供URL，工具将生成当前页面的测试用例。"),
        title="欢迎使用",
        border_style="blue"
    ))

    # 获取URL列表
    urls_input = Prompt.ask("[bold]请输入要测试的页面URL列表[/bold] (多个URL用逗号分隔)")
    urls = [url.strip() for url in urls_input.split(",")]

    # 选择设备类型
    device_choices = ["desktop", "mobile", "tablet"]
    device_type = Prompt.ask(
        "[bold]请选择设备类型[/bold] (desktop=桌面设备, mobile=手机, tablet=平板)",
        choices=device_choices,
        default="desktop"
    )

    # 选择登录方式
    login_choices = ["无需登录", "使用账号密码登录", "使用AI智能登录", "使用Cookies登录"]
    login_method = Prompt.ask(
        "[bold]请选择登录方式[/bold]",
        choices=login_choices,
        default=login_choices[0]
    )

    username = None
    password = None
    captcha = None
    cookies = None
    use_ai_login = False

    if login_method == "使用账号密码登录":
        username = Prompt.ask("[bold]请输入用户名[/bold]")
        password = Prompt.ask("[bold]请输入密码[/bold]")
        captcha = Prompt.ask("[bold]请输入验证码[/bold] (如无需验证码请留空)")
        use_ai_login = False
    elif login_method == "使用AI智能登录":
        username = Prompt.ask("[bold]请输入用户名[/bold]")
        password = Prompt.ask("[bold]请输入密码[/bold]")
        captcha = Prompt.ask("[bold]请输入验证码[/bold] (如无需验证码请留空)")
        use_ai_login = True
    elif login_method == "使用Cookies登录":
        cookies = Prompt.ask("[bold]请输入Cookies字符串[/bold]")

    # 获取需求文档路径
    requirements_paths = {}
    if Confirm.ask("[bold]是否需要分析需求文档？[/bold]", default=False):
        while True:
            req_name = Prompt.ask("[bold]请输入需求名称[/bold] (如无更多需求请留空)")
            if not req_name:
                break
            req_path = Prompt.ask("[bold]请输入需求文档路径[/bold]")
            requirements_paths[req_name] = req_path

    # 是否包含旧功能
    include_old = Confirm.ask("[bold]是否包含旧功能的测试用例？[/bold]", default=True)

    return urls, username, password, captcha, cookies, requirements_paths, include_old, device_type, use_ai_login


async def main_async():
    """主异步函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Web测试用例生成工具")
    parser.add_argument("--url", type=str, help="要生成测试用例的网页URL")
    parser.add_argument("--urls", type=str, help="要生成测试用例的网页URL列表，以逗号分隔")
    parser.add_argument("--username", type=str, help="登录用户名")
    parser.add_argument("--password", type=str, help="登录密码")
    parser.add_argument("--captcha", type=str, help="登录验证码")
    parser.add_argument("--cookies", type=str, help="登录Cookie")
    parser.add_argument("--login-url", type=str, help="登录页面URL，如果与测试URL不同")
    parser.add_argument("--device", type=str, choices=["desktop", "mobile", "tablet"], default="desktop", help="设备类型")
    parser.add_argument("--requirements", type=str, help="需求文档文件路径，多个文件以逗号分隔")
    parser.add_argument("--include-old", action="store_true", help="是否包含旧功能的测试用例")
    parser.add_argument("--output", type=str, help="输出文件名")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    parser.add_argument("--use-ai-login", action="store_true", help="使用AI识别登录元素")
    parser.add_argument("--show", type=str, choices=["true", "false"], help="是否显示浏览器窗口")
    
    args = parser.parse_args()
    
    # 如果提供了show参数，设置环境变量
    if args.show:
        os.environ["HEADLESS"] = "false" if args.show.lower() == "true" else "true"
    
    # 如果没有提供足够的参数，使用交互模式获取输入
    if not (args.url or args.urls):
        urls, username, password, captcha, cookies, requirements, include_old, device_type, use_ai_login = get_user_input()
    else:
        # 从命令行参数获取输入
        if args.url:
            urls = [args.url]
        elif args.urls:
            urls = [url.strip() for url in args.urls.split(",")]
        
        username = args.username
        password = args.password
        captcha = args.captcha
        cookies = args.cookies
        
        # 处理需求文档
        requirements = {}
        if args.requirements:
            requirement_files = [path.strip() for path in args.requirements.split(",")]
            requirements = load_multiple_requirements(requirement_files)
        
        include_old = args.include_old
        device_type = args.device
        use_ai_login = args.use_ai_login
    
    # 运行页面分析
    console.print("[bold cyan]开始页面分析...[/bold cyan]")
    start_time = time.time()
    
    page_data = await run_web_explorer_on_multiple_urls(
        urls,
        username,
        password,
        captcha,
        cookies,
        device_type
    )
    
    # 检查是否存在页面数据
    if not page_data:
        console.print("[bold red]未获取到任何页面数据，无法生成测试用例[/bold red]")
        return
    
    processing_time = round(time.time() - start_time, 2)
    console.print(f"[bold green]页面分析完成! 耗时: {processing_time}秒[/bold green]")
    
    # 生成测试用例
    console.print("[bold cyan]开始生成测试用例...[/bold cyan]")
    start_time = time.time()
    
    test_cases = generate_test_cases(
        page_data,
        requirements,
        include_old,
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    if not test_cases:
        console.print("[bold red]未生成任何测试用例[/bold red]")
        return
    
    processing_time = round(time.time() - start_time, 2)
    console.print(f"[bold green]测试用例生成完成! 共 {len(test_cases)} 个测试用例, 耗时: {processing_time}秒[/bold green]")
    
    # 导出测试用例
    console.print("[bold cyan]开始导出测试用例...[/bold cyan]")
    
    output_file = args.output if args.output else None
    output_dir = args.output_dir if args.output_dir else None
    
    output_path = export_to_excel(
        test_cases,
        urls,
        list(requirements.keys()) if requirements else [],
        filename=output_file,
        output_dir=output_dir
    )
    
    if output_path:
        console.print(f"[bold green]测试用例已导出到: {output_path}[/bold green]")
    else:
        console.print("[bold red]测试用例导出失败[/bold red]")
    
    console.print("[bold green]所有操作已完成![/bold green]")


def main():
    """主函数"""
    # if sys.platform == "win32":
    #     # Windows平台使用ProactorEventLoop
    #     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
