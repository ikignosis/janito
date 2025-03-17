"""
Functions for chunking large content into manageable pieces.
"""

from typing import List
from janito.tools.rich_console import print_info, print_success


def chunk_large_content(text: str, chunk_size: int = 4000, overlap: int = 500) -> List[str]:
    """
    Split very large text content into manageable chunks suitable for LLM processing.
    
    Args:
        text: The text to chunk
        chunk_size: Target size for each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    print_info(f"Chunking {len(text)} characters of text into ~{chunk_size} character chunks", "Content Chunking")
    
    # Try to split on paragraph breaks first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # If adding this paragraph would exceed chunk size
        if len(current_chunk) + len(para) + 2 > chunk_size:
            # If current chunk is not empty, add it to chunks
            if current_chunk:
                chunks.append(current_chunk)
                # Start new chunk with overlap from previous chunk
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                # If paragraph itself is bigger than chunk size, split it
                if len(para) > chunk_size:
                    words = para.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > chunk_size:
                            chunks.append(temp_chunk)
                            # Start new chunk with overlap
                            if overlap > 0 and len(temp_chunk) > overlap:
                                temp_chunk = temp_chunk[-overlap:] + " " + word
                            else:
                                temp_chunk = word
                        else:
                            if temp_chunk:
                                temp_chunk += " " + word
                            else:
                                temp_chunk = word
                    if temp_chunk:
                        current_chunk = temp_chunk
                else:
                    chunks.append(para)
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    print_success(f"Text chunked into {len(chunks)} segments", "Content Chunking")
    return chunks