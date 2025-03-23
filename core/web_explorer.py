"""
网页探索模块，负责自动化登录网页并探索页面功能
"""
import asyncio
import json
import re
import time
import traceback
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import urlparse, urljoin

from playwright.async_api import (
    Page, Browser, BrowserContext, async_playwright,
    TimeoutError as PlaywrightTimeoutError,
    ElementHandle
)

from config.settings import (
    BROWSER_TYPE, HEADLESS, SLOW_MO, TIMEOUT,
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_BASE_URL
)
from utils.logger import get_logger
from utils.helpers import (
    is_valid_url, extract_domain, parse_cookies
)

# 获取日志记录器
logger = get_logger(__name__)


class WebExplorer:
    """网页探索器，负责自动化登录网页并探索页面功能"""

    def __init__(self):
        """初始化网页探索器"""
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.visited_urls = set()
        self.page_data = {}
        self.interactive_elements = {}
        self.click_paths = []
        self.explored_urls = set()
        self.results = []

    async def initialize(self, device_type: str = "desktop", url: str = None, cookies_str: str = None) -> None:
        """
        初始化Playwright和浏览器

        Args:
            device_type (str): 设备类型，可选值为 "desktop", "mobile", "tablet"
            cookies_str (str, optional): 可选的Cookie字符串，如果提供将在浏览器启动时直接应用
        """
        self.playwright = await async_playwright().start()

        # 根据配置选择浏览器类型
        if BROWSER_TYPE == "firefox":
            self.browser = await self.playwright.firefox.launch(
                headless=HEADLESS, slow_mo=SLOW_MO
            )
        elif BROWSER_TYPE == "webkit":
            self.browser = await self.playwright.webkit.launch(
                headless=HEADLESS, slow_mo=SLOW_MO
            )
        else:  # 默认为 chromium
            self.browser = await self.playwright.chromium.launch(
                headless=HEADLESS, slow_mo=SLOW_MO
            )

        # 准备浏览器上下文参数
        context_options = {}

        # 根据设备类型设置视口和用户代理
        if device_type == "mobile":
            # 模拟移动设备
            context_options.update({
                "viewport": {"width": 375, "height": 667},  # iPhone 8 尺寸
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
                "device_scale_factor": 2.0,
                "is_mobile": True,
                "has_touch": True
            })
            logger.info("初始化为移动设备模式")
        elif device_type == "tablet":
            # 模拟平板设备
            context_options.update({
                "viewport": {"width": 768, "height": 1024},  # iPad 尺寸
                "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
                "device_scale_factor": 2.0,
                "is_mobile": True,
                "has_touch": True
            })
            logger.info("初始化为平板设备模式")
        else:
            # 默认桌面设备
            context_options.update({
                "viewport": {"width": 1280, "height": 800},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            })
            logger.info("初始化为桌面设备模式")

        # 如果提供了cookies_str，预处理并添加到storage_state
        cookies = None
        if cookies_str:
            try:
                cookies = parse_cookies(url, cookies_str)
            except Exception as e:
                logger.error(f"预处理Cookie时出错: {str(e)}")
                # 出错时继续不带Cookie创建上下文

        # 创建浏览器上下文
        self.context = await self.browser.new_context(**context_options)
        if cookies:
            logger.info(f"使用预设的 {len(cookies)} 个Cookie初始化浏览器")
            await self.context.add_cookies(cookies)

        # 设置超时
        self.context.set_default_timeout(TIMEOUT)

        # 创建新页面
        self.page = await self.context.new_page()

        # 监听控制台消息
        self.page.on("console", lambda msg: logger.debug(f"浏览器控制台: {msg.text}"))

        # 监听页面错误
        self.page.on("pageerror", lambda err: logger.error(f"页面错误: {err}"))

        logger.info("浏览器初始化完成")

    async def close(self) -> None:
        """关闭浏览器和Playwright"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭")

    async def login_with_credentials(self, url: str, username: str, password: str, captcha_code: str = None) -> bool:
        """
        使用用户名和密码登录网站

        Args:
            url: 登录页面URL
            username: 用户名
            password: 密码
            captcha_code: 验证码(如果需要)

        Returns:
            bool: 登录是否成功
        """
        try:
            # 导航到登录页面
            logger.info(f"正在访问登录页面: {url}")
            response = await self.page.goto(url, wait_until="networkidle")

            if not response:
                logger.error(f"无法加载登录页面: {url}")
                return False

            # 等待页面完全加载
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)  # 给页面额外的加载时间

            # 查找用户名输入框
            username_selectors = [
                "input[name='username']",
                "input[name='user']",
                "input[name='email']",
                "input[name='account']",
                "input[name='phone']",
                "input[name='mobile']",
                "input[name='login']",
                "input[id='username']",
                "input[id='user']",
                "input[id='email']",
                "input[id='account']",
                "input[id='phone']",
                "input[id='mobile']",
                "input[id='login']",
                "input[type='text']",
                "input[type='email']",
                "input[placeholder*='用户名']",
                "input[placeholder*='邮箱']",
                "input[placeholder*='账号']",
                "input[placeholder*='手机']",
                "input[placeholder*='username']",
                "input[placeholder*='email']",
                "input[placeholder*='account']",
                "input[placeholder*='phone']"
            ]

            # 查找密码输入框
            password_selectors = [
                "input[name='password']",
                "input[name='pwd']",
                "input[name='pass']",
                "input[id='password']",
                "input[id='pwd']",
                "input[id='pass']",
                "input[type='password']",
                "input[placeholder*='密码']",
                "input[placeholder*='password']",
                "input[placeholder*='pwd']"
            ]

            # 查找提交按钮
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('登录')",
                "button:has-text('登 录')",
                "button:has-text('Login')",
                "button:has-text('Sign in')",
                "a:has-text('登录')",
                "a:has-text('Login')",
                "a:has-text('Sign in')",
                ".login-button",
                ".loginBtn",
                ".submit-btn",
                ".signin-button",
                "#login-button",
                "#loginBtn",
                "#submit-btn",
                "#signin-button"
            ]

            # 尝试查找验证码输入框
            captcha_selectors = [
                "input[name='captcha']",
                "input[name='verifyCode']",
                "input[name='validCode']",
                "input[id='captcha']",
                "input[id='verifyCode']",
                "input[id='validCode']",
                "input[placeholder*='验证码']",
                "input[placeholder*='captcha']",
                "input[placeholder*='verify']"
            ]

            # 查找并填写用户名
            username_element = None
            for selector in username_selectors:
                try:
                    username_element = await self.page.wait_for_selector(selector, timeout=2000)
                    if username_element:
                        break
                except Exception:
                    continue

            if not username_element:
                logger.error("未找到用户名输入框")
                return False

            await username_element.click()
            await username_element.fill("")  # 先清空
            await username_element.type(username, delay=100)
            logger.info(f"已填写用户名: {username}")

            # 查找并填写密码
            password_element = None
            for selector in password_selectors:
                try:
                    password_element = await self.page.wait_for_selector(selector, timeout=2000)
                    if password_element:
                        break
                except Exception:
                    continue

            if not password_element:
                logger.error("未找到密码输入框")
                return False

            await password_element.click()
            await password_element.fill("")  # 先清空
            await password_element.type(password, delay=100)
            logger.info("已填写密码")

            # 查找并填写验证码(如果有)
            if captcha_code:
                captcha_element = None
                for selector in captcha_selectors:
                    try:
                        captcha_element = await self.page.wait_for_selector(selector, timeout=2000)
                        if captcha_element:
                            break
                    except Exception:
                        continue

                if captcha_element:
                    await captcha_element.click()
                    await captcha_element.fill("")  # 先清空
                    await captcha_element.type(captcha_code, delay=100)
                    logger.info(f"已填写验证码: {captcha_code}")
                else:
                    logger.warning("未找到验证码输入框，但提供了验证码")

            # 查找并点击提交按钮
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if submit_button:
                        break
                except Exception:
                    continue

            if not submit_button:
                logger.error("未找到提交按钮")
                return False

            # 点击提交按钮
            logger.info("正在点击提交按钮")
            await submit_button.click()

            # 等待网络请求完成
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                logger.warning(f"等待网络请求完成时出错: {str(e)}")

            # 等待一段时间以确保登录结果可用
            await asyncio.sleep(3)

            # 检查登录是否成功
            current_url = self.page.url
            logger.info(f"登录后的URL: {current_url}")

            # 检查URL变化
            if current_url != url and (
                    "account" in current_url or "dashboard" in current_url or "home" in current_url or "welcome" in current_url):
                logger.info("登录成功(URL变化)")
                return True

            # 检查页面内容
            page_content = await self.page.content()
            logout_texts = ["退出", "登出", "注销", "logout", "sign out", "signout"]
            if any(text in page_content.lower() for text in logout_texts):
                logger.info("登录成功(检测到退出登录元素)")
                return True

            # 检查可能的登录失败信息
            failure_texts = ["密码错误", "用户名错误", "登录失败"]
            if any(text in page_content.lower() for text in failure_texts):
                logger.error("登录失败(检测到失败消息)")
                return False

            # 如果页面内容看起来包含个人信息，也认为登录成功
            personal_texts = ["个人中心", "我的账户", "用户名", "profile", "account", "my center"]
            if any(text in page_content.lower() for text in personal_texts):
                logger.info("登录成功(检测到个人信息)")
                return True

            # 默认情况下假设登录成功
            logger.warning("无法确定登录状态，默认为成功")
            return True

        except Exception as e:
            logger.error(f"登录过程中出错: {str(e)}")
            return False

    async def login_with_cookies(self, url: str, cookies_str: str) -> bool:
        """
        使用Cookies登录网页

        Args:
            url (str): 目标网页URL
            cookies_str (str): Cookies字符串

        Returns:
            bool: 是否登录成功
        """
        try:
            # 检查是否已有现有页面和上下文
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()

            # 使用cookies重新初始化浏览器
            logger.info("使用cookies重新创建浏览器上下文")
            await self.initialize(url=url, cookies_str=cookies_str)

            # 直接导航到目标URL
            logger.info(f"带Cookie直接导航到目标URL: {url}")
            try:
                response = await self.page.goto(url, wait_until="networkidle", timeout=30000)
                if not response:
                    logger.error(f"无法加载目标URL: {url}")
                    return False
            except Exception as e:
                logger.error(f"导航到目标URL时出错: {str(e)}")
                return False

            # 检查是否成功登录
            current_url = self.page.url
            logger.info(f"当前页面URL: {current_url}")

            # 等待页面加载完成
            await asyncio.sleep(2)  # 给页面一点时间加载

            # 检查页面内容，确认登录状态
            page_content = await self.page.content()

            # 1. 检查是否有登录按钮，如果没有可能已登录
            login_elements = await self.page.query_selector_all(
                'button:has-text("登录"), a:has-text("登录"), button:has-text("Login"), a:has-text("Login"), button:has-text("Sign in"), a:has-text("Sign in")')
            if login_elements:
                logger.warning(f"页面上仍存在 {len(login_elements)} 个登录按钮，可能未成功登录")

                # 保存截图以便调试
                screenshot_path = f"login_failed_{int(time.time())}.png"
                await self.page.screenshot(path=screenshot_path)
                logger.info(f"已保存失败登录页面截图到 {screenshot_path}")

                # 保存页面源码以便调试
                html_path = f"login_failed_{int(time.time())}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                logger.info(f"已保存失败登录页面源码到 {html_path}")

                return False
            else:
                logger.info("页面上未找到登录按钮，可能已成功登录")

            # 2. 检查是否有登出/用户信息元素，表明已登录
            logout_texts = ["退出", "登出", "注销", "logout", "sign out", "signout"]
            user_info_texts = ["个人中心", "我的账户", "用户名", "profile", "account", "my center", "我的", "用户中心"]

            for text in logout_texts + user_info_texts:
                try:
                    elements = await self.page.query_selector_all(f'text="{text}"')
                    if elements:
                        logger.info(f"检测到已登录状态指示: '{text}'")
                        return True
                except Exception:
                    continue

            # 3. 检查页面的cookie是否包含会话cookie
            cookies_after = await self.context.cookies()
            session_cookie_names = ["sid", "session", "token", "auth", "logged", "user", "ssid"]
            has_session_cookie = False

            for cookie in cookies_after:
                if any(session_name in cookie['name'].lower() for session_name in session_cookie_names):
                    logger.info(f"检测到会话Cookie: {cookie['name']}")
                    has_session_cookie = True
                    break

            if has_session_cookie:
                logger.info("基于会话Cookie判断为已登录状态")
                return True

            # 如果没有明确的登录状态指示，但也没有登录按钮，假定为已登录
            if not login_elements:
                logger.info("虽然没有明确的登录状态指示，但页面上没有登录按钮，假定为已登录")
                return True

            logger.warning("无法确定登录状态，默认为未登录")
            return False

        except Exception as e:
            logger.error(f"使用Cookies登录过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    async def login_with_ai_recognition(self, url: str, username: str, password: str, captcha_code: str = None,
                                        use_openai: bool = True) -> bool:
        """
        使用AI识别登录元素并进行登录

        Args:
            url: 登录页面URL
            username: 用户名
            password: 密码
            captcha_code: 验证码(如果需要)
            use_openai: 是否使用OpenAI API进行识别，默认为True

        Returns:
            bool: 登录是否成功
        """
        try:
            # 导航到登录页面
            logger.info(f"正在访问登录页面并使用AI识别登录元素: {url}")
            response = await self.page.goto(url, wait_until="networkidle")

            if not response:
                logger.error(f"无法加载登录页面: {url}")
                return False

            # 等待页面完全加载
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)  # 给页面额外的加载时间

            # 使用AI识别登录元素
            login_elements = await self._ai_identify_login_elements(use_openai)

            # 检查是否找到了必要的登录元素
            if not login_elements or not login_elements.get("username_xpath") or not login_elements.get(
                    "password_xpath"):
                logger.error("AI无法识别用户名或密码输入框")
                logger.info("尝试回退到常规登录方法")
                return await self.login_with_credentials(url, username, password, captcha_code)

            # 填写用户名
            if login_elements.get("username_xpath"):
                try:
                    username_element = await self.page.wait_for_selector(login_elements["username_xpath"], timeout=5000)
                    if username_element:
                        await username_element.click()
                        await username_element.fill("")  # 先清空
                        await username_element.type(username, delay=100)
                        logger.info(f"已填写用户名: {username}")
                    else:
                        logger.error("未找到用户名输入框")
                        return False
                except Exception as e:
                    logger.error(f"填写用户名时出错: {str(e)}")
                    return False

            # 填写密码
            if login_elements.get("password_xpath"):
                try:
                    password_element = await self.page.wait_for_selector(login_elements["password_xpath"], timeout=5000)
                    if password_element:
                        await password_element.click()
                        await password_element.fill("")  # 先清空
                        await password_element.type(password, delay=100)
                        logger.info("已填写密码")
                    else:
                        logger.error("未找到密码输入框")
                        return False
                except Exception as e:
                    logger.error(f"填写密码时出错: {str(e)}")
                    return False

            # 填写验证码(如果有)
            if captcha_code and login_elements.get("captcha_xpath"):
                try:
                    captcha_element = await self.page.wait_for_selector(login_elements["captcha_xpath"], timeout=5000)
                    if captcha_element:
                        await captcha_element.click()
                        await captcha_element.fill("")  # 先清空
                        await captcha_element.type(captcha_code, delay=100)
                        logger.info(f"已填写验证码: {captcha_code}")
                except Exception as e:
                    logger.warning(f"填写验证码时出错: {str(e)}")

            # 点击登录按钮
            if login_elements.get("login_button_xpath"):
                try:
                    login_button = await self.page.wait_for_selector(login_elements["login_button_xpath"], timeout=5000)
                    if login_button:
                        logger.info("正在点击AI识别的登录按钮")
                        await login_button.click()
                    else:
                        logger.error("未找到登录按钮")
                        return False
                except Exception as e:
                    logger.error(f"点击登录按钮时出错: {str(e)}")
                    return False
            else:
                logger.error("AI未能识别登录按钮")
                return False

            # 等待网络请求完成
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                logger.warning(f"等待网络请求完成时出错: {str(e)}")

            # 等待一段时间以确保登录结果可用
            await asyncio.sleep(3)

            # 严格检查登录是否成功
            current_url = self.page.url
            logger.info(f"登录后的URL: {current_url}")

            # 检查URL变化
            if current_url != url and (
                    "account" in current_url or "dashboard" in current_url or "home" in current_url or "welcome" in current_url or "user" in current_url):
                logger.info("登录成功(URL变化)")
                return True

            # 检查页面内容
            page_content = await self.page.content()

            # 检查登出元素
            logout_texts = ["退出", "登出", "注销", "logout", "sign out", "signout"]
            if any(text in page_content.lower() for text in logout_texts):
                logger.info("登录成功(检测到退出登录元素)")
                return True

            # 检查可能的登录失败信息
            failure_texts = ["密码错误", "用户名错误", "登录失败", "账号或密码不正确"]
            if any(text in page_content.lower() for text in failure_texts):
                logger.error("登录失败(检测到失败消息)")
                return False

            # 检查是否仍显示登录表单
            try:
                login_form_still_visible = await self.page.query_selector(login_elements["username_xpath"]) is not None
                if login_form_still_visible:
                    logger.error("登录可能失败(登录表单仍然可见)")
                    return False
            except Exception:
                pass

            # 如果页面内容看起来包含个人信息，认为登录成功
            personal_texts = ["个人中心", "我的账户", "用户名", "profile", "account", "my center", "我的", "用户中心"]
            if any(text in page_content.lower() for text in personal_texts):
                logger.info("登录成功(检测到个人信息)")
                return True

            # 检查是否登录按钮仍然存在
            try:
                login_button_still_exists = await self.page.query_selector(
                    login_elements["login_button_xpath"]) is not None
                if login_button_still_exists:
                    logger.error("登录可能失败(登录按钮仍然存在)")
                    return False
            except Exception:
                pass

            # 如果没有明确的失败迹象，假设成功
            logger.warning("无法确定登录状态，假设为成功")
            return True

        except Exception as e:
            logger.error(f"使用AI登录过程中出错: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    async def explore_page(self, url: str, max_depth: int = 2, device_type: str = "desktop") -> Dict[str, Any]:
        """
        加载页面并收集页面信息，但不再探索页面上的可点击元素

        Args:
            url (str): 要访问的页面URL
            max_depth (int): 已不再使用的参数，保留向后兼容性
            device_type (str): 设备类型，可选值为 "desktop", "mobile", "tablet"

        Returns:
            Dict[str, Any]: 页面信息
        """
        try:
            # 清除之前的访问记录
            self.visited_urls = set()
            self.page_data = {}
            self.interactive_elements = {}
            self.click_paths = []
            self.explored_urls = set()
            self.results = []

            # 检查URL是否有效
            if not is_valid_url(url):
                logger.error(f"URL无效: {url}")
                return {"error": f"URL无效: {url}", "success": False}

            # 导航到页面
            logger.info(f"正在访问页面: {url}")
            response = await self.page.goto(url, wait_until="networkidle")

            if not response:
                logger.error(f"无法加载页面: {url}")
                return {"error": f"无法加载页面: {url}", "success": False}

            # 等待页面完全加载
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)  # 给页面额外的加载时间

            # 收集页面信息
            logger.info("收集当前页面信息")
            page_info = await self._collect_page_info()

            # 记录结果
            self.visited_urls.add(url)
            self.page_data[url] = page_info

            # 返回结果
            result = {
                "url": url,
                "page_info": page_info,
                "success": True
            }

            return result

        except Exception as e:
            logger.error(f"探索页面时出错: {str(e)}")
            traceback.print_exc()
            return {"error": str(e), "success": False}

    async def _collect_page_info(self) -> Dict[str, Any]:
        """
        收集当前页面的关键信息用于AI生成测试用例，优化数据质量而非限制数量

        Returns:
            Dict[str, Any]: 页面信息字典
        """
        try:
            url = self.page.url
            title = await self.page.title()

            # 创建结果字典
            result = {
                "url": url,
                "title": title,
                "timestamp": time.time()
            }

            # 使用一个共同的错误处理函数收集各种页面元素信息
            async def safe_evaluate(js_code, default_value=None, key_name=None):
                try:
                    value = await self.page.evaluate(js_code)
                    if key_name:
                        result[key_name] = value
                    return value
                except Exception as e:
                    logger.warning(f"获取页面信息时出错 ({key_name}): {str(e)}")
                    if key_name:
                        result[key_name] = default_value
                    return default_value

            # 获取页面结构概览（提供整体结构而不是详细内容）
            await safe_evaluate("""() => {
                // 获取页面的主要结构
                const structure = {
                    hasHeader: !!document.querySelector('header'),
                    hasFooter: !!document.querySelector('footer'),
                    hasNavigation: !!document.querySelector('nav'),
                    hasMainContent: !!document.querySelector('main'),
                    hasSidebar: !!document.querySelector('aside'),
                    hasForms: document.forms.length > 0,
                    formCount: document.forms.length,
                    linkCount: document.querySelectorAll('a').length,
                    buttonCount: document.querySelectorAll('button, input[type="button"], input[type="submit"]').length,
                    inputCount: document.querySelectorAll('input:not([type="button"]):not([type="submit"]), textarea, select').length,
                    imageCount: document.querySelectorAll('img').length,
                    tableCount: document.querySelectorAll('table').length
                };
                return structure;
            }""", {}, "page_structure")

            # 获取重要的meta标签（减少不重要的元数据）
            await safe_evaluate("""() => {
                const importantMeta = {};
                const importantMetaNames = ['description', 'keywords', 'viewport', 'author', 'og:title', 'og:description'];
                document.querySelectorAll('meta').forEach(meta => {
                    const name = meta.name || meta.property;
                    if (name && importantMetaNames.includes(name)) {
                        importantMeta[name] = meta.content;
                    }
                });
                return importantMeta;
            }""", {}, "meta")

            # 分析并提取页面主要功能而不是所有元素
            await safe_evaluate("""() => {
                // 分析页面主要功能块
                const functionalAreas = [];

                // 识别页面上的主要功能区域和操作
                const addFunctionalArea = (element, type, importance = 'medium') => {
                    if (!element) return;

                    // 检查是否已包含此元素
                    const elementRect = element.getBoundingClientRect();
                    if (elementRect.width === 0 || elementRect.height === 0) return;

                    // 计算元素可见性和位置得分
                    const viewportHeight = window.innerHeight;
                    const viewportWidth = window.innerWidth;
                    const centerY = viewportHeight / 2;
                    const centerX = viewportWidth / 2;
                    const elementCenterY = elementRect.top + elementRect.height / 2;
                    const elementCenterX = elementRect.left + elementRect.width / 2;

                    // 计算到视口中心的距离（归一化）
                    const distanceToCenter = Math.sqrt(
                        Math.pow((elementCenterX - centerX) / viewportWidth, 2) +
                        Math.pow((elementCenterY - centerY) / viewportHeight, 2)
                    );

                    // 计算元素大小得分
                    const sizeScore = (elementRect.width * elementRect.height) / (viewportWidth * viewportHeight);

                    // 根据元素包含的交互元素计算功能重要性
                    const interactiveElements = element.querySelectorAll('button, a, input, select, textarea');
                    const interactivityScore = interactiveElements.length;

                    // 总得分 = 位置得分 + 大小得分 + 交互元素得分
                    const totalScore = (1 - distanceToCenter) * 0.4 + sizeScore * 0.3 + Math.min(interactivityScore * 0.05, 0.3);

                    // 根据得分确定重要性
                    let calculatedImportance = 'low';
                    if (totalScore > 0.6) calculatedImportance = 'high';
                    else if (totalScore > 0.3) calculatedImportance = 'medium';

                    const finalImportance = importance === 'high' ? 'high' : calculatedImportance;

                    // 提取元素的关键信息
                    functionalAreas.push({
                        type,
                        tagName: element.tagName.toLowerCase(),
                        id: element.id,
                        className: element.className,
                        text: element.textContent.trim().substring(0, 100),
                        importance: finalImportance,
                        interactiveElementCount: interactiveElements.length,
                        position: {
                            top: Math.round(elementRect.top),
                            left: Math.round(elementRect.left),
                            width: Math.round(elementRect.width),
                            height: Math.round(elementRect.height)
                        }
                    });
                };

                // 识别主要内容区域
                const mainContent = document.querySelector('main') ||
                                    document.querySelector('article') ||
                                    document.querySelector('#content') ||
                                    document.querySelector('.content');
                if (mainContent) {
                    addFunctionalArea(mainContent, 'main_content', 'high');
                }

                // 识别表单（高优先级功能区域）
                document.querySelectorAll('form').forEach(form => {
                    addFunctionalArea(form, 'form', 'high');
                });

                // 识别可能的功能卡片/面板
                ['section', '.card', '.panel', '.box', '.container', '.module', '[role="region"]'].forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        // 仅添加包含交互元素的区域
                        if (el.querySelectorAll('button, a, input, select, textarea').length > 0) {
                            addFunctionalArea(el, 'functional_module');
                        }
                    });
                });

                // 根据重要性排序
                const importanceScores = { 'high': 3, 'medium': 2, 'low': 1 };
                functionalAreas.sort((a, b) => importanceScores[b.importance] - importanceScores[a.importance]);

                return functionalAreas;
            }""", [], "functional_areas")

            # 智能分析表单（关注关键属性而非所有属性）
            await safe_evaluate("""() => {
                return Array.from(document.forms).map(form => {
                    // 分析表单的用途
                    const formPurpose = (() => {
                        const action = form.action.toLowerCase();
                        const id = (form.id || '').toLowerCase();
                        const className = (form.className || '').toLowerCase();
                        const buttonText = Array.from(form.querySelectorAll('button, input[type="submit"]'))
                            .map(el => el.textContent || el.value || '').join(' ').toLowerCase();

                        if (action.includes('login') || id.includes('login') || className.includes('login') ||
                            buttonText.includes('login') || buttonText.includes('sign in') || buttonText.includes('登录')) {
                            return 'login';
                        } else if (action.includes('register') || id.includes('register') || className.includes('register') ||
                                 buttonText.includes('register') || buttonText.includes('sign up') || buttonText.includes('注册')) {
                            return 'registration';
                        } else if (action.includes('search') || id.includes('search') || className.includes('search') ||
                                 buttonText.includes('search') || buttonText.includes('搜索')) {
                            return 'search';
                        } else if (action.includes('contact') || id.includes('contact') || className.includes('contact') ||
                                 buttonText.includes('contact') || buttonText.includes('send') || buttonText.includes('联系')) {
                            return 'contact';
                        } else if (form.querySelector('input[name="password"]') || form.querySelector('input[type="password"]')) {
                            return 'authentication';
                        } else {
                            return 'data_entry';
                        }
                    })();

                    // 分析表单的关键字段
                    const formFields = Array.from(form.elements)
                        .filter(el => el.tagName !== 'BUTTON' && el.type !== 'submit' && el.type !== 'reset' && el.type !== 'button')
                        .map(el => {
                            // 确定字段类型和用途
                            const fieldPurpose = (() => {
                                const name = (el.name || '').toLowerCase();
                                const id = (el.id || '').toLowerCase();
                                const placeholder = (el.placeholder || '').toLowerCase();
                                const label = el.labels && el.labels.length > 0
                                    ? el.labels[0].textContent.toLowerCase()
                                    : '';

                                if (el.type === 'password') return 'password';
                                if (el.required) return 'required_field';
                                if (name.includes('email') || id.includes('email') || placeholder.includes('email') || label.includes('email')) return 'email';
                                if (name.includes('name') || id.includes('name') || placeholder.includes('name') || label.includes('name')) return 'name';
                                if (name.includes('phone') || id.includes('phone') || placeholder.includes('phone') || label.includes('phone')) return 'phone';
                                if (name.includes('address') || id.includes('address') || placeholder.includes('address') || label.includes('address')) return 'address';
                                if (name.includes('date') || id.includes('date') || placeholder.includes('date') || label.includes('date')) return 'date';
                                if (el.type === 'checkbox') return 'option';
                                if (el.type === 'radio') return 'selection';
                                if (el.tagName === 'SELECT') return 'dropdown';
                                if (el.tagName === 'TEXTAREA') return 'text_area';

                                return 'text_field';
                            })();

                            return {
                                type: el.type || el.tagName.toLowerCase(),
                                name: el.name,
                                id: el.id,
                                placeholder: el.placeholder,
                                required: el.required,
                                disabled: el.disabled,
                                fieldPurpose: fieldPurpose
                            };
                        });

                    return {
                        id: form.id,
                        action: form.action,
                        method: form.method,
                        purpose: formPurpose,
                        formFields: formFields
                    };
                });
            }""", [], "forms")

            # 提取页面关键交互元素（按钮、链接等）
            await safe_evaluate("""() => {
                // 分析页面交互元素的结构和目的
                const getElementPurpose = (el) => {
                    const text = (el.textContent || el.value || '').trim().toLowerCase();
                    const classes = (el.className || '').toLowerCase();
                    const id = (el.id || '').toLowerCase();

                    // 根据文本和类名推断按钮目的
                    if (text.includes('login') || text.includes('sign in') || text.includes('登录')) return 'login';
                    if (text.includes('register') || text.includes('sign up') || text.includes('注册')) return 'registration';
                    if (text.includes('submit') || text.includes('save') || text.includes('提交') || text.includes('保存')) return 'submission';
                    if (text.includes('search') || text.includes('搜索')) return 'search';
                    if (text.includes('cancel') || text.includes('close') || text.includes('取消') || text.includes('关闭')) return 'cancellation';
                    if (text.includes('delete') || text.includes('remove') || text.includes('删除') || text.includes('移除')) return 'deletion';
                    if (text.includes('edit') || text.includes('modify') || text.includes('编辑') || text.includes('修改')) return 'editing';
                    if (text.includes('add') || text.includes('create') || text.includes('new') || text.includes('添加') || text.includes('创建')) return 'creation';
                    if (text.includes('view') || text.includes('show') || text.includes('查看') || text.includes('显示')) return 'viewing';
                    if (text.includes('next') || text.includes('continue') || text.includes('下一步') || text.includes('继续')) return 'navigation_forward';
                    if (text.includes('previous') || text.includes('back') || text.includes('上一步') || text.includes('返回')) return 'navigation_backward';

                    // 根据类名推断
                    if (classes.includes('btn-primary') || classes.includes('primary-button')) return 'primary_action';
                    if (classes.includes('btn-secondary') || classes.includes('secondary-button')) return 'secondary_action';
                    if (classes.includes('btn-danger') || classes.includes('danger-button')) return 'danger_action';
                    if (classes.includes('btn-warning') || classes.includes('warning-button')) return 'warning_action';
                    if (classes.includes('btn-success') || classes.includes('success-button')) return 'success_action';

                    // 默认目的
                    return 'interaction';
                };

                // 获取重要的按钮
                const importantButtons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"]'))
                    .filter(btn => {
                        // 过滤掉隐藏和禁用的按钮
                        return window.getComputedStyle(btn).display !== 'none' &&
                               window.getComputedStyle(btn).visibility !== 'hidden' &&
                               !btn.disabled;
                    })
                    .map(btn => {
                        return {
                            text: (btn.textContent || btn.value || '').trim(),
                            type: btn.type,
                            purpose: getElementPurpose(btn),
                            isFormSubmit: btn.type === 'submit',
                            isDisabled: btn.disabled,
                            isVisible: true,
                            position: (() => {
                                const rect = btn.getBoundingClientRect();
                                return {
                                    top: Math.round(rect.top),
                                    left: Math.round(rect.left)
                                };
                            })()
                        };
                    });

                // 获取重要的链接
                const importantLinks = Array.from(document.querySelectorAll('a'))
                    .filter(link => {
                        // 过滤掉空链接和隐藏链接
                        const hasText = (link.textContent || '').trim().length > 0;
                        const isVisible = window.getComputedStyle(link).display !== 'none' &&
                                          window.getComputedStyle(link).visibility !== 'hidden';
                        return hasText && isVisible;
                    })
                    .map(link => {
                        return {
                            text: link.textContent.trim(),
                            href: link.href,
                            purpose: getElementPurpose(link),
                            isExternal: link.hostname !== window.location.hostname,
                            position: (() => {
                                const rect = link.getBoundingClientRect();
                                return {
                                    top: Math.round(rect.top),
                                    left: Math.round(rect.left)
                                };
                            })()
                        };
                    });

                return {
                    buttons: importantButtons,
                    links: importantLinks
                };
            }""", {}, "interactive_elements")

            # 提取页面内容语义结构（而不是完整文本）
            await safe_evaluate("""() => {
                // 提取页面的语义结构
                const extractSemanticStructure = () => {
                    const structure = [];

                    // 提取标题层次结构
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
                    const headingStructure = headings.map(heading => {
                        return {
                            level: parseInt(heading.tagName.substring(1)),
                            text: heading.textContent.trim()
                        };
                    });

                    if (headingStructure.length > 0) {
                        structure.push({
                            type: 'heading_hierarchy',
                            content: headingStructure
                        });
                    }

                    // 提取列表结构
                    const lists = Array.from(document.querySelectorAll('ul, ol'));
                    const listStructure = lists.map(list => {
                        const items = Array.from(list.querySelectorAll('li')).map(li => li.textContent.trim());
                        return {
                            type: list.tagName.toLowerCase(),
                            items: items
                        };
                    });

                    if (listStructure.length > 0) {
                        structure.push({
                            type: 'lists',
                            content: listStructure
                        });
                    }

                    // 提取主要段落结构
                    const mainElement = document.querySelector('main') ||
                                       document.querySelector('article') ||
                                       document.querySelector('#content') ||
                                       document.querySelector('.content');

                    if (mainElement) {
                        const paragraphs = Array.from(mainElement.querySelectorAll('p'))
                            .filter(p => p.textContent.trim().length > 0)
                            .map(p => {
                                // 智能提取段落摘要，保留关键信息
                                const text = p.textContent.trim();
                                return text.length > 100 ? text.substring(0, 100) + '...' : text;
                            });

                        if (paragraphs.length > 0) {
                            structure.push({
                                type: 'paragraphs',
                                content: paragraphs
                            });
                        }
                    }

                    return structure;
                };

                return extractSemanticStructure();
            }""", [], "content_structure")

            # 提取页面重要的错误信息和提示
            await safe_evaluate("""() => {
                return Array.from(document.querySelectorAll('.error, .alert, .message, .notification, [role="alert"], [aria-live]'))
                    .filter(el => el.textContent.trim().length > 0)
                    .map(el => {
                        // 确定消息类型
                        const classes = (el.className || '').toLowerCase();
                        let messageType = 'info';
                        if (classes.includes('error') || classes.includes('danger')) messageType = 'error';
                        else if (classes.includes('warn')) messageType = 'warning';
                        else if (classes.includes('success')) messageType = 'success';

                        return {
                            type: messageType,
                            text: el.textContent.trim()
                        };
                    });
            }""", [], "messages")

            # 提取关键输入控件的特征（较优先）
            await safe_evaluate("""() => {
                return Array.from(document.querySelectorAll('input:not([type="button"]):not([type="submit"]), textarea, select'))
                    .filter(el => window.getComputedStyle(el).display !== 'none')
                    .map(el => {
                        // 确定字段的用途
                        const fieldPurpose = (() => {
                            const name = (el.name || '').toLowerCase();
                            const id = (el.id || '').toLowerCase();
                            const placeholder = (el.placeholder || '').toLowerCase();

                            if (el.type === 'password') return 'password';
                            if (name.includes('email') || id.includes('email') || placeholder.includes('email')) return 'email';
                            if (name.includes('name') || id.includes('name') || placeholder.includes('name')) return 'name';
                            if (name.includes('phone') || id.includes('phone') || placeholder.includes('phone')) return 'phone';
                            if (name.includes('search') || id.includes('search') || placeholder.includes('search')) return 'search';
                            if (el.type === 'date') return 'date';
                            if (el.type === 'checkbox') return 'checkbox';
                            if (el.type === 'radio') return 'radio';
                            if (el.tagName === 'SELECT') return 'dropdown';
                            if (el.tagName === 'TEXTAREA') return 'long_text';

                            return 'text';
                        })();

                        return {
                            type: el.type || el.tagName.toLowerCase(),
                            purpose: fieldPurpose,
                            name: el.name,
                            id: el.id,
                            placeholder: el.placeholder,
                            required: el.required,
                            disabled: el.disabled,
                            readOnly: el.readOnly
                        };
                    });
            }""", [], "input_controls")

            return result

        except Exception as e:
            logger.error(f"收集页面信息时出错: {str(e)}")
            traceback.print_exc()
            # 返回最小化的结果
            return {
                "url": self.page.url,
                "title": "Error collecting page info",
                "error": str(e),
                "timestamp": time.time()
            }


    async def _ai_identify_login_elements(self, use_openai: bool = True) -> Dict[str, str]:
        """
        使用AI识别页面上的登录表单元素

        Args:
            use_openai (bool): 是否使用OpenAI API进行识别，默认为True

        Returns:
            Dict[str, str]: 包含登录元素的xpath字典
        """
        try:
            logger.info("使用AI技术识别登录表单元素...")

            # 如果不使用OpenAI，则使用启发式规则识别
            if not use_openai:
                logger.info("使用启发式规则识别登录元素")
                return await self._identify_login_elements_heuristic()

            # 使用OpenAI API识别
            # 获取页面HTML内容
            html_content = await self.page.content()

            # 截取HTML内容（避免过大的内容影响API请求）
            html_preview = html_content[:200000] if len(html_content) > 200000 else html_content
            if len(html_content) > 200000:
                logger.warning(f"页面HTML内容过大，已截取前200000字符用于AI分析 (原始大小: {len(html_content)}字符)")

            # 构建AI提示词
            prompt = f"""你是一个资深的UI自动化测试工程师，你需要根据我给的html元素，找出登录用户名，密码，验证码，登录按钮的xpath，如果一个xpath对应多个元素，你需要精确到哪个元素，只需要输出json结果就行，如果没找到的话，对应的字段值设置为空就行，你只需要输出json结果，输出json格式为这样的{{
              "username_xpath": "//input[@placeholder='用户名']",
              "password_xpath": "//input[@placeholder='密码']",
              "captcha_xpath": "//input[@placeholder='验证码']",
              "login_button_xpath": "//button[@type='button' and contains(@class, 'ant-btn-primary')]"
            }}
            
            以下是页面的HTML内容:
            {html_preview}
            """

            # 调用OpenAI API
            try:
                import openai

                # 检查API密钥是否配置
                if not OPENAI_API_KEY:
                    logger.error("未配置OpenAI API密钥，无法使用AI识别登录元素")
                    return {
                        "username_xpath": "",
                        "password_xpath": "",
                        "captcha_xpath": "",
                        "login_button_xpath": ""
                    }

                # 记录API调用信息
                logger.info(f"调用OpenAI API (模型: {OPENAI_MODEL}, 接口: {OPENAI_BASE_URL})")

                # 配置OpenAI客户端
                client = openai.Client(
                    api_key=OPENAI_API_KEY,
                    base_url=OPENAI_BASE_URL
                )

                # 发送请求
                response = client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system",
                         "content": "你是一个专业的UI测试自动化工程师，擅长分析HTML并找出登录表单元素。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=OPENAI_TEMPERATURE,
                    max_tokens=1000
                )

                # 提取JSON响应
                result_text = response.choices[0].message.content
                import json
                import re

                # 尝试从响应中提取JSON部分
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        login_elements = json.loads(json_str)
                        # 验证返回的JSON结构是否符合预期
                        expected_keys = ["username_xpath", "password_xpath", "captcha_xpath", "login_button_xpath"]
                        for key in expected_keys:
                            if key not in login_elements:
                                login_elements[key] = ""

                        logger.info(f"AI成功识别登录元素:")
                        for key, value in login_elements.items():
                            if value:
                                logger.info(f"- {key}: {value}")
                            else:
                                logger.info(f"- {key}: 未找到")

                        return login_elements
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {str(e)}")
                        logger.error(f"原始JSON字符串: {json_str}")
                        return {
                            "username_xpath": "",
                            "password_xpath": "",
                            "captcha_xpath": "",
                            "login_button_xpath": ""
                        }
                else:
                    logger.warning("无法从AI响应中提取JSON数据")
                    logger.debug(f"AI响应内容: {result_text[:200]}...")
                    return {
                        "username_xpath": "",
                        "password_xpath": "",
                        "captcha_xpath": "",
                        "login_button_xpath": ""
                    }

            except ImportError:
                logger.error("缺少openai库，无法使用AI识别登录元素")
                return {
                    "username_xpath": "",
                    "password_xpath": "",
                    "captcha_xpath": "",
                    "login_button_xpath": ""
                }
            except Exception as e:
                logger.error(f"调用AI服务时出错: {str(e)}")
                logger.error(traceback.format_exc())
                return {
                    "username_xpath": "",
                    "password_xpath": "",
                    "captcha_xpath": "",
                    "login_button_xpath": ""
                }

        except Exception as e:
            logger.error(f"AI识别登录元素时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "username_xpath": "",
                "password_xpath": "",
                "captcha_xpath": "",
                "login_button_xpath": ""
            }

    async def _identify_login_elements_heuristic(self) -> Dict[str, str]:
        """
        使用启发式规则识别登录表单元素，无需调用OpenAI API

        Returns:
            Dict[str, str]: 包含登录元素的xpath字典
        """
        try:
            logger.info("使用启发式规则识别登录元素...")

            # 初始化结果字典
            login_elements = {
                "username_xpath": "",
                "password_xpath": "",
                "captcha_xpath": "",
                "login_button_xpath": ""
            }

            # 查找用户名输入框的常见xpath
            username_xpaths = [
                "//input[@type='text' and (contains(@placeholder, '用户') or contains(@placeholder, 'user') or contains(@placeholder, 'email') or contains(@placeholder, '账号') or contains(@placeholder, 'account'))]",
                "//input[@type='email']",
                "//input[@id='username' or @id='user' or @id='email' or @id='account']",
                "//input[@name='username' or @name='user' or @name='email' or @name='account']",
                "//input[@type='text' and ancestor::form]",  # 表单中的第一个文本输入框很可能是用户名
                "//input[contains(@class, 'username') or contains(@class, 'user') or contains(@class, 'account')]"
            ]

            # 查找密码输入框的常见xpath
            password_xpaths = [
                "//input[@type='password']",
                "//input[@id='password' or @id='pwd' or @id='pass']",
                "//input[@name='password' or @name='pwd' or @name='pass']",
                "//input[contains(@placeholder, '密码') or contains(@placeholder, 'password')]"
            ]

            # 查找验证码输入框的常见xpath
            captcha_xpaths = [
                "//input[contains(@placeholder, '验证码') or contains(@placeholder, 'captcha') or contains(@placeholder, 'verify')]",
                "//input[@id='captcha' or @id='verify-code' or @id='verification']",
                "//input[@name='captcha' or @name='verify-code' or @name='verification']",
                "//input[ancestor::div[img[contains(@src, 'captcha') or contains(@src, 'verify')]]]",
                "//input[contains(@class, 'captcha') or contains(@class, 'verify-code')]"
            ]

            # 查找登录按钮的常见xpath
            login_button_xpaths = [
                "//button[contains(text(), '登录') or contains(text(), '登 录') or contains(text(), 'Login') or contains(text(), 'Sign in')]",
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//a[contains(text(), '登录') or contains(text(), 'Login') or contains(text(), 'Sign in')]",
                "//button[contains(@class, 'login') or contains(@class, 'submit') or contains(@class, 'sign-in')]",
                "//input[@value='登录' or @value='Login' or @value='Sign in']",
                "//div[contains(@class, 'login') or contains(@class, 'submit')][not(ancestor::input) and not(ancestor::button)]"
            ]

            # 查找登录表单，优先查找表单内元素
            form_xpaths = [
                "//form[.//input[@type='password']]",  # 含有密码输入框的表单很可能是登录表单
                "//form[contains(@action, 'login') or contains(@action, 'auth') or contains(@action, 'sign-in')]",
                "//form[@id='login-form' or @id='loginForm' or contains(@class, 'login')]",
                "//div[contains(@class, 'login-form') or contains(@class, 'login-container')]"
            ]

            # 查找登录表单元素
            form_element = None
            for xpath in form_xpaths:
                try:
                    element = await self.page.query_selector(xpath)
                    if element:
                        form_element = element
                        logger.info(f"找到登录表单: {xpath}")
                        break
                except Exception as e:
                    logger.debug(f"查找登录表单时出错: {str(e)}")
                    continue

            # 在找到的表单内查找元素
            context = form_element if form_element else self.page

            # 查找用户名输入框
            for xpath in username_xpaths:
                try:
                    element = await context.query_selector(xpath)
                    if element and await element.is_visible():
                        login_elements["username_xpath"] = xpath
                        logger.info(f"找到用户名输入框: {xpath}")
                        break
                except Exception as e:
                    logger.debug(f"查找用户名输入框时出错: {str(e)}")
                    continue

            # 查找密码输入框
            for xpath in password_xpaths:
                try:
                    element = await context.query_selector(xpath)
                    if element and await element.is_visible():
                        login_elements["password_xpath"] = xpath
                        logger.info(f"找到密码输入框: {xpath}")
                        break
                except Exception as e:
                    logger.debug(f"查找密码输入框时出错: {str(e)}")
                    continue

            # 查找验证码输入框
            for xpath in captcha_xpaths:
                try:
                    element = await context.query_selector(xpath)
                    if element and await element.is_visible():
                        login_elements["captcha_xpath"] = xpath
                        logger.info(f"找到验证码输入框: {xpath}")
                        break
                except Exception as e:
                    logger.debug(f"查找验证码输入框时出错: {str(e)}")
                    continue

            # 查找登录按钮
            for xpath in login_button_xpaths:
                try:
                    element = await context.query_selector(xpath)
                    if element and await element.is_visible():
                        login_elements["login_button_xpath"] = xpath
                        logger.info(f"找到登录按钮: {xpath}")
                        break
                except Exception as e:
                    logger.debug(f"查找登录按钮时出错: {str(e)}")
                    continue

            return login_elements

        except Exception as e:
            logger.error(f"使用启发式规则识别登录元素时出错: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "username_xpath": "",
                "password_xpath": "",
                "captcha_xpath": "",
                "login_button_xpath": ""
            }
