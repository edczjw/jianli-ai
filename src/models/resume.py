from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from services.ai_analyzer import AIAnalyzer

@dataclass
class ResumeSection:
    content: str
    suggestions: List[str]
    score: float
    highlights: List[str] = None

@dataclass
class Resume:
    id: str
    upload_time: datetime
    file_path: str
    image_path: str
    sections: Dict[str, ResumeSection]
    overall_score: float
    
    def analyze(self):
        """分析简历内容"""
        analyzer = AIAnalyzer()
        total_score = 0
        section_count = 0
        
        for name, section in self.sections.items():
            if name != '错误信息' and name != '未分类内容':
                result = analyzer.analyze_section(name, section.content)
                section.score = result.get('score', 0)
                section.suggestions = result.get('suggestions', [])
                section.highlights = result.get('highlights', [])
                total_score += section.score
                section_count += 1
        
        self.overall_score = total_score / max(section_count, 1) 