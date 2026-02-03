"""
Document processing and embedding generation
"""
import os
from typing import List, Dict, Any
from pathlib import Path
import pypdf
from sentence_transformers import SentenceTransformer
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, RAW_DATA_DIR
from src.utils.logger import get_logger
from src.utils.text_splitter import SimpleTextSplitter

logger = get_logger(__name__)


class DocumentProcessor:
    """Process documents and prepare them for vectorization"""
    
    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = SimpleTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Initialized DocumentProcessor with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract text from PDF with page metadata"""
        logger.info(f"Extracting text from: {pdf_path}")
        
        documents = []
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    
                    if text.strip():
                        documents.append({
                            "text": text,
                            "metadata": {
                                "source": pdf_path.name,
                                "page": page_num + 1,
                                "type": "pdf"
                            }
                        })
            
            logger.info(f"Extracted {len(documents)} pages from {pdf_path.name}")
            return documents
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {str(e)}")
            raise
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split documents into chunks while preserving metadata"""
        logger.info(f"Chunking {len(documents)} documents")
        
        chunked_docs = []
        for doc in documents:
            text = doc["text"]
            metadata = doc["metadata"]
            
            # Split text into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Create document for each chunk with metadata
            for idx, chunk in enumerate(chunks):
                chunked_docs.append({
                    "text": chunk,
                    "metadata": {
                        **metadata,
                        "chunk_id": idx,
                        "total_chunks": len(chunks)
                    }
                })
        
        logger.info(f"Created {len(chunked_docs)} chunks")
        return chunked_docs
    
    def add_scenario_metadata(self, documents: List[Dict[str, Any]], 
                            scenario_category: str = None) -> List[Dict[str, Any]]:
        """Add scenario-specific metadata to documents"""
        for doc in documents:
            if scenario_category:
                doc["metadata"]["scenario_category"] = scenario_category
        
        return documents
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            embeddings = self.embedding_model.encode(
                texts, 
                show_progress_bar=True,
                convert_to_numpy=True
            )
            
            logger.info(f"Generated embeddings with shape: {embeddings.shape}")
            return embeddings.tolist()
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def process_samhsa_document(self) -> List[Dict[str, Any]]:
        """Process the SAMHSA trauma-informed care document"""
        samhsa_path = RAW_DATA_DIR / "SAMHSA_Trauma-2014__1_.pdf"
        
        if not samhsa_path.exists():
            logger.error(f"SAMHSA document not found at {samhsa_path}")
            raise FileNotFoundError(f"SAMHSA document not found at {samhsa_path}")
        
        # Extract text from PDF
        documents = self.extract_text_from_pdf(samhsa_path)
        
        # Add source-specific metadata
        for doc in documents:
            doc["metadata"]["document_type"] = "foundational_framework"
            doc["metadata"]["category"] = "trauma_informed_care"
        
        # Chunk documents
        chunked_docs = self.chunk_documents(documents)
        
        return chunked_docs
    
    def process_all_documents(self) -> List[Dict[str, Any]]:
        """Process all documents in the raw data directory"""
        all_documents = []
        
        # Process SAMHSA document
        logger.info("Processing SAMHSA document...")
        samhsa_docs = self.process_samhsa_document()
        all_documents.extend(samhsa_docs)
        
        # Here you would add processing for other documents
        # For example, scenario documents, referral information, etc.
        
        logger.info(f"Total processed documents: {len(all_documents)}")
        return all_documents


if __name__ == "__main__":
    # Test document processing
    processor = DocumentProcessor()
    docs = processor.process_samhsa_document()
    
    print(f"\nProcessed {len(docs)} document chunks")
    print(f"\nSample chunk:")
    print(f"Text: {docs[0]['text'][:200]}...")
    print(f"Metadata: {docs[0]['metadata']}")