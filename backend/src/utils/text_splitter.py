"""
Simple text splitter
"""
from typing import List


class SimpleTextSplitter:
    """Simple text splitter with overlap"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize text splitter
        
        Args:
            chunk_size: Maximum size of each chunk (in characters)
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to split
        
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Calculate end position
            end = start + self.chunk_size
            
            # If this is not the last chunk and we're in the middle of a word,
            # try to find a good breaking point (space, newline, period)
            if end < text_length:
                # Look for good break points in the last 100 characters
                search_start = max(end - 100, start)
                
                # Try to break at paragraph
                last_double_newline = text.rfind('\n\n', search_start, end)
                if last_double_newline != -1:
                    end = last_double_newline + 2
                else:
                    # Try to break at sentence
                    last_period = text.rfind('. ', search_start, end)
                    if last_period != -1:
                        end = last_period + 2
                    else:
                        # Try to break at newline
                        last_newline = text.rfind('\n', search_start, end)
                        if last_newline != -1:
                            end = last_newline + 1
                        else:
                            # Try to break at space
                            last_space = text.rfind(' ', search_start, end)
                            if last_space != -1:
                                end = last_space + 1
            
            # Extract chunk
            chunk = text[start:end].strip()
            
            if chunk:
                chunks.append(chunk)
            
            # Move to next chunk with overlap
            start = end - self.chunk_overlap
            
            # Ensure we make progress
            if start <= (len(chunks[-1]) if chunks else 0):
                start = end
        
        return chunks