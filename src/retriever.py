"""
금융 문서 RAG 시스템용 검색 모듈
"""
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_upstage import ChatUpstage
from langchain.schema import Document
from typing import List, Dict, Any, Optional
import logging
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialDocumentRetriever:
    """전문 프롬프트를 가진 금융 문서 검색기"""
    
    def __init__(self, vectorstore, model_name: str = "solar-2-pro"):
        self.vectorstore = vectorstore
        
        # 환경변수에서 API 키 가져오기
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise ValueError("UPSTAGE_API_KEY 환경변수가 필요합니다")
        
        # LLM 초기화
        self.llm = ChatUpstage(
            model="solar-pro2",
            upstage_api_key=api_key,
            temperature=0.1,
            max_tokens=4000
        )
        
        # 컨텍스트 강화를 위한 금융 용어 사전
        self.finance_terms = {
            "이자율": ["이자", "금리", "연이율", "연체이율"],
            "수수료": ["수수료", "연회비", "발급비"],
            "한도": ["한도", "한도액", "신용한도"],
            "기간": ["만기", "유효기간", "상환기간"],
            "보험": ["보험료", "보험금", "보험사"],
            "대출": ["대출금", "대출한도", "대출이자"],
            "카드": ["신용카드", "체크카드", "카드한도"],
            "예금": ["예금", "적금", "정기예금"],
            "투자": ["투자", "펀드", "주식", "채권"]
        }
        
        # 프롬프트 템플릿 생성
        self.prompt_template = PromptTemplate(
            template="""당신은 금융상품 약관을 설명하는 전문가입니다.
주어진 문맥을 바탕으로 질문에 대해 정확하고 이해하기 쉽게 답변해주세요.
답변할 때는 다음 사항을 지켜주세요:
1. 약관 내용을 기반으로만 답변
2. 전문 용어는 쉽게 설명
3. 중요한 내용은 강조
4. 답변을 찾을 수 없으면 "약관에서 해당 내용을 찾을 수 없습니다"라고 답변

문맥: {context}
질문: {question}
답변:""",
            input_variables=["context", "question"]
        )
        
        # QA 체인 초기화
        self.qa_chain = None
        self._initialize_qa_chain()
    
    def _initialize_qa_chain(self):
        """RetrievalQA 체인 초기화"""
        try:
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.vectorstore.vectorstore.as_retriever(
                    search_kwargs={"k": 5}
                ),
                return_source_documents=True,
                chain_type_kwargs={"prompt": self.prompt_template}
            )
            logger.info("QA chain initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing QA chain: {str(e)}")
            raise
    
    def enhance_query_with_finance_terms(self, query: str) -> str:
        """
        관련 금융 용어로 쿼리 강화
        """
        enhanced_query = query
        
        # 관련 금융 용어 추가
        for category, terms in self.finance_terms.items():
            if any(term in query for term in terms):
                # 같은 카테고리의 다른 용어 추가
                for term in terms:
                    if term not in enhanced_query:
                        enhanced_query += f" {term}"
        
        return enhanced_query
    
    def search_documents(self, query: str, k: int = 5) -> List[Document]:
        """
        관련 문서 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            
        Returns:
            관련 문서 목록
        """
        try:
            # 금융 용어로 쿼리 강화
            enhanced_query = self.enhance_query_with_finance_terms(query)
            
            # 문서 검색
            results = self.vectorstore.similarity_search(enhanced_query, k=k)
            
            logger.info(f"Found {len(results)} documents for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            raise
    
    def search_with_scores(self, query: str, k: int = 5) -> List[tuple]:
        """
        유사도 점수와 함께 문서 검색
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            
        Returns:
            (문서, 점수) 튜플 목록
        """
        try:
            enhanced_query = self.enhance_query_with_finance_terms(query)
            results = self.vectorstore.similarity_search_with_score(enhanced_query, k=k)
            
            logger.info(f"Found {len(results)} documents with scores for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents with scores: {str(e)}")
            raise
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        RAG를 사용하여 질문에 답변
        
        Args:
            question: 사용자 질문
            
        Returns:
            답변과 소스 문서를 포함한 딕셔너리
        """
        try:
            if not self.qa_chain:
                raise ValueError("QA chain not initialized")
            
            # QA 체인에서 답변 가져오기
            result = self.qa_chain({"query": question})
            
            # 답변과 소스 추출
            answer = result.get("result", "답변을 생성할 수 없습니다.")
            source_docs = result.get("source_documents", [])
            
            # 소스 문서 포맷팅
            sources = []
            for doc in source_docs:
                # doc이 딕셔너리인 경우와 Document 객체인 경우 모두 처리
                if hasattr(doc, 'page_content'):
                    content = doc.page_content
                    metadata = doc.metadata
                elif isinstance(doc, dict):
                    content = doc.get('page_content', str(doc))
                    metadata = doc.get('metadata', {})
                else:
                    content = str(doc)
                    metadata = {}
                
                sources.append({
                    "content": content[:200] + "..." if len(content) > 200 else content,
                    "metadata": metadata
                })
            
            response = {
                "answer": answer,
                "sources": sources,
                "num_sources": len(sources),
                "question": question
            }
            
            logger.info(f"Generated answer for question: {question[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return {
                "answer": f"오류가 발생했습니다: {str(e)}",
                "sources": [],
                "num_sources": 0,
                "question": question
            }
    
    def get_retriever_info(self) -> Dict[str, Any]:
        """검색기에 대한 정보 가져오기"""
        try:
            collection_info = self.vectorstore.get_collection_info()
            return {
                "model_name": "solar-pro2",
                "collection_info": collection_info,
                "finance_terms_categories": list(self.finance_terms.keys()),
                "qa_chain_initialized": self.qa_chain is not None
            }
        except Exception as e:
            logger.error(f"Error getting retriever info: {str(e)}")
            return {"error": str(e)}
