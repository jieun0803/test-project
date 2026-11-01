"""
금융 문서용 PDF 청킹 모듈
금융 용어 및 구조화된 문서에 최적화됨
"""
import fitz  # PyMuPDF
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from typing import List, Dict, Any
import logging
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialDocumentChunker:
    """금융 문서 전용 청커"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 금융 문서 고려사항을 포함한 텍스트 분할기 초기화
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=[
                "\n\n제",  # 조항 헤더 (제1조, 제2조 등)
                "\n\n제",  # 조항 헤더
                "\n\n",    # 단락 구분
                "\n",      # 줄 구분
                ". ",      # 문장 끝
                " ",       # 단어 경계
                ""         # 문자 경계
            ]
        )
    
    def load_pdf_with_pypdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        PyPDFLoader를 사용하여 PDF 로드 (LangChain)
        """
        try:
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            
            # 우리 형식으로 변환
            documents = []
            for i, page in enumerate(pages):
                documents.append({
                    'text': page.page_content,
                    'metadata': {
                        'page_number': i + 1,
                        'source': pdf_path,
                        'chunk_type': 'page'
                    }
                })
            
            logger.info(f"Loaded {len(documents)} pages from {pdf_path}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading PDF with PyPDF: {str(e)}")
            raise
    
    def extract_text_with_pymupdf(self, pdf_path: str) -> str:
        """
        PyMuPDF를 사용하여 텍스트 추출 (복잡한 레이아웃에 더 적합)
        """
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                # 페이지 마커 추가
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page_text
            
            doc.close()
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text with PyMuPDF: {str(e)}")
            raise
    
    def clean_financial_text(self, text: str) -> str:
        """
        금융 문서에 특화된 텍스트 정리
        """
        # 페이지 마커 제거
        text = re.sub(r'--- Page \d+ ---', '', text)
        
        # 조항 헤더 정규화 (제1조, 제2조 등)
        text = re.sub(r'제(\d+)조', r'\n제\1조 ', text)
        
        # 섹션 헤더 정규화 (①, ②, ③ 등)
        text = re.sub(r'[①②③④⑤⑥⑦⑧⑨⑩]', lambda m: f'\n{m.group()} ', text)
        
        # 번호 목록 정규화 (1., 2., 3. 등)
        text = re.sub(r'(\d+)\.', r'\n\1. ', text)
        
        # 과도한 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 특수 문자 제거하되 한국어와 금융 기호는 유지
        text = re.sub(r'[^\w\s가-힣.,!?;:()\[\]{}"\'%원]', '', text)
        
        return text.strip()
    
    def chunk_by_articles(self, text: str) -> List[Dict[str, Any]]:
        """
        조항별로 텍스트 청킹 (제1조, 제2조 등)
        """
        # 조항 헤더로 분할
        articles = re.split(r'(제\d+조)', text)
        
        chunks = []
        chunk_id = 0
        
        for i in range(0, len(articles), 2):
            if i + 1 < len(articles):
                article_header = articles[i]
                article_content = articles[i + 1]
                
                # 정리하고 결합
                full_article = article_header + article_content
                cleaned_article = self.clean_financial_text(full_article)
                
                if len(cleaned_article) > 50:  # 실질적인 조항만 포함
                    chunks.append({
                        'id': chunk_id,
                        'text': cleaned_article,
                        'length': len(cleaned_article),
                        'metadata': {
                            'chunk_id': chunk_id,
                            'chunk_type': 'article',
                            'article_header': article_header.strip(),
                            'chunk_size': self.chunk_size
                        }
                    })
                    chunk_id += 1
        
        return chunks
    
    def chunk_with_langchain(self, text: str) -> List[Dict[str, Any]]:
        """
        LangChain의 RecursiveCharacterTextSplitter를 사용하여 텍스트 청킹
        """
        # 먼저 텍스트 정리
        cleaned_text = self.clean_financial_text(text)
        
        # 문서로 분할
        docs = self.text_splitter.split_text(cleaned_text)
        
        # 우리 형식으로 변환
        chunks = []
        for i, doc_text in enumerate(docs):
            if len(doc_text.strip()) > 50:  # 실질적인 청크만 포함
                chunks.append({
                    'id': i,
                    'text': doc_text.strip(),
                    'length': len(doc_text),
                    'metadata': {
                        'chunk_id': i,
                        'chunk_type': 'langchain_split',
                        'chunk_size': self.chunk_size
                    }
                })
        
        return chunks
    
    def process_pdf(self, pdf_path: str, chunking_method: str = "langchain") -> List[Dict[str, Any]]:
        """
        완전한 PDF 처리 파이프라인
        
        Args:
            pdf_path: PDF 파일 경로
            chunking_method: "langchain" 또는 "articles"
        """
        try:
            # 텍스트 추출
            text = self.extract_text_with_pymupdf(pdf_path)
            
            if not text.strip():
                raise ValueError("PDF에서 텍스트를 추출할 수 없습니다")
            
            # 청킹 방법 선택
            if chunking_method == "articles":
                chunks = self.chunk_by_articles(text)
            else:
                chunks = self.chunk_with_langchain(text)
            
            logger.info(f"Successfully processed PDF: {pdf_path}")
            logger.info(f"Total chunks created: {len(chunks)}")
            logger.info(f"Chunking method: {chunking_method}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
