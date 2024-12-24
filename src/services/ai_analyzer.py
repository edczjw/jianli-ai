import os
from typing import List, Dict
import requests
from dotenv import load_dotenv
import datetime
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

load_dotenv()

class AIAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('KIMI_API_KEY')
        if not self.api_key:
            raise ValueError("KIMI_API_KEY not found in environment variables")
            
        self.api_url = "https://api.moonshot.cn/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.api_key
        }
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,  # 最多重试3次
            backoff_factor=1,  # 重试间隔
            status_forcelist=[429, 500, 502, 503, 504]  # 需要重试的HTTP状态码
        )
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        
    def analyze_section(self, section_name: str, content: str) -> Dict:
        """使用Kimi AI分析简历各个部分"""
        print(f"开始分析部分: {section_name}")
        print(f"API URL: {self.api_url}")
        print(f"Headers: {self.headers}")
        
        if not content or not content.strip():
            return {
                'score': 0,
                'suggestions': ['该部分内容为空，请添加相关信息'],
                'highlights': [],
                'raw_analysis': ''
            }

        prompts = {
            '基本信息': '请分析以下简历基本信息部分，给出改进建议：',
            '教育背景': '请分析以下教育背景，评估其优劣势并给出建议：',
            '工作经验': '请分析以下工作经验，给出如何更好展示的建议：',
            '技能特长': '请分析以下技能特长，并给出改进建议：'
        }
        
        prompt = f"{prompts.get(section_name, '请分析以下简历内容：')}\n\n{content}\n\n" + \
                 "请给出：\n1. 评分（0-100）\n2. 具体改进建议（至少3条）\n3. 亮点分析"
        
        try:
            payload = {
                "model": "moonshot-v1-8k",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的HR和简历分析专家，请帮助分析简历并给出专业的建议。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7
            }
            
            print(f"发送请求到 API，payload: {payload}")
            # 使用session发送请求
            response = self.session.post(self.api_url, headers=self.headers, json=payload)
            print(f"API 响应状态码: {response.status_code}")
            
            # 处理速率限制
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                print(f"达到速率限制，等待 {retry_after} 秒后重试")
                time.sleep(retry_after)
                # 重试请求
                response = self.session.post(self.api_url, headers=self.headers, json=payload)
            
            print(f"API 响应内容: {response.text[:200]}...")  # 只打印前200个字符
            
            response.raise_for_status()
            
            result = response.json()
            if 'choices' not in result or not result['choices']:
                raise ValueError("Invalid response from AI service")
                
            analysis = result['choices'][0]['message']['content']
            
            score = self._extract_score(analysis)
            suggestions = self._extract_suggestions(analysis)
            highlights = self._extract_highlights(analysis)
            
            return {
                'score': score,
                'suggestions': suggestions,
                'highlights': highlights,
                'raw_analysis': analysis
            }
            
        except requests.exceptions.RequestException as e:
            print(f"API请求错误: {str(e)}")
            print(f"请求详情: URL={self.api_url}, Headers={self.headers}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"错误响应: {e.response.text}")
                if e.response.status_code == 429:
                    return {
                        'score': 0,
                        'suggestions': ['服务器繁忙，请稍后再试（速率限制）'],
                        'highlights': [],
                        'raw_analysis': str(e)
                    }
            return {
                'score': 0,
                'suggestions': [
                    'AI服务暂时无法访问，请检查：',
                    '1. 网络连接是否正常',
                    '2. API密钥是否正确',
                    '3. API服务是否可用'
                ],
                'highlights': [],
                'raw_analysis': str(e)
            }
        except Exception as e:
            print(f"分析过程出错: {str(e)}")
            return {
                'score': 0,
                'suggestions': ['分析过程出现错误，请重试'],
                'highlights': [],
                'raw_analysis': str(e)
            }
    
    def _extract_score(self, analysis: str) -> float:
        """从AI响应中提取分数"""
        try:
            for line in analysis.split('\n'):
                if '评分' in line or '分数' in line:
                    score = float(''.join(filter(str.isdigit, line)))
                    return min(100, max(0, score))
        except:
            pass
        return 60
    
    def _extract_suggestions(self, analysis: str) -> List[str]:
        """从AI响应中提取建议"""
        suggestions = []
        in_suggestions = False
        for line in analysis.split('\n'):
            if '建议' in line:
                in_suggestions = True
                continue
            if in_suggestions and line.strip():
                if line.startswith(('1.', '2.', '3.', '-', '•')):
                    suggestions.append(line.strip())
            if len(suggestions) >= 3:
                break
        return suggestions or ['暂无具体建议']
    
    def _extract_highlights(self, analysis: str) -> List[str]:
        """从AI响应中提取亮点分析"""
        highlights = []
        in_highlights = False
        for line in analysis.split('\n'):
            if '亮点' in line:
                in_highlights = True
                continue
            if in_highlights and line.strip():
                if line.startswith(('1.', '2.', '3.', '-', '•')):
                    highlights.append(line.strip())
        return highlights 