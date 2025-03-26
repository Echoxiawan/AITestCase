"""
=========================================
@Project ：AITestCase
@Date ：2025/3/22 上午9:39
@Author:Echoxiawan
@Comment:测试用例生成模块，负责使用OpenAI分析页面数据并生成测试用例
=========================================
"""
import json
import time
from typing import Any, Dict, List, Optional, Union

import openai
from openai import OpenAI

from config.settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_BASE_URL
from utils.logger import get_logger, console

# 获取日志记录器
logger = get_logger(__name__)


class TestGenerator:
    """测试用例生成器，使用OpenAI生成测试用例"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化测试用例生成器
        
        Args:
            api_key (Optional[str]): OpenAI API密钥，如果为None则使用配置文件中的密钥
        """
        # 设置OpenAI API密钥
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("未提供OpenAI API密钥，请在配置文件或初始化时提供")

        # 初始化OpenAI客户端
        self.client = OpenAI(api_key=self.api_key, base_url=OPENAI_BASE_URL)
        logger.info("测试用例生成器初始化完成")
        
    def generate_test_cases_from_multiple_sources(
            self,
            pages_data: Dict[str, Dict[str, Any]],
            new_requirements: Optional[Dict[str, str]] = None,
            include_old_features: bool = False
    ) -> List[Dict[str, Any]]:
        """
        从多个页面和多个需求文档生成测试用例
        
        Args:
            pages_data (Dict[str, Dict[str, Any]]): 多个页面的探索数据，以URL为键
            new_requirements (Optional[Dict[str, str]]): 多个需求文档内容，以文件名为键
            include_old_features (bool): 是否包含旧功能的测试用例
            
        Returns:
            List[Dict[str, Any]]: 测试用例列表
        """
        try:
            # 日志记录
            logger.info(f"开始从 {len(pages_data)} 个页面和 {len(new_requirements) if new_requirements else 0} 个需求文档生成测试用例")
            
            # 准备提示信息
            prompt = self._build_multi_source_prompt(pages_data, new_requirements, include_old_features)
            
            # 调用OpenAI API
            console.print("[bold yellow]正在使用AI生成测试用例，这可能需要一些时间...[/bold yellow]")
            response = self._call_openai_api(prompt)
            
            # 解析响应并返回测试用例
            test_cases = self._parse_response(response)
            
            # 为每个测试用例添加来源标记
            for tc in test_cases:
                # 添加页面来源（如果可以从测试步骤中推断）
                page_url = None
                for url in pages_data.keys():
                    if tc.get("test_title", "") and url in tc.get("test_title", ""):
                        page_url = url
                        break
                    
                    steps = tc.get("test_steps", [])
                    if steps and isinstance(steps, list):
                        for step in steps:
                            if url in str(step):
                                page_url = url
                                break
                
                tc["page_source"] = page_url or "多页面"
                
                # 添加需求来源（如果可以从测试标题中推断）
                if new_requirements:
                    req_source = None
                    for req_name in new_requirements.keys():
                        if tc.get("test_title", "") and req_name in tc.get("test_title", ""):
                            req_source = req_name
                            break
                    
                    tc["requirement_source"] = req_source or "综合需求"
                
                # 添加测试区域
                if "test_area" not in tc:
                    tc["test_area"] = self._determine_test_area(tc)
            
            logger.info(f"已生成 {len(test_cases)} 个测试用例")
            return test_cases
            
        except Exception as e:
            logger.error(f"生成测试用例时出错: {str(e)}")
            return []

    def generate_test_cases(
            self,
            page_data: Dict[str, Any],
            new_requirements: Optional[str] = None,
            include_old_features: bool = False
    ) -> List[Dict[str, Any]]:
        """
        生成测试用例
        
        Args:
            page_data (Dict[str, Any]): 页面探索数据
            new_requirements (Optional[str]): 新需求文档
            include_old_features (bool): 是否包含旧功能的测试用例
            
        Returns:
            List[Dict[str, Any]]: 测试用例列表
        """
        try:
            # 准备提示信息
            prompt = self._build_prompt(page_data, new_requirements, include_old_features)

            # 调用OpenAI API
            response = self._call_openai_api(prompt)

            # 解析响应并返回测试用例
            test_cases = self._parse_response(response)
            
            # 添加测试区域
            for tc in test_cases:
                if "test_area" not in tc:
                    tc["test_area"] = self._determine_test_area(tc)

            logger.info(f"已生成 {len(test_cases)} 个测试用例")
            return test_cases

        except Exception as e:
            logger.error(f"生成测试用例时出错: {str(e)}")
            return []
    
    def _determine_test_area(self, test_case: Dict[str, Any]) -> str:
        """
        确定测试用例的测试区域
        
        Args:
            test_case (Dict[str, Any]): 测试用例
            
        Returns:
            str: 测试区域，"主内容区域"或"页面框架"
        """
        # 检查测试标题和步骤中是否包含导航相关词汇
        navigation_keywords = ["导航", "菜单", "导航栏", "menu", "navigation", "nav", "header", "footer", 
                              "页眉", "页脚", "侧边栏", "sidebar", "顶部栏", "底部栏", "链接跳转", "路由", 
                              "route", "标签页", "tab", "登录", "注册", "login", "register"]
        
        # 获取测试标题
        title = test_case.get("test_title", "") or test_case.get("title", "") or ""
        
        # 获取测试步骤
        steps = test_case.get("test_steps", []) or []
        if isinstance(steps, str):
            steps = [steps]
        
        # 检查标题中是否有导航关键词
        if any(keyword in title.lower() for keyword in navigation_keywords):
            return "页面框架"
        
        # 检查步骤中是否有导航关键词
        steps_text = " ".join(str(step) for step in steps)
        if any(keyword in steps_text.lower() for keyword in navigation_keywords):
            return "页面框架"
        
        # 默认为主内容区域
        return "主内容区域"
            
    def _build_multi_source_prompt(
            self,
            pages_data: Dict[str, Dict[str, Any]],
            new_requirements: Optional[Dict[str, str]] = None,
            include_old_features: bool = False
    ) -> str:
        """
        构建多源提示信息
        
        Args:
            pages_data (Dict[str, Dict[str, Any]]): 多个页面的探索数据，以URL为键
            new_requirements (Optional[Dict[str, str]]): 多个需求文档内容，以文件名为键
            include_old_features (bool): 是否包含旧功能的测试用例
            
        Returns:
            str: 提示信息
        """
        # 格式化页面数据
        pages_data_str = json.dumps(pages_data, ensure_ascii=False, indent=2)
        
        # 构建测试对象描述
        test_objects = []
        for url in pages_data.keys():
            test_objects.append(f"- {url}")
        
        test_objects_str = "\n".join(test_objects)
        
        # 构建需求描述
        requirements_str = ""
        if new_requirements:
            for doc_name, content in new_requirements.items():
                requirements_str += f"### {doc_name}\n{content}\n\n"
        
        # 确定测试类型
        test_types = ["功能测试", "UI测试"]
        if include_old_features:
            test_types.append("回归测试")
        
        test_types_str = "、".join(test_types)
        
        # 构建基础提示
        prompt = f"""
### **测试专家角色设定**
你是一位经验丰富的软件测试专家，擅长设计高效、全面的测试用例，确保软件质量和稳定性。你的任务是根据提供的页面数据和需求描述，生成详尽的测试用例。

### **测试输入信息**
**测试对象**：以下网页功能和UI界面
{test_objects_str}

**需求描述**：
{requirements_str or "基于页面探索数据生成测试用例，确保页面功能正常工作。"}

**测试类型**：{test_types_str}

**特殊要求**：
1. 重点关注页面的主内容区域，如内容展示区域、功能操作区域、表单等
2. 忽略导航栏、菜单、侧边栏、页眉、页脚等页面框架元素
3. 忽略路由行为、设置项等非核心功能
4. 包含正常路径测试、边界条件测试和异常情况测试
5. {"生成包含新需求和现有功能的完整测试用例集" if include_old_features else "仅针对新需求生成测试用例"}

### **页面探索数据**
```json
{pages_data_str}
```

### **测试用例格式要求**
请生成具有以下字段的JSON格式测试用例列表：
```json
[
  {{
    "test_id": "TC001",             // 测试用例唯一标识
    "test_title": "测试用例标题",     // 简要描述测试目标
    "priority": "高/中/低",          // 测试优先级
    "preconditions": "前置条件",     // 执行测试所需的系统状态和准备工作
    "test_steps": [                 // 详细的测试步骤列表
      "步骤1",
      "步骤2"
    ],
    "expected_results": [           // 每个步骤对应的预期结果列表
      "预期结果1",
      "预期结果2"
    ],
    "test_data": "测试数据",         // 测试中使用的输入数据
    "test_type": "功能测试/UI测试"    // 测试类型
  }}
]
```

### **测试用例设计要求**
1. 确保测试覆盖所有重要功能点
2. 测试步骤应详细、清晰，可直接执行
3. 预期结果应明确、可验证
4. 优先级分配应合理
5. 包含边界值测试和异常场景测试
6. 针对不同的页面功能设计不同的测试用例
7. 不要生成页面框架元素（导航栏、菜单等）的测试用例
8. 请直接返回JSON格式的测试用例列表，不要添加额外解释
"""

        return prompt

    def _build_prompt(
            self,
            page_data: Dict[str, Any],
            new_requirements: Optional[str] = None,
            include_old_features: bool = False
    ) -> str:
        """
        构建提示信息
        
        Args:
            page_data (Dict[str, Any]): 页面探索数据
            new_requirements (Optional[str]): 新需求文档
            include_old_features (bool): 是否包含旧功能的测试用例
            
        Returns:
            str: 提示信息
        """
        # 格式化页面数据
        page_data_str = json.dumps(page_data, ensure_ascii=False, indent=2)
        
        # 确定测试类型
        test_types = ["功能测试", "UI测试"]
        if include_old_features:
            test_types.append("回归测试")
        
        test_types_str = "、".join(test_types)
        
        # 构建测试对象描述
        url = page_data.get("url", "未知页面")
        
        # 构建基础提示
        prompt = f"""
### **测试专家角色设定**
你是一位经验丰富的软件测试专家，擅长设计高效、全面的测试用例，确保软件质量和稳定性。你的任务是根据提供的页面数据和需求描述，生成详尽的测试用例。

### **测试输入信息**
**测试对象**：{url}

**需求描述**：
{new_requirements or "基于页面探索数据生成测试用例，确保页面功能正常工作。"}

**测试类型**：{test_types_str}

**特殊要求**：
1. 重点关注页面的主内容区域，如内容展示区域、功能操作区域、表单等
2. 忽略导航栏、菜单、侧边栏、页眉、页脚等页面框架元素
3. 忽略路由行为、设置项等非核心功能
4. 包含正常路径测试、边界条件测试和异常情况测试
5. {"生成包含新需求和现有功能的完整测试用例集" if include_old_features else "仅针对新需求生成测试用例"}

### **页面探索数据**
```json
{page_data_str}
```

### **测试用例格式要求**
请生成具有以下字段的JSON格式测试用例列表：
```json
[
  {{
    "test_id": "TC001",             // 测试用例唯一标识
    "test_title": "测试用例标题",     // 简要描述测试目标
    "priority": "高/中/低",          // 测试优先级
    "preconditions": "前置条件",     // 执行测试所需的系统状态和准备工作
    "test_steps": [                 // 详细的测试步骤列表
      "步骤1",
      "步骤2"
    ],
    "expected_results": [           // 每个步骤对应的预期结果列表
      "预期结果1",
      "预期结果2"
    ],
    "test_data": "测试数据",         // 测试中使用的输入数据
    "test_type": "功能测试/UI测试"    // 测试类型
  }}
]
```

### **测试用例设计要求**
1. 确保测试覆盖所有重要功能点
2. 测试步骤应详细、清晰，可直接执行
3. 预期结果应明确、可验证
4. 优先级分配应合理
5. 包含边界值测试和异常场景测试
6. 不要生成页面框架元素（导航栏、菜单等）的测试用例
7. 请直接返回JSON格式的测试用例列表，不要添加额外解释
"""

        return prompt

    def _call_openai_api(self, prompt: str) -> str:
        """
        调用OpenAI API
        
        Args:
            prompt (str): 提示信息
            
        Returns:
            str: API响应
        """
        max_retries = 3
        retry_delay = 5  # 秒
        
        for attempt in range(max_retries):
            try:
                # 调用OpenAI Chat Completions API
                logger.info(f"请求OpenAI prompt： {prompt} ")
                response = self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": "你是一名专业的测试工程师，擅长编写清晰、全面的测试用例。遵循测试专家的角色设定，根据提供的信息生成高质量的测试用例。"},
                        {"role": "user", "content": prompt}
                    ],
                )
                print(response.model_dump_json())
                # 提取并返回响应文本
                if response.choices and len(response.choices) > 0:
                    return response.choices[0].message.content
                else:
                    raise ValueError("API返回的响应格式不正确")
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API调用失败，将在 {retry_delay} 秒后重试: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"API调用失败，已达到最大重试次数: {str(e)}")
                    raise
        
        return ""  # 这行代码永远不会被执行到，但是为了类型检查

    def _parse_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析API响应，提取测试用例
        
        Args:
            response (str): API响应
            
        Returns:
            List[Dict[str, Any]]: 测试用例列表
        """
        try:
            # 提取JSON部分
            json_str = self._extract_json(response)
            logger.info(f"成功解析返回结果： {json_str} ")
            if not json_str:
                logger.error("无法从API响应中提取有效的JSON")
                return []
                
            # 解析JSON
            test_cases = json.loads(json_str)
            
            # 验证结果
            if not isinstance(test_cases, list):
                logger.error("API返回的结果不是列表格式")
                return []
                
            logger.info(f"成功解析 {len(test_cases)} 个测试用例")
            return test_cases
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {str(e)}")
            logger.debug(f"原始响应: {response}")
            return []
        except Exception as e:
            logger.error(f"解析响应时出错: {str(e)}")
            return []

    def _extract_json(self, text: str) -> str:
        """
        从文本中提取JSON部分
        
        Args:
            text (str): 包含JSON的文本
            
        Returns:
            str: 提取的JSON字符串
        """
        # 查找JSON数组的开始和结束
        start_idx = text.find("[")
        end_idx = text.rfind("]")
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            return text[start_idx:end_idx+1]
            
        # 如果没有找到JSON数组，尝试查找JSON对象
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            return text[start_idx:end_idx+1]
            
        return ""
