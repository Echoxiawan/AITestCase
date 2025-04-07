// 语言包
const translations = {
    'zh': {
        // 导航栏
        'nav_home': '首页',
        'nav_features': '功能',
        'nav_generate': '生成测试用例',
        
        // 欢迎部分
        'welcome_title': '智能测试用例生成',
        'welcome_description': '基于当前网页和需求文档智能生成高质量测试用例，提高测试效率，减少重复工作。',
        'start_generate': '开始生成',
        'learn_more': '了解更多',
        
        // 功能部分
        'features_title': '强大功能',
        'feature_1_title': '智能生成测试用例',
        'feature_1_desc': '基于网页内容和需求文档智能生成测试用例，提高质量和覆盖率。',
        'feature_2_title': '多种登录方式',
        'feature_2_desc': '支持用户名/密码或Cookies登录，灵活应对不同认证需求。',
        'feature_3_title': 'Excel导出',
        'feature_3_desc': '支持将测试用例导出为Excel格式，便于分享和管理。',
        'feature_4_title': '需求关联',
        'feature_4_desc': '自动关联测试用例与需求文档，确保测试覆盖全部功能。',
        'feature_5_title': 'Web界面',
        'feature_5_desc': '提供友好的Web界面，无需命令行即可轻松使用所有功能。',
        'feature_6_title': '可自定义',
        'feature_6_desc': '灵活的配置选项，适应不同项目需求。',
        
        // 表单部分
        'form_title': '生成测试用例',
        'config_title': '参数配置',
        'url_label': '网页URL',
        'url_placeholder': 'https://example.com',
        'url_help': '输入您要测试的网页URL',
        'login_method_label': '登录方式',
        'login_none': '无需登录',
        'login_credentials': '用户名和密码',
        'login_cookies': 'Cookies',
        'username_label': '用户名',
        'username_placeholder': '输入用户名',
        'password_label': '密码',
        'password_placeholder': '输入密码',
        'ai_login_label': '使用AI智能识别登录元素',
        'cookies_label': 'Cookies',
        'cookies_placeholder': '格式: cookie1=value1; cookie2=value2;',
        'cookies_help': '从浏览器开发者工具中复制Cookie值',
        'requirements_label': '需求文档（可选）',
        'drag_drop': '拖拽文件到此处或点击上传',
        'supported_formats': '支持的格式: .txt, .md, .docx, .pdf',
        'browse_files': '浏览文件',
        'include_old_label': '包含旧功能的测试用例',
        'show_browser_label': '显示浏览器操作过程（调试用）',
        'generate_button': '生成测试用例',
        
        // 命令行部分
        'cmd_title': '命令行使用示例',
        'cmd_header': '命令行参数示例',
        'cmd_help': '查看所有可用参数：',
        
        // 页脚
        'footer_copyright': '© 2023 AI测试用例生成器',
        'footer_tech': '基于Python和AI技术构建',
        'github_tooltip': '访问GitHub项目',
        
        // 语言选择
        'language': '语言',
        'lang_zh': '中文',
        'lang_en': 'English'
    },
    'en': {
        // Navigation
        'nav_home': 'Home',
        'nav_features': 'Features',
        'nav_generate': 'Generate Test Cases',
        
        // Welcome section
        'welcome_title': 'Intelligent Test Case Generation',
        'welcome_description': 'Intelligently generate high-quality test cases based on current web pages and requirement documents, improving testing efficiency and reducing repetitive work.',
        'start_generate': 'Start Generating',
        'learn_more': 'Learn More',
        
        // Features section
        'features_title': 'Powerful Features',
        'feature_1_title': 'Intelligent Test Case Generation',
        'feature_1_desc': 'Generate test cases based on web content and requirement documents, improving quality and coverage.',
        'feature_2_title': 'Multiple Login Methods',
        'feature_2_desc': 'Support for username/password or Cookies login, flexibly handling different authentication requirements.',
        'feature_3_title': 'Excel Export',
        'feature_3_desc': 'Support for exporting test cases to Excel format for easy sharing and management.',
        'feature_4_title': 'Requirement Association',
        'feature_4_desc': 'Automatically associate test cases with requirement documents to ensure complete coverage.',
        'feature_5_title': 'Web Interface',
        'feature_5_desc': 'Provides a friendly web interface, easily use all features without command line.',
        'feature_6_title': 'Customizable',
        'feature_6_desc': 'Flexible configuration options to adapt to different project requirements.',
        
        // Form section
        'form_title': 'Generate Test Cases',
        'config_title': 'Parameter Configuration',
        'url_label': 'Web URL',
        'url_placeholder': 'https://example.com',
        'url_help': 'Enter the web URL you want to test',
        'login_method_label': 'Login Method',
        'login_none': 'No Login Required',
        'login_credentials': 'Username and Password',
        'login_cookies': 'Cookies',
        'username_label': 'Username',
        'username_placeholder': 'Enter username',
        'password_label': 'Password',
        'password_placeholder': 'Enter password',
        'ai_login_label': 'Use AI to recognize login elements',
        'cookies_label': 'Cookies',
        'cookies_placeholder': 'Format: cookie1=value1; cookie2=value2;',
        'cookies_help': 'Copy Cookie value from browser developer tools',
        'requirements_label': 'Requirement Documents (Optional)',
        'drag_drop': 'Drag files here or click to upload',
        'supported_formats': 'Supported formats: .txt, .md, .docx, .pdf',
        'browse_files': 'Browse Files',
        'include_old_label': 'Include test cases for existing features',
        'show_browser_label': 'Show browser process (for debugging)',
        'generate_button': 'Generate Test Cases',
        
        // Command-line section
        'cmd_title': 'Command Line Examples',
        'cmd_header': 'Command Line Parameters',
        'cmd_help': 'View all available parameters:',
        
        // Footer
        'footer_copyright': '© 2023 AI Test Case Generator',
        'footer_tech': 'Built with Python and AI Technology',
        'github_tooltip': 'Visit GitHub Project',
        
        // Language selection
        'language': 'Language',
        'lang_zh': '中文',
        'lang_en': 'English'
    }
};

// 当前语言，默认为中文
let currentLang = 'zh';

// 初始化语言
function initLanguage() {
    // 从本地存储中获取语言设置
    const savedLang = localStorage.getItem('language');
    if (savedLang && translations[savedLang]) {
        currentLang = savedLang;
    }
    
    // 应用语言
    applyLanguage();
}

// 切换语言
function switchLanguage(lang) {
    if (translations[lang]) {
        currentLang = lang;
        localStorage.setItem('language', lang);
        applyLanguage();
    }
}

// 应用语言到页面元素
function applyLanguage() {
    const elements = document.querySelectorAll('[data-i18n], [data-i18n-title]');
    const langData = translations[currentLang];
    
    elements.forEach(el => {
        // 处理元素内容
        const key = el.getAttribute('data-i18n');
        if (key && langData[key]) {
            if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                if (el.getAttribute('placeholder')) {
                    el.setAttribute('placeholder', langData[key]);
                } else {
                    el.value = langData[key];
                }
            } else {
                el.textContent = langData[key];
            }
        }
        
        // 处理title属性
        const titleKey = el.getAttribute('data-i18n-title');
        if (titleKey && langData[titleKey]) {
            el.setAttribute('title', langData[titleKey]);
        }
    });
    
    // 更新选择器状态
    const langSelector = document.getElementById('language-selector');
    if (langSelector) {
        langSelector.value = currentLang;
    }
}

// 当DOM加载完成后初始化
document.addEventListener('DOMContentLoaded', initLanguage); 