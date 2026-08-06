"""
금융 문서 AI 도우미용 유틸리티 함수
"""
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_logging(log_level: str = "INFO"):
    """로깅 설정 구성"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('financial_ai_assistant.log'),
            logging.StreamHandler()
        ]
    )

def validate_api_key(api_key: str) -> bool:
    """Upstage API 키 형식 검증"""
    if not api_key:
        return False
    
    # 기본 검증 - API 키는 비어있지 않은 문자열이어야 함
    if len(api_key.strip()) < 10:
        return False
    
    return True

def create_directories():
    """필요한 디렉토리 생성"""
    directories = [
        "data/pdfs",
        "vectordb",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def save_config(config: Dict[str, Any], filepath: str = "config.json"):
    """설정을 파일에 저장"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"Configuration saved to {filepath}")
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")

def load_config(filepath: str = "config.json") -> Dict[str, Any]:
    """파일에서 설정 로드"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {filepath}")
            return config
        else:
            logger.warning(f"Configuration file not found: {filepath}")
            return {}
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return {}

def format_file_size(size_bytes: int) -> str:
    """파일 크기를 사람이 읽기 쉬운 형식으로 포맷"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def clean_text_for_display(text: str, max_length: int = 200) -> str:
    """표시용 텍스트 정리 및 잘라내기"""
    # 과도한 공백 제거
    text = ' '.join(text.split())
    
    # 너무 길면 잘라내기
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text

def extract_financial_entities(text: str) -> Dict[str, List[str]]:
    """간단한 패턴을 사용하여 텍스트에서 금융 엔티티 추출"""
    import re
    
    entities = {
        "amounts": [],
        "rates": [],
        "dates": [],
        "terms": []
    }
    
    # 금액 패턴 (한국어)
    amount_patterns = [
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*원',
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*만원',
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*억원'
    ]
    
    for pattern in amount_patterns:
        matches = re.findall(pattern, text)
        entities["amounts"].extend(matches)
    
    # 이자율 패턴
    rate_patterns = [
        r'(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*퍼센트',
        r'연\s*(\d+(?:\.\d+)?)\s*%'
    ]
    
    for pattern in rate_patterns:
        matches = re.findall(pattern, text)
        entities["rates"].extend(matches)
    
    # 날짜 패턴
    date_patterns = [
        r'(\d{4})년',
        r'(\d{1,2})월',
        r'(\d{1,2})일',
        r'(\d{1,2})년\s*(\d{1,2})월\s*(\d{1,2})일'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        entities["dates"].extend([match if isinstance(match, str) else ' '.join(match) for match in matches])
    
    # 금융 용어
    financial_terms = [
        '이자율', '수수료', '한도', '만기', '보험료', '대출금', '신용카드',
        '예금', '적금', '투자', '펀드', '주식', '채권', '연체이율'
    ]
    
    for term in financial_terms:
        if term in text:
            entities["terms"].append(term)
    
    return entities

def get_system_info() -> Dict[str, Any]:
    """시스템 정보 가져오기"""
    import platform
    import sys
    
    return {
        "platform": platform.platform(),
        "python_version": sys.version,
        "architecture": platform.architecture(),
        "processor": platform.processor()
    }

def validate_pdf_file(file_path: str) -> bool:
    """PDF 파일 검증"""
    if not os.path.exists(file_path):
        return False
    
    if not file_path.lower().endswith('.pdf'):
        return False
    
    # 파일 크기 확인 (최대 50MB)
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:  # 50MB
        return False
    
    return True

def get_file_info(file_path: str) -> Dict[str, Any]:
    """파일 정보 가져오기"""
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    
    stat = os.stat(file_path)
    return {
        "name": os.path.basename(file_path),
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "modified": stat.st_mtime,
        "extension": os.path.splitext(file_path)[1].lower()
    }
