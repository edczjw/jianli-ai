import cv2
import pytesseract
from PIL import Image
import numpy as np
from typing import Dict, List
from models.resume import Resume, ResumeSection
import datetime
import pdf2image
import PyPDF2
import tempfile
import os
import shutil

class ResumeAnalyzer:
    def __init__(self):
        # 扩展关键词列表，增加更多可能的标题格式
        self.keywords = {
            '基本信息': ['基本信息', '个人信息', '个人资料', '简历信息', '联系方式'],
            '教育背景': ['教育背景', '教育经历', '学习经历', '教育信息', '学历信息'],
            '工作经验': ['工作经验', '工作经历', '项目经验', '实习经历', '工作情况'],
            '技能特长': ['技能特长', '专业技能', '技术技能', '个人技能', '技能证书']
        }
        # 检查 poppler 是否已安装
        self._check_dependencies()
        # 设置 tesseract 路径
        if os.path.exists('/usr/local/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
        elif os.path.exists('/usr/bin/tesseract'):
            pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
    
    def _check_dependencies(self):
        """检查必要的依赖是否已安装"""
        # 检查 poppler
        if not shutil.which('pdftoppm'):
            print("警告: poppler 未安装，PDF处理可能无法正常工作")
            print("请安装 poppler:")
            print("Mac: brew install poppler")
            print("Linux: sudo apt-get install poppler-utils")
            print("Windows: 下载安装 poppler 并添加到系统路径")
    
    def analyze_resume_image(self, image_path: str) -> Resume:
        """分析上传的简历图片"""
        # 获取文件扩展名
        file_extension = os.path.splitext(image_path)[1].lower()
        
        # 使用OCR提取文本
        if file_extension == '.pdf':
            text = self._extract_text_from_pdf(image_path)
        else:
            text = self._extract_text_from_image(image_path)
            
        # 分段处理
        sections = self._split_sections(text)
        # 创建简历对象
        resume = Resume(
            id=str(hash(text)),
            upload_time=datetime.datetime.now(),
            file_path='',
            image_path=image_path,
            sections=sections,
            overall_score=0
        )
        # 进行分析
        resume.analyze()
        return resume
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """从PDF文件中提取文本"""
        try:
            print(f"开始处理PDF文件: {pdf_path}")
            if not os.path.exists(pdf_path):
                return f"找不到PDF文件: {pdf_path}"
            
            # 检查 poppler 是否可用
            if not shutil.which('pdftoppm'):
                print("Poppler未找到，检查环境变量PATH")
                return ("PDF处理失败: 缺少必要的依赖。\n"
                        "请安装 poppler:\n"
                        "Mac: brew install poppler\n"
                        "Linux: sudo apt-get install poppler-utils\n"
                        "Windows: 下载安装 poppler 并添加到系统路径")
            
            # 首先尝试直接提取文本
            with open(pdf_path, 'rb') as file:
                print("尝试直接提取PDF文本")
                pdf_reader = PyPDF2.PdfReader(file)
                text = ''
                for page in pdf_reader.pages:
                    text += page.extract_text()
                
                if text.strip():  # 如果成功提取到文本
                    print("成功直接提取PDF文本")
                    return text
            
            print("直接提取文本失败，尝试OCR方式")
            # 如果直接提取失败，转换为图片后OCR
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    print(f"创建临时目录: {temp_dir}")
                    # 将PDF转换为图片
                    images = pdf2image.convert_from_path(
                        pdf_path,
                        dpi=300,  # 提高分辨率
                        fmt='png',
                        output_folder=temp_dir,
                        poppler_path=self._get_poppler_path(),  # 添加poppler路径
                        paths_only=True
                    )
                    print(f"成功将PDF转换为{len(images)}张图片")
                    text = ''
                    
                    for image_path in images:
                        print(f"处理图片: {image_path}")
                        # 提取文本
                        page_text = self._extract_text_from_image(image_path)
                        text += page_text + '\n\n'
                    
                    if not text.strip():
                        print("OCR未能提取到文本")
                        return "无法从PDF中提取文本，请确保PDF文件包含可识别的文字内容"
                    
                    print("成功通过OCR提取文本")
                    return text
            except pdf2image.exceptions.PDFPageCountError:
                print("PDF页面计数错误")
                return "PDF文件可能已损坏或为空"
            except pdf2image.exceptions.PDFSyntaxError:
                print("PDF语法错误")
                return "PDF文件格式错误或已损坏"
                
        except Exception as e:
            print(f"PDF处理错误: {str(e)}")
            if "poppler" in str(e).lower():
                return ("PDF处理失败: 缺少必要的依赖。\n"
                        "请安装 poppler:\n"
                        "Mac: brew install poppler\n"
                        "Linux: sudo apt-get install poppler-utils\n"
                        "Windows: 下载安装 poppler 并添加到系统路径")
            return f"PDF处理失败，请确保：\n1. PDF文件未被加密\n2. PDF文件未被损坏\n3. PDF包含可识别的文字"
    
    def _extract_text_from_image(self, image_path: str) -> str:
        """使用OCR提取图片中的文本"""
        try:
            print(f"开始处理图片: {image_path}")
            
            # 先用PIL打开图片检查格式
            try:
                with Image.open(image_path) as img:
                    print(f"图片格式: {img.format}, 大小: {img.size}, 模式: {img.mode}")
                    # 如果是RGBA格式，转换为RGB
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                        img.save(image_path)
                        print("已将RGBA转换为RGB格式")
            except Exception as e:
                print(f"PIL打开图片失败: {str(e)}")
                return "无法识别图片文件，请确保上传了有效的图片文件"
            
            image = cv2.imread(image_path)
            if image is None:
                print("OpenCV无法读取图片")
                raise ValueError("无法读取图片文件，请确保上传了有效的图片文件")
                
            # 检查图片尺寸
            height, width = image.shape[:2]
            print(f"图片尺寸: {width}x{height}")
            if width < 300 or height < 300:
                raise ValueError("图片尺寸太小，请上传更清晰的图片")
            
            # 图片预处理以提高OCR效果
            # 1. 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            print("已转换为灰度图")
            
            # 2. 降噪
            denoised = cv2.fastNlMeansDenoising(gray)
            print("已完成降噪处理")
            
            # 3. 提高对比度
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            print("已增强对比度")
            
            # 保存处理后的图片用于调试
            debug_path = image_path + '_debug.png'
            cv2.imwrite(debug_path, enhanced)
            print(f"已保存处理后的图片到: {debug_path}")
            
            # 使用增强后的图片进行OCR
            print("开始OCR识别...")
            text = pytesseract.image_to_string(
                enhanced, 
                lang='chi_sim',
                config='--psm 1 --oem 3'  # 自动检测页面方向和使用最新的OCR引擎
            )
            
            if not text.strip():
                print("OCR未能识别出文字")
                return "无法识别文字内容，请确保：\n1. 图片清晰度足够\n2. 文字内容清晰可见\n3. 图片方向正确"
            
            print(f"成功识别文字，长度: {len(text)}")
            return text
            
        except Exception as e:
            print(f"OCR处理错误: {str(e)}")
            error_msg = str(e)
            if "无法读取图片" in error_msg:
                return "请上传有效的图片文件（支持PNG、JPG、JPEG格式）"
            elif "尺寸太小" in error_msg:
                return "图片分辨率太低，请上传更清晰的图片"
            else:
                return f"文字识别失败，请确保：\n1. 图片格式正确\n2. 图片未被损坏\n3. 图片清晰度足够"
    
    def _split_sections(self, text: str) -> Dict[str, ResumeSection]:
        """将文本分成不同部分"""
        sections = {}
        if not text or "文字识别失败" in text:
            sections['错误信息'] = ResumeSection(
                content=text,
                suggestions=['请上传清晰的简历图片'],
                score=0
            )
            return sections

        # 预处理文本
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        current_section = ''
        current_content = []
        
        for line in lines:
            # 检查当前行是否匹配任何关键词组
            matched_section = None
            for section_name, keywords in self.keywords.items():
                if any(k in line for k in keywords):
                    matched_section = section_name
                    break
            
            if matched_section:
                if current_section:
                    sections[current_section] = ResumeSection(
                        content='\n'.join(current_content),
                        suggestions=[],
                        score=0
                    )
                current_section = matched_section
                current_content = []
            else:
                current_content.append(line)
        
        # 处理最后一个部分
        if current_section and current_content:
            sections[current_section] = ResumeSection(
                content='\n'.join(current_content),
                suggestions=[],
                score=0
            )
        
        # 如果没有识别出任何部分
        if not sections:
            # 尝试智能分段
            text_blocks = self._smart_split_text(text)
            if text_blocks:
                for i, block in enumerate(text_blocks):
                    section_name = self._guess_section_type(block)
                    sections[section_name] = ResumeSection(
                        content=block,
                        suggestions=[],
                        score=0
                    )
            else:
                sections['未分类内容'] = ResumeSection(
                    content=text,
                    suggestions=[
                        '无法识别简历结构，建议：',
                        '1. 确保简历包含清晰的标题（如：基本信息、教育背景等）',
                        '2. 检查图片是否清晰完整',
                        '3. 调整图片方向确保文字正向'
                    ],
                    score=0
                )
        
        return sections
    
    def _smart_split_text(self, text: str) -> List[str]:
        """智能分段文本"""
        # 按照空行分段
        blocks = []
        current_block = []
        
        for line in text.split('\n'):
            if line.strip():
                current_block.append(line)
            elif current_block:
                blocks.append('\n'.join(current_block))
                current_block = []
                
        if current_block:
            blocks.append('\n'.join(current_block))
            
        return blocks
        
    def _guess_section_type(self, text: str) -> str:
        """猜测文本块的类型"""
        text = text.lower()
        # 基于内容特征判断部分类型
        if any(word in text for word in ['电话', '邮箱', '地址', '性别', '年龄']):
            return '基本信息'
        elif any(word in text for word in ['大学', '学校', '专业', '学历']):
            return '教育背景'
        elif any(word in text for word in ['公司', '工作', '职位', '项目']):
            return '工作经验'
        elif any(word in text for word in ['技能', '证书', '语言', '熟练']):
            return '技能特长'
        else:
            return '其他信息'
    
    def _get_poppler_path(self) -> str:
        """获取poppler的路径"""
        # 检查常见的poppler安装路径
        common_paths = [
            '/usr/local/bin',  # Mac (Homebrew)
            '/usr/bin',        # Linux
            'C:\\Program Files\\poppler\\bin',  # Windows
            'C:\\Program Files (x86)\\poppler\\bin',  # Windows
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                if os.path.exists(os.path.join(path, 'pdftoppm')) or \
                   os.path.exists(os.path.join(path, 'pdftoppm.exe')):
                    print(f"找到poppler路径: {path}")
                    return path
        
        # 如果在常见路径中找不到，尝试从环境变量中查找
        poppler_path = shutil.which('pdftoppm')
        if poppler_path:
            print(f"从环境变量中找到poppler: {os.path.dirname(poppler_path)}")
            return os.path.dirname(poppler_path)
        
        print("未找到poppler路径")
        return None 