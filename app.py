"""
=========================================
@Project ：AITestCase
@Date ：2023/04/07
@Author:Echoxiawan
@Comment:Web界面入口
=========================================
"""
import os
import tempfile
import asyncio
from flask import Flask, render_template, request, redirect, url_for, send_file, flash, jsonify, session
from werkzeug.utils import secure_filename
import sys
import main

# 从环境变量或配置文件获取端口
PORT = int(os.environ.get('APP_PORT', 5000))

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix="uploads_")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 限制

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 允许的文件类型
ALLOWED_EXTENSIONS = {'txt', 'md', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # 获取表单数据
    url = request.form.get('url', '')
    login_method = request.form.get('login_method', 'none')
    username = request.form.get('username', '') if login_method == 'credentials' else None
    password = request.form.get('password', '') if login_method == 'credentials' else None
    cookies = request.form.get('cookies', '') if login_method == 'cookies' else None
    use_ai_login = 'use_ai_login' in request.form
    show_browser = 'show_browser' in request.form
    include_old = 'include_old' in request.form
    
    # 处理需求文件上传
    requirement_files = []
    if 'requirements' in request.files:
        files = request.files.getlist('requirements')
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                requirement_files.append(filepath)
    
    # 保存参数到会话
    session['params'] = {
        'url': url,
        'login_method': login_method,
        'username': username,
        'password': password, 
        'cookies': cookies,
        'use_ai_login': use_ai_login,
        'show_browser': show_browser,
        'requirement_files': requirement_files,
        'include_old': include_old
    }
    
    # 调用异步处理函数
    try:
        return redirect(url_for('process'))
    except Exception as e:
        flash(f'发生错误: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/process')
def process():
    if 'params' not in session:
        flash('会话已过期，请重新提交', 'error')
        return redirect(url_for('index'))
    
    return render_template('processing.html')

@app.route('/start_processing', methods=['POST'])
def start_processing():
    params = session.get('params', {})
    if not params:
        return jsonify({'status': 'error', 'message': '会话已过期，请重新提交'})
    
    try:
        # 准备参数
        url = params.get('url', '')
        username = params.get('username')
        password = params.get('password')
        cookies = params.get('cookies')
        use_ai_login = params.get('use_ai_login', False)
        requirement_files = params.get('requirement_files', [])
        include_old = params.get('include_old', False)
        
        # 运行Web Explorer
        page_data = main.run_web_explorer_on_multiple_urls_sync(
            [url], 
            username=username, 
            password=password, 
            cookies=cookies
        )
        
        # 加载需求文档
        requirements = {}
        if requirement_files:
            requirements = main.load_multiple_requirements(requirement_files)
        
        # 生成测试用例
        test_cases = main.generate_test_cases(page_data, requirements, include_old)
        
        # 导出到Excel
        output_file = main.export_to_excel(
            test_cases, 
            [url], 
            requirement_files
        )
        
        # 保存结果路径到会话
        session['output_file'] = output_file
        
        return jsonify({'status': 'success', 'message': '测试用例生成成功！', 'output_file': output_file})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'处理过程中出错: {str(e)}'})

@app.route('/download')
def download():
    output_file = session.get('output_file')
    if not output_file or not os.path.exists(output_file):
        flash('文件不存在或已过期', 'error')
        return redirect(url_for('index'))
    
    return send_file(output_file, as_attachment=True)

@app.route('/api/generate', methods=['POST'])
async def api_generate():
    """API端点，允许通过API调用生成测试用例"""
    data = request.json
    
    try:
        url = data.get('url', '')
        username = data.get('username')
        password = data.get('password')
        cookies = data.get('cookies')
        use_ai_login = data.get('use_ai_login', False)
        
        # API不支持文件上传，但可以支持通过文本传递需求内容
        requirements_content = data.get('requirements_content', {})
        
        # 运行Web Explorer
        page_data = await main.run_web_explorer_on_multiple_urls(
            [url], 
            username=username, 
            password=password, 
            cookies=cookies
        )
        
        # 生成测试用例
        test_cases = main.generate_test_cases(page_data, requirements_content)
        
        # 导出到Excel
        output_file = main.export_to_excel(
            test_cases, 
            [url], 
            []
        )
        
        return jsonify({
            'status': 'success', 
            'message': '测试用例生成成功！',
            'test_cases': test_cases,
            'output_file': output_file
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'处理过程中出错: {str(e)}'})

# API别名，将'/api/test-cases'映射到'/api/generate'函数
@app.route('/api/test-cases', methods=['POST'])
async def api_test_cases():
    return await api_generate()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True) 