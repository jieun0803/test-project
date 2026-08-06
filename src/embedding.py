"""
Upstage Solar 임베딩과 ChromaDB를 사용한 임베딩 및 벡터 데이터베이스 모듈
"""
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_upstage import UpstageEmbeddings
from langchain.schema import Document
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import os

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialEmbeddingStore:
    """Upstage Solar 임베딩과 ChromaDB를 사용한 금융 문서 임베딩 스토어"""
    
    def __init__(self, 
                 persist_directory: str = "./vectordb",
                 embedding_model: str = "solar-embedding-1-large-passage",
                 collection_name: str = "financial_documents"):
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        self.collection_name = collection_name
        
        # 환경변수에서 API 키 가져오기
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise ValueError("UPSTAGE_API_KEY 환경변수가 필요합니다")
        
        # 임베딩 초기화
        self.embeddings = UpstageEmbeddings(
            model=embedding_model,
            upstage_api_key=api_key
        )
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 벡터 스토어 초기화
        self.vectorstore = None
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """ChromaDB 벡터 스토어 초기화"""
        try:
            # 컬렉션 존재 여부 확인
            try:
                existing_collection = self.client.get_collection(self.collection_name)
                logger.info(f"기존 컬렉션 발견: {self.collection_name}")
            except:
                logger.info(f"새 컬렉션 생성: {self.collection_name}")
            
            self.vectorstore = Chroma(
                client=self.client,
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
            logger.info("벡터 스토어가 성공적으로 초기화되었습니다")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
        """
        벡터 스토어에 문서 추가
        
        Args:
            documents: 'text' 필드를 가진 문서 청크 목록
            metadata: 문서에 대한 추가 메타데이터
        """
        try:
            # LangChain 문서로 변환
            langchain_docs = []
            for i, doc in enumerate(documents):
                langchain_doc = Document(
                    page_content=doc['text'],
                    metadata={
                        'chunk_id': doc.get('id', i),
                        'chunk_length': doc.get('length', len(doc['text'])),
                        'source': metadata.get('source', 'unknown') if metadata else 'unknown',
                        'document_type': metadata.get('document_type', 'financial_terms') if metadata else 'financial_terms',
                        **doc.get('metadata', {})
                    }
                )
                langchain_docs.append(langchain_doc)
            
            # 벡터 스토어에 추가
            self.vectorstore.add_documents(langchain_docs)
            logger.info(f"Added {len(langchain_docs)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        유사도 검색 수행
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            
        Returns:
            유사한 문서 목록
        """
        try:
            results = self.vectorstore.similarity_search(query, k=k)
            logger.info(f"Found {len(results)} similar documents for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            raise
    
    def similarity_search_with_score(self, query: str, k: int = 5) -> List[tuple]:
        """
        점수와 함께 유사도 검색 수행
        
        Args:
            query: 검색 쿼리
            k: 반환할 문서 수
            
        Returns:
            (문서, 점수) 튜플 목록
        """
        try:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            logger.info(f"Found {len(results)} similar documents with scores for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error performing similarity search with score: {str(e)}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the vector store collection"""
        try:
            collection = self.client.get_collection(self.collection_name)
            count = collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory)
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {"error": str(e)}
    
    def delete_collection(self):
        """Delete the entire collection (use with caution)"""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Collection deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise
    
    def reset_vectorstore(self):
        """Reset the vector store by deleting and recreating"""
        try:
            self.delete_collection()
            self._initialize_vectorstore()
            logger.info("Vector store reset successfully")
        except Exception as e:
            logger.error(f"Error resetting vector store: {str(e)}")
            raise
    
    def load_existing_vectorstore(self) -> bool:
        """
        Load existing vector store if it exists
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            collection = self.client.get_collection(self.collection_name)
            count = collection.count()
            if count > 0:
                logger.info(f"Loaded existing vector store with {count} documents")
                return True
            else:
                logger.info("Vector store exists but is empty")
                return False
        except Exception as e:
            logger.info(f"No existing vector store found: {str(e)}")
            return False
