# AITestCase
[English ](README_EN.md) | [中文](README_CN.md)
根据网页当前页面和需求文档生成测试用例的工具

## 功能特点

- 📋 **测试用例生成**：基于当前页面和需求文档内容自动生成测试用例，解决单个需求文档生成测试用例质量较差的问题
- 🔐 **多种登录方式**：支持账号密码登录和Cookie登录
- 📱 **多设备支持**：支持模拟桌面、手机和平板设备
- 📊 **Excel导出**：支持将测试用例导出为Excel格式
- 📝 **需求关联**：自动将测试用例与需求文档关联
- 🛠️ **可定制化**：灵活的配置选项适应不同项目需求
- 📄 **多种文档格式**：支持纯文本、Markdown和Word(DOCX)等多种格式的需求文档

## 安装步骤

1. 确保已安装Python 3.8或更高版本
2. 克隆或下载本仓库
3. 安装依赖:
   ```
   pip install -r requirements.txt
   ```
4. 安装Playwright:
   ```
   playwright install
   ```

## 使用方法

### 基本用法

```bash
# 基本使用方法
python main.py --url <网站URL>

# 使用用户名密码登录
python main.py --url <网站URL> --username <用户名> --password <密码>

# 使用Cookie登录
python main.py --url <网站URL> --cookies "<Cookie字符串>"

# 指定设备类型（桌面/移动/平板）
python main.py --url <网站URL> --device <desktop|mobile|tablet>

# 使用需求文档（支持.txt、.md、.docx格式）
python main.py --url <网站URL> --requirements "需求1.docx,需求2.md,需求3.txt"
```

### Cookie登录支持

本工具支持多种Cookie格：

1. **键值对格式**（浏览器开发者工具中常见）:
   ```
   cookie1=value1; cookie2=value2; JSESSIONID=123456789; auth_token=abcdefg
   ```



### 示例

```bash
# 使用键值对格式的Cookie登录
python main.py --url https://example.com --cookies "session=abc123; token=xyz789"

```

### 命令行参数

```
python main.py --url https://example.com --username user --password pass
```

### 使用AI识别登录元素

```
python main.py --url https://example.com --login-url https://example.com/login --username user --password pass --use-ai-login
```

这将使用AI自动识别登录页面上的表单元素，比传统方法更准确地定位登录表单。

查看所有可用参数:

```
python main.py --help
```

## 配置选项

配置文件位于`config/`目录，可以修改以下设置:

- `settings.py`: 常规设置
- `user_agents.py`: 用户代理字符串

## 正确使用Cookie登录

Cookie字符串可以是以下格式之一：

1. **标准键值对**：
```
cookieName=cookieValue; otherCookie=otherValue
```


## 开源协议

   GPL License 

## 故障排查

### Cookie问题排查

如果遇到Cookie相关问题，可以尝试以下步骤进行排查：

1. **检查Cookie格式**：确保Cookie格式正确，最好使用浏览器开发者工具导出Cookie
   ```bash
   # Chrome浏览器中复制Cookie
   1. 打开开发者工具 (F12)
   2. 切换到Application/Network标签页
   3. 找到Cookie或请求中的Cookie头
   4. 复制完整的Cookie字符串
   ```

2. **查看详细日志**：修改config/settings.py，设置日志级别为DEBUG
   ```python
   # config/settings.py中设置
   LOG_LEVEL = "DEBUG"  # 可选值: DEBUG, INFO, WARNING, ERROR
   ```

3. **尝试其他登录方式**：如果Cookie登录持续失败，可以尝试用户名密码登录
   ```bash
   python main.py --url https://example.com --username user --password pass
   ```

### 查看浏览器界面

如果需要看到浏览器操作过程，可以使用`--show`参数：

```bash
python main.py --url https://example.com --cookies "sessionid=abc123" --show true
```

这对于调试Cookie和登录问题特别有用，可以观察浏览器的实际行为和重定向情况。 
## 文档链接

- [使用手册](USAGE.md)

## 联系方式

<img src="contact.jpg" alt="Contact QR Code" style="width: 30%; height: auto;">