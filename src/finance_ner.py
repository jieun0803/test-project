"""
금융 NER (Named Entity Recognition) 시스템 구현 모듈
금융 용어 사전 구축, 정규표현식 패턴 정의, 엔티티 추출, 쿼리 강화 기능을 포함
"""
import re
import logging
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EntityType(Enum):
    """엔티티 타입 열거형"""
    INTEREST_RATE = "이자율"
    FEE = "수수료"
    LIMIT = "한도"
    PERIOD = "기간"
    AMOUNT = "금액"
    DATE = "날짜"
    CARD_TYPE = "카드종류"
    ACCOUNT_TYPE = "계좌종류"
    INSURANCE_TYPE = "보험종류"
    LOAN_TYPE = "대출종류"

@dataclass
class FinancialEntity:
    """금융 엔티티 데이터 클래스"""
    text: str
    entity_type: EntityType
    start_pos: int
    end_pos: int
    confidence: float
    metadata: Dict[str, Any] = None

class FinancialNER:
    """금융 도메인 전용 NER 시스템"""
    
    def __init__(self):
        # 금융 용어 사전 구축
        self.financial_terms = self._build_financial_dictionary()
        
        # 정규표현식 패턴 정의
        self.patterns = self._define_regex_patterns()
        
        # 금융 키워드 매핑
        self.keyword_mapping = self._build_keyword_mapping()
    
    def _build_financial_dictionary(self) -> Dict[EntityType, List[str]]:
        """금융 용어 사전 구축"""
        return {
            EntityType.INTEREST_RATE: [
                "이자율", "금리", "연이율", "연체이율", "기준금리", "가산금리", 
                "우대금리", "고정금리", "변동금리", "복리", "단리", "연체료"
            ],
            EntityType.FEE: [
                "수수료", "연회비", "발급비", "관리비", "취급수수료", "인출수수료",
                "해외이용수수료", "현금서비스수수료", "연체수수료", "가맹점수수료"
            ],
            EntityType.LIMIT: [
                "한도", "한도액", "신용한도", "대출한도", "카드한도", "현금서비스한도",
                "일일한도", "월한도", "연한도", "승인한도", "사용한도"
            ],
            EntityType.PERIOD: [
                "만기", "유효기간", "상환기간", "계약기간", "보장기간", "이용기간",
                "우대기간", "무이자기간", "연체기간", "상환기한", "만료일"
            ],
            EntityType.CARD_TYPE: [
                "신용카드", "체크카드", "현금카드", "선불카드", "기프트카드",
                "법인카드", "개인카드", "학생카드", "주니어카드", "골드카드"
            ],
            EntityType.ACCOUNT_TYPE: [
                "예금", "적금", "정기예금", "정기적금", "자유적금", "주택청약",
                "연금저축", "펀드", "MMF", "CMA", "RP", "CD"
            ],
            EntityType.INSURANCE_TYPE: [
                "보험", "생명보험", "손해보험", "자동차보험", "화재보험", "여행보험",
                "건강보험", "실손보험", "종신보험", "연금보험", "상해보험"
            ],
            EntityType.LOAN_TYPE: [
                "대출", "신용대출", "주택대출", "자동차대출", "학자금대출", "사업자대출",
                "담보대출", "무담보대출", "전세대출", "마이너스통장", "신용한도대출"
            ]
        }
    
    def _define_regex_patterns(self) -> Dict[EntityType, str]:
        """정규표현식 패턴 정의"""
        return {
            EntityType.AMOUNT: r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:원|만원|억원|천원)',
            EntityType.INTEREST_RATE: r'(\d+(?:\.\d+)?)\s*%',
            EntityType.DATE: r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일|(\d{1,2})월\s*(\d{1,2})일|(\d{4})년',
            EntityType.PERIOD: r'(\d+)\s*(?:년|월|일|개월|주|일)',
            EntityType.LIMIT: r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:원|만원|억원)\s*(?:한도|한도액)'
        }
    
    def _build_keyword_mapping(self) -> Dict[str, EntityType]:
        """키워드-엔티티 타입 매핑 구축"""
        mapping = {}
        for entity_type, terms in self.financial_terms.items():
            for term in terms:
                mapping[term] = entity_type
        return mapping
    
    def extract_entities(self, text: str) -> List[FinancialEntity]:
        """
        텍스트에서 금융 엔티티 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            추출된 금융 엔티티 목록
        """
        entities = []
        
        try:
            # 1. 사전 기반 엔티티 추출
            dictionary_entities = self._extract_dictionary_entities(text)
            entities.extend(dictionary_entities)
            
            # 2. 정규표현식 기반 엔티티 추출
            regex_entities = self._extract_regex_entities(text)
            entities.extend(regex_entities)
            
            # 3. 중복 제거 및 정렬
            entities = self._remove_duplicates(entities)
            entities.sort(key=lambda x: x.start_pos)
            
            logger.info(f"엔티티 추출 완료: {len(entities)}개")
            return entities
            
        except Exception as e:
            logger.error(f"엔티티 추출 중 오류: {str(e)}")
            return []
    
    def _extract_dictionary_entities(self, text: str) -> List[FinancialEntity]:
        """사전 기반 엔티티 추출"""
        entities = []
        
        for entity_type, terms in self.financial_terms.items():
            for term in terms:
                # 대소문자 구분 없이 검색
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                
                for match in pattern.finditer(text):
                    entity = FinancialEntity(
                        text=match.group(),
                        entity_type=entity_type,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.9,  # 사전 기반이므로 높은 신뢰도
                        metadata={"source": "dictionary", "term": term}
                    )
                    entities.append(entity)
        
        return entities
    
    def _extract_regex_entities(self, text: str) -> List[FinancialEntity]:
        """정규표현식 기반 엔티티 추출"""
        entities = []
        
        for entity_type, pattern in self.patterns.items():
            regex = re.compile(pattern)
            
            for match in regex.finditer(text):
                entity = FinancialEntity(
                    text=match.group(),
                    entity_type=entity_type,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.8,  # 정규표현식 기반이므로 중간 신뢰도
                    metadata={"source": "regex", "pattern": pattern}
                )
                entities.append(entity)
        
        return entities
    
    def _remove_duplicates(self, entities: List[FinancialEntity]) -> List[FinancialEntity]:
        """중복 엔티티 제거"""
        unique_entities = []
        seen_positions = set()
        
        for entity in entities:
            position_key = (entity.start_pos, entity.end_pos)
            if position_key not in seen_positions:
                unique_entities.append(entity)
                seen_positions.add(position_key)
        
        return unique_entities
    
    def enhance_query_with_entities(self, query: str) -> Tuple[str, List[FinancialEntity]]:
        """
        엔티티를 활용한 쿼리 강화
        
        Args:
            query: 원래 쿼리
            
        Returns:
            (강화된 쿼리, 추출된 엔티티 목록)
        """
        try:
            # 엔티티 추출
            entities = self.extract_entities(query)
            
            enhanced_query = query
            
            # 관련 금융 용어 추가
            for entity in entities:
                entity_type = entity.entity_type
                if entity_type in self.financial_terms:
                    related_terms = self.financial_terms[entity_type]
                    for term in related_terms:
                        if term not in enhanced_query:
                            enhanced_query += f" {term}"
            
            # 금액, 이자율 등 수치 정보 강화
            amount_entities = [e for e in entities if e.entity_type == EntityType.AMOUNT]
            rate_entities = [e for e in entities if e.entity_type == EntityType.INTEREST_RATE]
            
            if amount_entities:
                enhanced_query += " 금액 한도"
            if rate_entities:
                enhanced_query += " 이자율 금리"
            
            logger.info(f"쿼리 강화 완료: {len(entities)}개 엔티티 추출")
            return enhanced_query, entities
            
        except Exception as e:
            logger.error(f"쿼리 강화 중 오류: {str(e)}")
            return query, []
    
    def extract_financial_numbers(self, text: str) -> Dict[str, List[str]]:
        """
        금융 관련 수치 정보 추출
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            수치 정보 딕셔너리
        """
        try:
            financial_numbers = {
                "amounts": [],
                "rates": [],
                "periods": [],
                "limits": []
            }
            
            # 금액 패턴
            amount_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:원|만원|억원|천원)'
            amounts = re.findall(amount_pattern, text)
            financial_numbers["amounts"] = amounts
            
            # 이자율 패턴
            rate_pattern = r'(\d+(?:\.\d+)?)\s*%'
            rates = re.findall(rate_pattern, text)
            financial_numbers["rates"] = rates
            
            # 기간 패턴
            period_pattern = r'(\d+)\s*(?:년|월|일|개월|주)'
            periods = re.findall(period_pattern, text)
            financial_numbers["periods"] = periods
            
            # 한도 패턴
            limit_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:원|만원|억원)\s*(?:한도|한도액)'
            limits = re.findall(limit_pattern, text)
            financial_numbers["limits"] = limits
            
            return financial_numbers
            
        except Exception as e:
            logger.error(f"금융 수치 정보 추출 중 오류: {str(e)}")
            return {"amounts": [], "rates": [], "periods": [], "limits": []}
    
    def get_entity_statistics(self, entities: List[FinancialEntity]) -> Dict[str, Any]:
        """
        엔티티 통계 정보 생성
        
        Args:
            entities: 엔티티 목록
            
        Returns:
            통계 정보 딕셔너리
        """
        try:
            stats = {
                "total_entities": len(entities),
                "entity_types": {},
                "confidence_distribution": {
                    "high": 0,    # >= 0.8
                    "medium": 0,  # 0.5-0.8
                    "low": 0      # < 0.5
                }
            }
            
            # 엔티티 타입별 개수
            for entity in entities:
                entity_type = entity.entity_type.value
                stats["entity_types"][entity_type] = stats["entity_types"].get(entity_type, 0) + 1
                
                # 신뢰도 분포
                if entity.confidence >= 0.8:
                    stats["confidence_distribution"]["high"] += 1
                elif entity.confidence >= 0.5:
                    stats["confidence_distribution"]["medium"] += 1
                else:
                    stats["confidence_distribution"]["low"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"엔티티 통계 생성 중 오류: {str(e)}")
            return {"error": str(e)}
    
    def get_ner_info(self) -> Dict[str, Any]:
        """NER 시스템 정보 반환"""
        return {
            "supported_entity_types": [e.value for e in EntityType],
            "dictionary_size": sum(len(terms) for terms in self.financial_terms.values()),
            "pattern_count": len(self.patterns),
            "keyword_mapping_size": len(self.keyword_mapping)
        }
