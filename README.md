 # AITestCase
[English Version](doc/README_EN.md) | [中文版本](doc/README_CN.md)
A tool for generating test cases based on the current webpage and requirement documents.

## Features

- 📋 **Test Case Generation**: Automatically generate test cases based on the current page and requirement document content, solving the problem of poor quality test cases generated from a single requirement document.
- 🔐 **Multiple Login Methods**: Supports login with username/password and cookies.
- 📱 **Multi-Device Support**: Simulates desktop, mobile, and tablet devices.
- 📊 **Excel Export**: Supports exporting test cases to Excel format.
- 📝 **Requirement Association**: Automatically associates test cases with requirement documents.
- 🛠️ **Customizable**: Flexible configuration options to suit different project needs.

## Installation Steps

1. Ensure Python 3.8 or higher is installed.
2. Clone or download this repository.
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Install Playwright:
   ```
   playwright install
   ```

## Usage

### Basic Usage

```bash
# Basic usage
python main.py --url <website URL>

# Login with username and password
python main.py --url <website URL> --username <username> --password <password>

# Login with cookies
python main.py --url <website URL> --cookies "<cookie string>"

# Specify device type (desktop/mobile/tablet)
python main.py --url <website URL> --device <desktop|mobile|tablet>
```

### Cookie Login Support

This tool supports multiple cookie formats:

1. **Key-Value Format** (common in browser developer tools):
   ```
   cookie1=value1; cookie2=value2; JSESSIONID=123456789; auth_token=abcdefg
   ```

### Example

```bash
# Login with key-value format cookies
python main.py --url https://example.com --cookies "session=abc123; token=xyz789"
```

### Command Line Parameters

```
python main.py --url https://example.com --username user --password pass
```

### Use AI to Identify Login Elements

```
python main.py --url https://example.com --login-url https://example.com/login --username user --password pass --use-ai-login
```

This will use AI to automatically identify form elements on the login page, more accurately locating the login form than traditional methods.

View all available parameters:

```
python main.py --help
```

## Configuration Options

Configuration files are located in the `config/` directory, where you can modify the following settings:

- `settings.py`: General settings
- `user_agents.py`: User agent strings

## Correct Use of Cookie Login

Cookie strings can be in one of the following formats:

1. **Standard Key-Value**:
```
cookieName=cookieValue; otherCookie=otherValue
```

## Open Source License

   GPL License

## Troubleshooting

### Cookie Issue Troubleshooting

If you encounter cookie-related issues, try the following steps to troubleshoot:

1. **Check Cookie Format**: Ensure the cookie format is correct, preferably using the browser developer tools to export cookies
   ```bash
   # Copy cookies in Chrome browser
   1. Open Developer Tools (F12)
   2. Switch to the Application/Network tab
   3. Find the cookies or the cookie header in the request
   4. Copy the complete cookie string
   ```

2. **View Detailed Logs**: Modify `config/settings.py` to set the log level to DEBUG
   ```python
   # Set in config/settings.py
   LOG_LEVEL = "DEBUG"  # Options: DEBUG, INFO, WARNING, ERROR
   ```

3. **Try Other Login Methods**: If cookie login continues to fail, try username/password login
   ```bash
   python main.py --url https://example.com --username user --password pass
   ```

### View Browser Interface

If you need to see the browser operation process, use the `--show` parameter:

```bash
python main.py --url https://example.com --cookies "sessionid=abc123" --show true
```

This is particularly useful for debugging cookie and login issues, allowing you to observe the actual behavior and redirection of the browser.

## Documentation Links

- [Usage Guide](USAGE.md)

## WeChat Contact

<img src="doc/contact.jpg" alt="Contact QR Code" style="width: 30%; height: auto;">