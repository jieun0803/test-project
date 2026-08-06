"""
고급 RAG 통합 시스템 구현 모듈
모든 모듈을 통합한 파이프라인 구성 및 컴포넌트 활성화/비활성화 옵션을 포함
"""
import os
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain.schema import Document
from langchain_upstage import ChatUpstage
from langchain.prompts import PromptTemplate

# 로컬 모듈 임포트
from .embedding import FinancialEmbeddingStore
from .retriever import FinancialDocumentRetriever
from .corrective_rag import CorrectiveRAG
from .reranker import DocumentReranker
from .finance_ner import FinancialNER

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedRAGSystem:
    """고급 RAG 통합 시스템"""
    
    def __init__(self, 
                 vectorstore: FinancialEmbeddingStore,
                 enable_corrective_rag: bool = True,
                 enable_reranking: bool = True,
                 enable_ner: bool = True,
                 rerank_method: str = "hybrid",
                 top_k: int = 5):
        
        self.vectorstore = vectorstore
        self.enable_corrective_rag = enable_corrective_rag
        self.enable_reranking = enable_reranking
        self.enable_ner = enable_ner
        self.rerank_method = rerank_method
        self.top_k = top_k
        
        # API 키 가져오기
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
        
        # 컴포넌트 초기화
        self._initialize_components()
        
        # 고급 프롬프트 템플릿
        self.advanced_prompt = PromptTemplate(
            template="""당신은 금융상품 약관을 설명하는 전문가입니다.
다음 정보를 바탕으로 질문에 대해 정확하고 이해하기 쉽게 답변해주세요.

추출된 금융 엔티티: {entities}
관련성 점수: {relevance_scores}

문맥: {context}
질문: {question}

답변할 때는 다음 사항을 지켜주세요:
1. 약관 내용을 기반으로만 답변
2. 전문 용어는 쉽게 설명
3. 중요한 내용은 강조
4. 추출된 금융 정보를 활용하여 정확한 답변 제공
5. 답변을 찾을 수 없으면 "약관에서 해당 내용을 찾을 수 없습니다"라고 답변

답변:""",
            input_variables=["entities", "relevance_scores", "context", "question"]
        )
    
    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            # 기본 검색기 초기화
            self.basic_retriever = FinancialDocumentRetriever(self.vectorstore)
            
            # 고급 컴포넌트 초기화 (활성화된 경우에만)
            if self.enable_corrective_rag:
                self.corrective_rag = CorrectiveRAG(self.vectorstore)
                logger.info("Corrective RAG 활성화됨")
            
            if self.enable_reranking:
                self.reranker = DocumentReranker()
                logger.info("Reranking 시스템 활성화됨")
            
            if self.enable_ner:
                self.ner = FinancialNER()
                logger.info("금융 NER 시스템 활성화됨")
            
            logger.info("고급 RAG 시스템 초기화 완료")
            
        except Exception as e:
            logger.error(f"컴포넌트 초기화 중 오류: {str(e)}")
            raise
    
    def process_query(self, question: str) -> Dict[str, Any]:
        """
        고급 RAG 파이프라인을 통한 질문 처리
        
        Args:
            question: 사용자 질문
            
        Returns:
            처리 결과 딕셔너리
        """
        try:
            pipeline_metadata = {
                "original_question": question,
                "components_used": [],
                "processing_steps": [],
                "final_documents": [],
                "entities": [],
                "relevance_scores": []
            }
            
            # Step 1: NER 엔티티 추출 (활성화된 경우)
            enhanced_question = question
            entities = []
            if self.enable_ner:
                enhanced_question, entities = self.ner.enhance_query_with_entities(question)
                pipeline_metadata["entities"] = [{"text": e.text, "type": e.entity_type.value} for e in entities]
                pipeline_metadata["components_used"].append("NER")
                pipeline_metadata["processing_steps"].append("엔티티 추출 및 쿼리 강화")
            
            # Step 2: Corrective RAG 검색 (활성화된 경우)
            if self.enable_corrective_rag:
                documents, corrective_metadata = self.corrective_rag.perform_corrective_search(
                    enhanced_question, k=self.top_k * 2
                )
                pipeline_metadata["components_used"].append("CorrectiveRAG")
                pipeline_metadata["processing_steps"].append("문서 관련성 검증 및 쿼리 재작성")
            else:
                # 기본 검색
                documents = self.vectorstore.similarity_search(enhanced_question, k=self.top_k * 2)
                pipeline_metadata["processing_steps"].append("기본 벡터 검색")
            
            # Step 3: Reranking (활성화된 경우)
            if self.enable_reranking and documents:
                reranked_docs, scores, rerank_metadata = self.reranker.rerank_documents(
                    question, documents, method=self.rerank_method, top_k=self.top_k
                )
                documents = reranked_docs
                pipeline_metadata["relevance_scores"] = scores
                pipeline_metadata["components_used"].append("Reranking")
                pipeline_metadata["processing_steps"].append(f"{self.rerank_method} 방법으로 문서 재순위화")
            
            # 최종 문서 선택
            final_documents = documents[:self.top_k]
            pipeline_metadata["final_documents"] = [{"content": doc.page_content[:200], "metadata": doc.metadata} for doc in final_documents]
            
            # Step 4: 답변 생성
            answer = self._generate_advanced_answer(question, final_documents, entities, pipeline_metadata["relevance_scores"])
            
            # 결과 구성
            result = {
                "answer": answer,
                "sources": final_documents,
                "num_sources": len(final_documents),
                "question": question,
                "enhanced_question": enhanced_question,
                "entities": pipeline_metadata["entities"],
                "relevance_scores": pipeline_metadata["relevance_scores"],
                "pipeline_metadata": pipeline_metadata
            }
            
            logger.info(f"고급 RAG 처리 완료: {len(pipeline_metadata['components_used'])}개 컴포넌트 사용")
            return result
            
        except Exception as e:
            logger.error(f"고급 RAG 처리 중 오류: {str(e)}")
            return {
                "answer": f"오류가 발생했습니다: {str(e)}",
                "sources": [],
                "num_sources": 0,
                "question": question,
                "error": str(e)
            }
    
    def _generate_advanced_answer(self, question: str, documents: List[Document], 
                                 entities: List, relevance_scores: List[float]) -> str:
        """고급 답변 생성"""
        try:
            if not documents:
                return "관련 문서를 찾을 수 없습니다."
            
            # 컨텍스트 구성
            context = "\n\n".join([doc.page_content for doc in documents])
            
            # 엔티티 정보 구성
            entity_info = ", ".join([f"{e.text}({e.entity_type.value})" for e in entities]) if entities else "없음"
            
            # 관련성 점수 정보 구성
            score_info = f"평균: {sum(relevance_scores)/len(relevance_scores):.2f}" if relevance_scores else "없음"
            
            # 프롬프트 구성
            prompt = self.advanced_prompt.format(
                entities=entity_info,
                relevance_scores=score_info,
                context=context,
                question=question
            )
            
            # LLM 답변 생성
            response = self.llm.invoke(prompt)
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"고급 답변 생성 중 오류: {str(e)}")
            return "답변 생성 중 오류가 발생했습니다."
    
    def toggle_component(self, component_name: str, enable: bool):
        """
        컴포넌트 활성화/비활성화
        
        Args:
            component_name: 컴포넌트 이름 ("corrective_rag", "reranking", "ner")
            enable: 활성화 여부
        """
        try:
            if component_name == "corrective_rag":
                self.enable_corrective_rag = enable
                if enable and not hasattr(self, 'corrective_rag'):
                    self.corrective_rag = CorrectiveRAG(self.vectorstore)
                logger.info(f"Corrective RAG {'활성화' if enable else '비활성화'}")
                
            elif component_name == "reranking":
                self.enable_reranking = enable
                if enable and not hasattr(self, 'reranker'):
                    self.reranker = DocumentReranker()
                logger.info(f"Reranking {'활성화' if enable else '비활성화'}")
                
            elif component_name == "ner":
                self.enable_ner = enable
                if enable and not hasattr(self, 'ner'):
                    self.ner = FinancialNER()
                logger.info(f"NER {'활성화' if enable else '비활성화'}")
                
            else:
                raise ValueError(f"지원하지 않는 컴포넌트: {component_name}")
                
        except Exception as e:
            logger.error(f"컴포넌트 토글 중 오류: {str(e)}")
            raise
    
    def set_rerank_method(self, method: str):
        """
        재순위화 방법 설정
        
        Args:
            method: 재순위화 방법 ("llm", "tfidf", "hybrid", "mmr")
        """
        if method in ["llm", "tfidf", "hybrid", "mmr"]:
            self.rerank_method = method
            logger.info(f"재순위화 방법 변경: {method}")
        else:
            raise ValueError(f"지원하지 않는 재순위화 방법: {method}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 정보 반환"""
        return {
            "corrective_rag_enabled": self.enable_corrective_rag,
            "reranking_enabled": self.enable_reranking,
            "ner_enabled": self.enable_ner,
            "rerank_method": self.rerank_method,
            "top_k": self.top_k,
            "components_available": {
                "corrective_rag": hasattr(self, 'corrective_rag'),
                "reranker": hasattr(self, 'reranker'),
                "ner": hasattr(self, 'ner')
            }
        }
    
    def get_performance_metrics(self, question: str) -> Dict[str, Any]:
        """
        성능 메트릭 계산
        
        Args:
            question: 테스트 질문
            
        Returns:
            성능 메트릭 딕셔너리
        """
        try:
            import time
            start_time = time.time()
            
            # 처리 시간 측정
            result = self.process_query(question)
            processing_time = time.time() - start_time
            
            # 메트릭 계산
            metrics = {
                "processing_time": processing_time,
                "num_sources": result.get("num_sources", 0),
                "num_entities": len(result.get("entities", [])),
                "components_used": len(result.get("pipeline_metadata", {}).get("components_used", [])),
                "avg_relevance_score": sum(result.get("relevance_scores", [])) / len(result.get("relevance_scores", [])) if result.get("relevance_scores") else 0.0
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"성능 메트릭 계산 중 오류: {str(e)}")
            return {"error": str(e)}
    
    def reset_system(self):
        """시스템 초기화"""
        try:
            # 컴포넌트 재초기화
            self._initialize_components()
            logger.info("시스템 초기화 완료")
            
        except Exception as e:
            logger.error(f"시스템 초기화 중 오류: {str(e)}")
            raise
