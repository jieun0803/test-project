"""
PDF processing module for extracting and chunking text from financial documents
"""
from typing import List, Dict, Any
import logging
from pathlib import Path

from src.pdf_text import extract_pdf_text, extract_with_pdfplumber, has_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF document processor for financial documents"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file (pdfplumber, pypdf fallback; see src/pdf_text.py)
        """
        try:
            text = extract_pdf_text(pdf_path)
            logger.info(f"Successfully extracted text from {pdf_path}")
            return text

        except Exception:
            logger.exception(f"Error extracting text from {pdf_path}")
            raise

    def extract_text_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Text extraction using pdfplumber only
        """
        return extract_with_pdfplumber(pdf_path)
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page markers
        text = re.sub(r'--- Page \d+ ---', '', text)
        
        # Remove special characters but keep Korean characters
        text = re.sub(r'[^\w\s가-힣.,!?;:()\[\]{}"\'-]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into chunks with metadata
        """
        import re
        
        # Clean the text first
        cleaned_text = self.clean_text(text)
        
        # Split by sentences first (Korean and English)
        sentences = re.split(r'[.!?]\s+', cleaned_text)
        
        chunks = []
        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            # If adding this sentence would exceed chunk size, save current chunk
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append({
                    'id': chunk_id,
                    'text': current_chunk.strip(),
                    'length': len(current_chunk),
                    'metadata': {
                        'chunk_id': chunk_id,
                        'chunk_size': self.chunk_size
                    }
                })
                chunk_id += 1
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk if it exists
        if current_chunk.strip():
            chunks.append({
                'id': chunk_id,
                'text': current_chunk.strip(),
                'length': len(current_chunk),
                'metadata': {
                    'chunk_id': chunk_id,
                    'chunk_size': self.chunk_size
                }
            })
        
        logger.info(f"Created {len(chunks)} chunks from text")
        return chunks
    
    def process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Complete PDF processing pipeline
        """
        try:
            # Extract text (pdfplumber, then pypdf if it yields no text)
            text = self.extract_text_from_pdf(pdf_path)

            if not has_text(text):
                raise ValueError("No text could be extracted from the PDF")
            
            # Chunk the text
            chunks = self.chunk_text(text)
            
            logger.info(f"Successfully processed PDF: {pdf_path}")
            logger.info(f"Total chunks created: {len(chunks)}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
