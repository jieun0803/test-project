"""
PDF processing module for extracting and chunking text from financial documents
"""
import pdfplumber  # MIT
from pypdf import PdfReader  # BSD-3-Clause (fallback)
from typing import List, Dict, Any
import logging
import re
from pathlib import Path

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
        Extract text from PDF file using pdfplumber.
        (PyMuPDF was removed: AGPL-3.0 is blocked by .cursor/oss-policy.md)
        """
        try:
            text = self.extract_text_with_pdfplumber(pdf_path)
            logger.info(f"Successfully extracted text from {pdf_path}")
            return text

        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            raise

    def extract_text_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Text extraction using pdfplumber (one page marker per page, as before)
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page.extract_text() or ""

            logger.info(f"Successfully extracted text using pdfplumber from {pdf_path}")
            return text

        except Exception as e:
            logger.error(f"Error extracting text with pdfplumber from {pdf_path}: {str(e)}")
            raise

    def extract_text_with_pypdf(self, pdf_path: str) -> str:
        """
        Fallback text extraction using pypdf
        """
        try:
            text = ""
            for page_num, page in enumerate(PdfReader(pdf_path).pages):
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.extract_text() or ""

            logger.info(f"Successfully extracted text using pypdf from {pdf_path}")
            return text

        except Exception as e:
            logger.error(f"Error extracting text with pypdf from {pdf_path}: {str(e)}")
            raise
    
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
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)
            
            # If extraction is empty (only page markers), try pypdf
            if not re.sub(r'--- Page \d+ ---', '', text).strip():
                text = self.extract_text_with_pypdf(pdf_path)

            if not re.sub(r'--- Page \d+ ---', '', text).strip():
                raise ValueError("No text could be extracted from the PDF")
            
            # Chunk the text
            chunks = self.chunk_text(text)
            
            logger.info(f"Successfully processed PDF: {pdf_path}")
            logger.info(f"Total chunks created: {len(chunks)}")
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {str(e)}")
            raise
