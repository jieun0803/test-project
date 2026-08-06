"""
Corrective RAG 구현 모듈
문서 관련성 검증, 쿼리 재작성, 재검색 로직을 포함한 고급 RAG 시스템
"""
import os
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain.schema import Document
from langchain_upstage import ChatUpstage
from langchain.prompts import PromptTemplate
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CorrectiveRAG:
    """문서 관련성 검증과 쿼리 재작성을 통한 Corrective RAG 시스템"""
    
    def __init__(self, vectorstore, min_relevant_docs: int = 2, relevance_threshold: float = 0.7):
        self.vectorstore = vectorstore
        self.min_relevant_docs = min_relevant_docs
        self.relevance_threshold = relevance_threshold
        
        # API 키 가져오기
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise ValueError("UPSTAGE_API_KEY 환경변수가 필요합니다")
        
        # LLM 초기화
        self.llm = ChatUpstage(
            model="solar-pro2",
            upstage_api_key=api_key,
            temperature=0.1,
            max_tokens=2000
        )
        
        # 관련성 검증 프롬프트
        self.relevance_prompt = PromptTemplate(
            template="""다음 문서가 주어진 질문과 관련이 있는지 평가해주세요.

질문: {question}
문서: {document}

평가 기준:
1. 문서가 질문에 직접적으로 답변할 수 있는가?
2. 문서에 질문과 관련된 정보가 포함되어 있는가?
3. 문서의 내용이 질문의 맥락과 일치하는가?

관련성 점수 (0.0-1.0): """,
            input_variables=["question", "document"]
        )
        
        # 쿼리 재작성 프롬프트
        self.query_rewrite_prompt = PromptTemplate(
            template="""다음 질문을 더 구체적이고 검색하기 좋은 형태로 재작성해주세요.

원래 질문: {original_query}
검색된 문서 수: {num_docs}
관련성 점수: {avg_relevance}

재작성된 질문: """,
            input_variables=["original_query", "num_docs", "avg_relevance"]
        )
        
        # 금융 도메인 특화 키워드
        self.financial_keywords = {
            "이자율": ["이자", "금리", "연이율", "연체이율", "기준금리"],
            "수수료": ["수수료", "연회비", "발급비", "관리비", "취급수수료"],
            "한도": ["한도", "한도액", "신용한도", "대출한도", "카드한도"],
            "기간": ["만기", "유효기간", "상환기간", "계약기간", "보장기간"],
            "보험": ["보험료", "보험금", "보험사", "보험가입", "보험계약"],
            "대출": ["대출금", "대출한도", "대출이자", "대출조건", "대출승인"],
            "카드": ["신용카드", "체크카드", "카드한도", "카드수수료", "카드발급"],
            "예금": ["예금", "적금", "정기예금", "예금이자", "예금한도"],
            "투자": ["투자", "펀드", "주식", "채권", "투자수익"]
        }
    
    def calculate_relevance_score(self, question: str, document: Document) -> float:
        """
        문서와 질문 간의 관련성 점수 계산
        
        Args:
            question: 사용자 질문
            document: 검색된 문서
            
        Returns:
            관련성 점수 (0.0-1.0)
        """
        try:
            # LLM을 사용한 관련성 평가
            prompt = self.relevance_prompt.format(
                question=question,
                document=document.page_content[:500]  # 처음 500자만 사용
            )
            
            response = self.llm.invoke(prompt)
            score_text = response.content.strip()
            
            # 점수 추출 (0.0-1.0 범위)
            score_match = re.search(r'(\d+\.?\d*)', score_text)
            if score_match:
                score = float(score_match.group(1))
                # 점수를 0.0-1.0 범위로 정규화
                if score > 1.0:
                    score = score / 100.0
                return min(max(score, 0.0), 1.0)
            else:
                # 기본 점수 반환
                return 0.5
                
        except Exception as e:
            logger.error(f"관련성 점수 계산 중 오류: {str(e)}")
            return 0.5
    
    def verify_document_relevance(self, question: str, documents: List[Document]) -> Tuple[List[Document], List[float]]:
        """
        검색된 문서들의 관련성 검증
        
        Args:
            question: 사용자 질문
            documents: 검색된 문서 목록
            
        Returns:
            (관련 문서 목록, 관련성 점수 목록)
        """
        try:
            relevant_docs = []
            relevance_scores = []
            
            for doc in documents:
                score = self.calculate_relevance_score(question, doc)
                relevance_scores.append(score)
                
                # 임계값 이상인 문서만 포함
                if score >= self.relevance_threshold:
                    relevant_docs.append(doc)
            
            logger.info(f"관련성 검증 완료: {len(relevant_docs)}/{len(documents)} 문서가 관련성 있음")
            return relevant_docs, relevance_scores
            
        except Exception as e:
            logger.error(f"문서 관련성 검증 중 오류: {str(e)}")
            return documents, [0.5] * len(documents)
    
    def rewrite_query(self, original_query: str, num_docs: int, avg_relevance: float) -> str:
        """
        쿼리 재작성
        
        Args:
            original_query: 원래 질문
            num_docs: 검색된 문서 수
            avg_relevance: 평균 관련성 점수
            
        Returns:
            재작성된 쿼리
        """
        try:
            # 관련성 점수가 낮거나 문서 수가 부족한 경우 쿼리 재작성
            if avg_relevance < self.relevance_threshold or num_docs < self.min_relevant_docs:
                prompt = self.query_rewrite_prompt.format(
                    original_query=original_query,
                    num_docs=num_docs,
                    avg_relevance=avg_relevance
                )
                
                response = self.llm.invoke(prompt)
                rewritten_query = response.content.strip()
                
                # 금융 키워드 강화
                enhanced_query = self.enhance_query_with_keywords(rewritten_query)
                
                logger.info(f"쿼리 재작성: '{original_query}' -> '{enhanced_query}'")
                return enhanced_query
            else:
                return original_query
                
        except Exception as e:
            logger.error(f"쿼리 재작성 중 오류: {str(e)}")
            return original_query
    
    def enhance_query_with_keywords(self, query: str) -> str:
        """
        금융 키워드로 쿼리 강화
        
        Args:
            query: 원래 쿼리
            
        Returns:
            강화된 쿼리
        """
        enhanced_query = query
        
        # 관련 금융 키워드 추가
        for category, keywords in self.financial_keywords.items():
            if any(keyword in query for keyword in keywords):
                # 같은 카테고리의 다른 키워드 추가
                for keyword in keywords:
                    if keyword not in enhanced_query:
                        enhanced_query += f" {keyword}"
        
        return enhanced_query
    
    def check_minimum_relevant_docs(self, relevant_docs: List[Document]) -> bool:
        """
        최소 관련 문서 수 체크
        
        Args:
            relevant_docs: 관련 문서 목록
            
        Returns:
            최소 요구사항 충족 여부
        """
        return len(relevant_docs) >= self.min_relevant_docs
    
    def perform_corrective_search(self, question: str, k: int = 10) -> Tuple[List[Document], Dict[str, Any]]:
        """
        Corrective RAG 검색 수행
        
        Args:
            question: 사용자 질문
            k: 검색할 문서 수
            
        Returns:
            (최종 문서 목록, 검색 메타데이터)
        """
        try:
            search_metadata = {
                "original_query": question,
                "search_iterations": 0,
                "final_relevance_scores": [],
                "query_rewritten": False
            }
            
            current_query = question
            max_iterations = 3
            
            for iteration in range(max_iterations):
                search_metadata["search_iterations"] = iteration + 1
                
                # 1. 초기 검색
                documents = self.vectorstore.similarity_search(current_query, k=k)
                
                if not documents:
                    logger.warning("검색된 문서가 없습니다.")
                    return [], search_metadata
                
                # 2. 관련성 검증
                relevant_docs, relevance_scores = self.verify_document_relevance(question, documents)
                search_metadata["final_relevance_scores"] = relevance_scores
                
                # 3. 최소 관련 문서 수 체크
                if self.check_minimum_relevant_docs(relevant_docs):
                    logger.info(f"충분한 관련 문서 발견: {len(relevant_docs)}개")
                    return relevant_docs, search_metadata
                
                # 4. 쿼리 재작성 및 재검색
                avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
                rewritten_query = self.rewrite_query(current_query, len(relevant_docs), avg_relevance)
                
                if rewritten_query != current_query:
                    search_metadata["query_rewritten"] = True
                    current_query = rewritten_query
                    logger.info(f"쿼리 재작성 후 재검색: {rewritten_query}")
                else:
                    # 더 이상 개선할 수 없음
                    logger.info("쿼리 재작성으로 개선할 수 없음")
                    break
            
            # 최종 결과 반환
            logger.info(f"Corrective RAG 완료: {len(relevant_docs)}개 관련 문서")
            return relevant_docs, search_metadata
            
        except Exception as e:
            logger.error(f"Corrective RAG 검색 중 오류: {str(e)}")
            return [], {"error": str(e)}
    
    def get_corrective_info(self) -> Dict[str, Any]:
        """Corrective RAG 시스템 정보 반환"""
        return {
            "min_relevant_docs": self.min_relevant_docs,
            "relevance_threshold": self.relevance_threshold,
            "financial_keywords_categories": list(self.financial_keywords.keys()),
            "max_search_iterations": 3
        }
