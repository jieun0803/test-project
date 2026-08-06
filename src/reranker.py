"""
Reranking 시스템 구현 모듈
LLM 기반 관련성 점수 계산, 점수 기반 정렬, MMR 알고리즘을 포함한 고급 재순위화 시스템
"""
import os
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from langchain.schema import Document
from langchain_upstage import ChatUpstage
from langchain.prompts import PromptTemplate
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentReranker:
    """문서 재순위화를 위한 고급 시스템"""
    
    def __init__(self, diversity_weight: float = 0.3, relevance_weight: float = 0.7):
        self.diversity_weight = diversity_weight
        self.relevance_weight = relevance_weight
        
        # API 키 가져오기
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise ValueError("UPSTAGE_API_KEY 환경변수가 필요합니다")
        
        # LLM 초기화
        self.llm = ChatUpstage(
            model="solar-pro2",
            upstage_api_key=api_key,
            temperature=0.1,
            max_tokens=1000
        )
        
        # 관련성 점수 계산 프롬프트
        self.relevance_scoring_prompt = PromptTemplate(
            template="""다음 문서가 주어진 질문과 얼마나 관련이 있는지 0.0-1.0 점수로 평가해주세요.

질문: {question}
문서: {document}

평가 기준:
1. 문서가 질문에 직접적으로 답변할 수 있는가? (0.0-0.4)
2. 문서에 질문과 관련된 정보가 포함되어 있는가? (0.0-0.3)
3. 문서의 내용이 질문의 맥락과 일치하는가? (0.0-0.3)

총점 (0.0-1.0): """,
            input_variables=["question", "document"]
        )
        
        # TF-IDF 벡터화기 초기화
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # 한국어는 별도 처리
            ngram_range=(1, 2)
        )
    
    def calculate_llm_relevance_score(self, question: str, document: Document) -> float:
        """
        LLM을 사용한 관련성 점수 계산
        
        Args:
            question: 사용자 질문
            document: 검색된 문서
            
        Returns:
            관련성 점수 (0.0-1.0)
        """
        try:
            # 문서 내용을 적절한 길이로 자르기
            doc_content = document.page_content[:800]  # 처음 800자만 사용
            
            prompt = self.relevance_scoring_prompt.format(
                question=question,
                document=doc_content
            )
            
            response = self.llm.invoke(prompt)
            score_text = response.content.strip()
            
            # 점수 추출
            score_match = re.search(r'(\d+\.?\d*)', score_text)
            if score_match:
                score = float(score_match.group(1))
                # 점수를 0.0-1.0 범위로 정규화
                if score > 1.0:
                    score = score / 100.0
                return min(max(score, 0.0), 1.0)
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"LLM 관련성 점수 계산 중 오류: {str(e)}")
            return 0.5
    
    def calculate_tfidf_similarity(self, question: str, documents: List[Document]) -> List[float]:
        """
        TF-IDF 기반 유사도 계산
        
        Args:
            question: 사용자 질문
            documents: 문서 목록
            
        Returns:
            유사도 점수 목록
        """
        try:
            # 문서 텍스트 추출
            doc_texts = [doc.page_content for doc in documents]
            all_texts = [question] + doc_texts
            
            # TF-IDF 벡터화
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(all_texts)
            
            # 질문과 문서들 간의 코사인 유사도 계산
            question_vector = tfidf_matrix[0:1]
            doc_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(question_vector, doc_vectors)[0]
            
            return similarities.tolist()
            
        except Exception as e:
            logger.error(f"TF-IDF 유사도 계산 중 오류: {str(e)}")
            return [0.5] * len(documents)
    
    def calculate_hybrid_relevance_scores(self, question: str, documents: List[Document]) -> List[float]:
        """
        하이브리드 관련성 점수 계산 (LLM + TF-IDF)
        
        Args:
            question: 사용자 질문
            documents: 문서 목록
            
        Returns:
            하이브리드 관련성 점수 목록
        """
        try:
            # LLM 점수 계산
            llm_scores = []
            for doc in documents:
                score = self.calculate_llm_relevance_score(question, doc)
                llm_scores.append(score)
            
            # TF-IDF 점수 계산
            tfidf_scores = self.calculate_tfidf_similarity(question, documents)
            
            # 하이브리드 점수 계산 (가중 평균)
            hybrid_scores = []
            for llm_score, tfidf_score in zip(llm_scores, tfidf_scores):
                hybrid_score = (llm_score * 0.7) + (tfidf_score * 0.3)
                hybrid_scores.append(hybrid_score)
            
            logger.info(f"하이브리드 관련성 점수 계산 완료: {len(hybrid_scores)}개 문서")
            return hybrid_scores
            
        except Exception as e:
            logger.error(f"하이브리드 관련성 점수 계산 중 오류: {str(e)}")
            return [0.5] * len(documents)
    
    def calculate_mmr_score(self, doc: Document, question: str, selected_docs: List[Document], 
                           relevance_scores: List[float], doc_index: int) -> float:
        """
        MMR(Maximal Marginal Relevance) 점수 계산
        
        Args:
            doc: 현재 문서
            question: 사용자 질문
            selected_docs: 이미 선택된 문서들
            relevance_scores: 관련성 점수 목록
            doc_index: 현재 문서의 인덱스
            
        Returns:
            MMR 점수
        """
        try:
            # 관련성 점수
            relevance_score = relevance_scores[doc_index]
            
            # 다양성 점수 계산
            if not selected_docs:
                diversity_score = 1.0
            else:
                # 현재 문서와 선택된 문서들 간의 유사도 계산
                similarities = []
                for selected_doc in selected_docs:
                    # 간단한 텍스트 유사도 계산
                    doc_text = doc.page_content.lower()
                    selected_text = selected_doc.page_content.lower()
                    
                    # 공통 단어 수 계산
                    doc_words = set(doc_text.split())
                    selected_words = set(selected_text.split())
                    common_words = len(doc_words.intersection(selected_words))
                    total_words = len(doc_words.union(selected_words))
                    
                    if total_words > 0:
                        similarity = common_words / total_words
                        similarities.append(similarity)
                    else:
                        similarities.append(0.0)
                
                # 최대 유사도 (다양성의 역수)
                max_similarity = max(similarities) if similarities else 0.0
                diversity_score = 1.0 - max_similarity
            
            # MMR 점수 계산
            mmr_score = (self.relevance_weight * relevance_score) + (self.diversity_weight * diversity_score)
            
            return mmr_score
            
        except Exception as e:
            logger.error(f"MMR 점수 계산 중 오류: {str(e)}")
            return relevance_scores[doc_index]
    
    def rerank_documents(self, question: str, documents: List[Document], 
                        method: str = "hybrid", top_k: int = 5) -> Tuple[List[Document], List[float], Dict[str, Any]]:
        """
        문서 재순위화
        
        Args:
            question: 사용자 질문
            documents: 재순위화할 문서 목록
            method: 재순위화 방법 ("llm", "tfidf", "hybrid", "mmr")
            top_k: 반환할 상위 문서 수
            
        Returns:
            (재순위화된 문서 목록, 점수 목록, 메타데이터)
        """
        try:
            if not documents:
                return [], [], {"error": "문서가 없습니다"}
            
            rerank_metadata = {
                "method": method,
                "total_documents": len(documents),
                "top_k": top_k,
                "scores": []
            }
            
            if method == "llm":
                # LLM 기반 재순위화
                scores = []
                for doc in documents:
                    score = self.calculate_llm_relevance_score(question, doc)
                    scores.append(score)
                
                # 점수 기준 정렬
                doc_score_pairs = list(zip(documents, scores))
                doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
                
                reranked_docs = [doc for doc, score in doc_score_pairs[:top_k]]
                reranked_scores = [score for doc, score in doc_score_pairs[:top_k]]
                
            elif method == "tfidf":
                # TF-IDF 기반 재순위화
                scores = self.calculate_tfidf_similarity(question, documents)
                
                # 점수 기준 정렬
                doc_score_pairs = list(zip(documents, scores))
                doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
                
                reranked_docs = [doc for doc, score in doc_score_pairs[:top_k]]
                reranked_scores = [score for doc, score in doc_score_pairs[:top_k]]
                
            elif method == "hybrid":
                # 하이브리드 재순위화
                scores = self.calculate_hybrid_relevance_scores(question, documents)
                
                # 점수 기준 정렬
                doc_score_pairs = list(zip(documents, scores))
                doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
                
                reranked_docs = [doc for doc, score in doc_score_pairs[:top_k]]
                reranked_scores = [score for doc, score in doc_score_pairs[:top_k]]
                
            elif method == "mmr":
                # MMR 알고리즘 기반 재순위화
                relevance_scores = self.calculate_hybrid_relevance_scores(question, documents)
                
                selected_docs = []
                selected_scores = []
                remaining_indices = list(range(len(documents)))
                
                for _ in range(min(top_k, len(documents))):
                    best_score = -1
                    best_index = -1
                    
                    for idx in remaining_indices:
                        mmr_score = self.calculate_mmr_score(
                            documents[idx], question, selected_docs, 
                            relevance_scores, idx
                        )
                        
                        if mmr_score > best_score:
                            best_score = mmr_score
                            best_index = idx
                    
                    if best_index != -1:
                        selected_docs.append(documents[best_index])
                        selected_scores.append(best_score)
                        remaining_indices.remove(best_index)
                
                reranked_docs = selected_docs
                reranked_scores = selected_scores
                
            else:
                raise ValueError(f"지원하지 않는 재순위화 방법: {method}")
            
            rerank_metadata["scores"] = reranked_scores
            rerank_metadata["avg_score"] = sum(reranked_scores) / len(reranked_scores) if reranked_scores else 0.0
            
            logger.info(f"문서 재순위화 완료: {method} 방법, {len(reranked_docs)}개 문서")
            return reranked_docs, reranked_scores, rerank_metadata
            
        except Exception as e:
            logger.error(f"문서 재순위화 중 오류: {str(e)}")
            return documents[:top_k], [0.5] * min(top_k, len(documents)), {"error": str(e)}
    
    def get_reranker_info(self) -> Dict[str, Any]:
        """재순위화 시스템 정보 반환"""
        return {
            "diversity_weight": self.diversity_weight,
            "relevance_weight": self.relevance_weight,
            "supported_methods": ["llm", "tfidf", "hybrid", "mmr"],
            "default_method": "hybrid"
        }
