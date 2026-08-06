"""
환경 변수 로더 모듈
.env 파일에서 환경 변수를 로드하고 검증하는 기능을 제공
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnvironmentLoader:
    """환경 변수 로더 클래스"""
    
    def __init__(self, env_file: str = "config.env"):
        self.env_file = Path(env_file)
        self.loaded_vars = {}
    
    def load_env_file(self) -> bool:
        """
        환경 파일에서 변수를 로드
        
        Returns:
            로드 성공 여부
        """
        try:
            if not self.env_file.exists():
                logger.warning(f"환경 파일이 없습니다: {self.env_file}")
                return False
            
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # 주석이나 빈 줄 건너뛰기
                    if not line or line.startswith('#'):
                        continue
                    
                    # KEY=VALUE 형식 파싱
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # 따옴표 제거
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # 환경 변수 설정
                        os.environ[key] = value
                        self.loaded_vars[key] = value
                        
                        logger.debug(f"환경 변수 로드: {key}")
                    else:
                        logger.warning(f"잘못된 형식 (라인 {line_num}): {line}")
            
            logger.info(f"환경 파일 로드 완료: {len(self.loaded_vars)}개 변수")
            return True
            
        except Exception as e:
            logger.error(f"환경 파일 로드 중 오류: {str(e)}")
            return False
    
    def validate_required_vars(self, required_vars: list) -> bool:
        """
        필수 환경 변수 검증
        
        Args:
            required_vars: 필수 환경 변수 목록
            
        Returns:
            모든 필수 변수가 설정되었는지 여부
        """
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"필수 환경 변수가 설정되지 않았습니다: {missing_vars}")
            return False
        
        logger.info("모든 필수 환경 변수가 설정되었습니다.")
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """
        로드된 환경 변수 정보 반환
        
        Returns:
            환경 변수 딕셔너리
        """
        return {
            "env_file": str(self.env_file),
            "loaded_vars": self.loaded_vars,
            "file_exists": self.env_file.exists()
        }
    
    def create_sample_env_file(self) -> bool:
        """
        샘플 환경 파일 생성
        
        Returns:
            생성 성공 여부
        """
        try:
            sample_content = """# Upstage API Configuration
UPSTAGE_API_KEY=your_upstage_api_key_here

# Document Processing Configuration
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Model Configuration
EMBEDDING_MODEL=solar-embedding-1-large-passage
MAX_TOKENS=4000
TEMPERATURE=0.1

# Vector Database Configuration
VECTOR_DB_PATH=./vectordb
"""
            
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            
            logger.info(f"샘플 환경 파일 생성: {self.env_file}")
            return True
            
        except Exception as e:
            logger.error(f"샘플 환경 파일 생성 중 오류: {str(e)}")
            return False

def load_environment(env_file: str = "config.env") -> bool:
    """
    환경 파일을 로드하고 필수 변수를 검증하는 편의 함수
    
    Args:
        env_file: 환경 파일 경로
        
    Returns:
        로드 및 검증 성공 여부
    """
    loader = EnvironmentLoader(env_file)
    
    # 환경 파일 로드
    if not loader.load_env_file():
        logger.warning("환경 파일 로드 실패, 샘플 파일 생성 시도")
        if not loader.create_sample_env_file():
            return False
        if not loader.load_env_file():
            return False
    
    # 필수 변수 검증
    required_vars = ["UPSTAGE_API_KEY"]
    return loader.validate_required_vars(required_vars)

def get_api_key() -> Optional[str]:
    """
    API 키를 안전하게 가져오는 함수
    
    Returns:
        API 키 또는 None
    """
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key or api_key == "your_upstage_api_key_here":
        logger.error("UPSTAGE_API_KEY가 설정되지 않았거나 기본값입니다.")
        return None
    return api_key
