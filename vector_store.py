"""
Vector store implementation using ChromaDB and Upstage Solar embeddings
"""
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain_upstage import UpstageEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialVectorStore:
    """Vector store for financial documents using ChromaDB and Upstage embeddings"""
    
    def __init__(self, 
                 persist_directory: str = "./vector_db",
                 embedding_model: str = "solar-embedding-1-large-passage",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = UpstageEmbeddings(
            model=embedding_model,
            upstage_api_key="your_api_key_here"  # Will be set from config
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize vector store
        self.vectorstore = None
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """Initialize the ChromaDB vector store"""
        try:
            self.vectorstore = Chroma(
                client=self.client,
                collection_name="financial_documents",
                embedding_function=self.embeddings,
                persist_directory=str(self.persist_directory)
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]], metadata: Dict[str, Any] = None):
        """
        Add documents to the vector store
        
        Args:
            documents: List of document chunks with 'text' field
            metadata: Additional metadata for the documents
        """
        try:
            # Convert to LangChain documents
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
            
            # Add to vector store
            self.vectorstore.add_documents(langchain_docs)
            logger.info(f"Added {len(langchain_docs)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            raise
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        Perform similarity search
        
        Args:
            query: Search query
            k: Number of documents to return
            
        Returns:
            List of similar documents
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
        Perform similarity search with scores
        
        Args:
            query: Search query
            k: Number of documents to return
            
        Returns:
            List of (document, score) tuples
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
            collection = self.client.get_collection("financial_documents")
            count = collection.count()
            return {
                "total_documents": count,
                "collection_name": "financial_documents",
                "persist_directory": str(self.persist_directory)
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {"error": str(e)}
    
    def delete_collection(self):
        """Delete the entire collection (use with caution)"""
        try:
            self.client.delete_collection("financial_documents")
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
