from flask import Flask, request, jsonify, render_template
from services.resume_analyzer import ResumeAnalyzer
import os
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
analyzer = ResumeAnalyzer()

# 从环境变量获取 secret key，如果没有则生成随机值
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {
    # 图片格式
    'png', 'jpg', 'jpeg', 'webp', 'bmp',
    # 文档格式
    'pdf', 'doc', 'docx',
    # 文本格式
    'txt', 'rtf'
}

# 设置最大文件大小为 10MB
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 设置上传文件夹路径
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 设置其他安全相关配置
app.config['SESSION_COOKIE_SECURE'] = True  # 只在 HTTPS 下发送 cookie
app.config['SESSION_COOKIE_HTTPONLY'] = True  # 防止 JavaScript 访问 cookie
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=30)  # session 过期时间

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    return jsonify({'error': '文件大小超过限制（最大10MB）'}), 413

@app.route('/api/analyze', methods=['POST'])
def analyze_resume():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
            
        file = request.files['file']
        print(f"接收到文���: {file.filename}, 类型: {file.content_type}")
        
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
            
        if file and allowed_file(file.filename):
            # 生成唯一的文件名
            original_filename = secure_filename(file.filename)
            file_extension = os.path.splitext(original_filename)[1].lower()
            
            # 如果文件没有扩展名，根据MIME类型添加
            if not file_extension:
                mime_to_ext = {
                    'application/pdf': '.pdf',
                    'image/jpeg': '.jpg',
                    'image/png': '.png',
                    'image/webp': '.webp',
                    'image/bmp': '.bmp'
                }
                file_extension = mime_to_ext.get(file.content_type, '')
            
            # 使用时间戳生成唯一文件名
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"resume_{timestamp}{file_extension}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # 确保上传目录存在
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            print(f"保存文件到: {filepath}")
            file.save(filepath)
            
            # 检查文件是否成功保存
            if not os.path.exists(filepath):
                return jsonify({'error': '文件保存失败'}), 500
            
            print(f"文件大小: {os.path.getsize(filepath)} bytes")
            print(f"文件类型: {file.content_type}")
            print(f"文件扩展名: {file_extension}")
            
            # 分析简历
            resume = analyzer.analyze_resume_image(filepath)
            
            # 清理临时文件
            try:
                os.remove(filepath)
                print("临时文件已清理")
                # 同时清理可能存在的调试图片
                debug_path = filepath + '_debug.png'
                if os.path.exists(debug_path):
                    os.remove(debug_path)
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")
                pass
            
            return jsonify({
                'id': resume.id,
                'overall_score': resume.overall_score,
                'sections': {
                    name: {
                        'score': section.score,
                        'suggestions': section.suggestions,
                        'highlights': getattr(section, 'highlights', []),
                        'content': section.content
                    }
                    for name, section in resume.sections.items()
                }
            })
        
        return jsonify({'error': '不支持的文件类型'}), 400
    except Exception as e:
        print(f"处理过程出错: {str(e)}")
        return jsonify({'error': f'处理过程出错: {str(e)}'}), 500

# 添加测试路由
@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    print('服务器正在启动...')
    print('访问 http://127.0.0.1:5000/ 使用网页界面')
    app.run(debug=True) 