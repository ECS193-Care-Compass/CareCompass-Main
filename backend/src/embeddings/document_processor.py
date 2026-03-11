"""
Document processing and embedding generation
"""
import os
from typing import List, Dict, Any
from pathlib import Path
import pypdf
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP, RAW_DATA_DIR
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
        # Removed: SentenceTransformer model load
        # ChromaDB's embedding function in VectorStore handles embeddings automatically
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
    
    def process_hiv_documents(self) -> List[Dict[str, Any]]:
        """Process CDC HIV testing and partner services documents"""
        hiv_docs = [
            {
                "filename": "cdc-hiv-lsht-treatment-brochure-partner-services-provider.pdf",
                "document_type": "referral_resource",
                "category": "hiv_partner_services",
                "scenario_categories": ["immediate_followup"],
            },
        ]
        
        all_chunks = []
        for doc_info in hiv_docs:
            pdf_path = RAW_DATA_DIR / doc_info["filename"]
            
            if not pdf_path.exists():
                logger.warning(f"HIV document not found: {pdf_path}")
                continue
            
            # Extract text from PDF
            documents = self.extract_text_from_pdf(pdf_path)
            
            # Add source-specific metadata
            for doc in documents:
                doc["metadata"]["document_type"] = doc_info["document_type"]
                doc["metadata"]["category"] = doc_info["category"]
                # Store primary scenario category for filtering
                doc["metadata"]["scenario_category"] = doc_info["scenario_categories"][0]
                doc["metadata"]["scenario_categories"] = ",".join(doc_info["scenario_categories"])
            
            # Chunk documents
            chunked = self.chunk_documents(documents)
            all_chunks.extend(chunked)
            logger.info(f"Processed {doc_info['filename']}: {len(chunked)} chunks")
        
        return all_chunks
    
    def process_survivor_resource_documents(self) -> List[Dict[str, Any]]:
        """Process survivor rights, local resources, and forensic exam protocol documents"""
        survivor_docs = [
            {
                "filename": "marsy-card-english.pdf",
                "document_type": "patient_education",
                "category": "victim_rights",
                "scenario_categories": ["legal_advocacy"],
            },
            {
                "filename": "Sac Sheriff SA TriFold Pamphlet Jan2023.pdf",
                "document_type": "referral_resource",
                "category": "local_resources",
                "scenario_categories": ["practical_social", "legal_advocacy"],
            },
            {
                "filename": "Survivors-Right-to-Time-Off-FAQs_English.pdf",
                "document_type": "patient_education",
                "category": "employment_rights",
                "scenario_categories": ["legal_advocacy", "practical_social"],
            },
            {
                "filename": "SAFE Protocol final 9.10.24.pdf",
                "document_type": "clinical_protocol",
                "category": "forensic_exam",
                "scenario_categories": ["immediate_followup"],
            },
        ]

        all_chunks = []
        for doc_info in survivor_docs:
            pdf_path = RAW_DATA_DIR / doc_info["filename"]

            if not pdf_path.exists():
                logger.warning(f"Survivor resource document not found: {pdf_path}")
                continue

            documents = self.extract_text_from_pdf(pdf_path)

            for doc in documents:
                doc["metadata"]["document_type"] = doc_info["document_type"]
                doc["metadata"]["category"] = doc_info["category"]
                doc["metadata"]["scenario_category"] = doc_info["scenario_categories"][0]
                doc["metadata"]["scenario_categories"] = ",".join(doc_info["scenario_categories"])

            chunked = self.chunk_documents(documents)
            all_chunks.extend(chunked)
            logger.info(f"Processed {doc_info['filename']}: {len(chunked)} chunks")

        return all_chunks

    def process_all_documents(self) -> List[Dict[str, Any]]:
        """Process all documents in the raw data directory"""
        all_documents = []
        
        # Process SAMHSA document
        logger.info("Processing SAMHSA document...")
        samhsa_docs = self.process_samhsa_document()
        all_documents.extend(samhsa_docs)
        
        # Process HIV documents
        logger.info("Processing HIV documents...")
        hiv_docs = self.process_hiv_documents()
        all_documents.extend(hiv_docs)

        # Process survivor resource documents
        logger.info("Processing survivor resource documents...")
        survivor_docs = self.process_survivor_resource_documents()
        all_documents.extend(survivor_docs)

        logger.info(f"Total processed documents: {len(all_documents)}")
        return all_documents


if __name__ == "__main__":
    # Test document processing
    processor = DocumentProcessor()
    
    print("=" * 60)
    print("Testing SAMHSA document processing...")
    print("=" * 60)
    docs = processor.process_samhsa_document()
    print(f"Processed {len(docs)} chunks")
    if docs:
        print(f"Sample chunk text: {docs[0]['text'][:200]}...")
        print(f"Sample metadata: {docs[0]['metadata']}")
    
    print("\n" + "=" * 60)
    print("Testing HIV document processing...")
    print("=" * 60)
    hiv_docs = processor.process_hiv_documents()
    print(f"Processed {len(hiv_docs)} chunks")
    if hiv_docs:
        print(f"Sample chunk text: {hiv_docs[0]['text'][:200]}...")
        print(f"Sample metadata: {hiv_docs[0]['metadata']}")
    
    print("\n" + "=" * 60)
    print("Testing full pipeline...")
    print("=" * 60)
    all_docs = processor.process_all_documents()
    print(f"Total chunks across all documents: {len(all_docs)}")