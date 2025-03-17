"""
Utility functions and constants for the fetch_webpage package.
"""

import re
import html
import unicodedata

# Dictionary of known content types and extraction strategies
SITE_SPECIFIC_STRATEGIES = {
    "news.google.com": {
        "method": "beautifulsoup",
        "target_strings": [
            "Top stories", "Headlines", "For you",
            "U.S.", "World", "Business", "Technology",
            "Entertainment", "Sports", "Science", "Health"
        ],
        "max_length": 20000,
        "article_selectors": ["article", "h3", "h4", ".ipQwMb", ".BOz6fb", ".MgUUmf"]
    },
    "news.yahoo.com": {
        "method": "beautifulsoup",
        "target_strings": ["Top Stories", "Trending News"],
        "max_length": 20000,
        "article_selectors": [".js-stream-content", ".js-content", "h3", "h2"]
    },
    "msn.com": {
        "method": "newspaper",
        "max_length": 20000,
        "target_strings": ["Top stories", "Headlines"]
    },
    "reddit.com": {
        "method": "trafilatura",
        "target_strings": ["comments", "Posted by", "communities"],
        "max_length": 15000,
        "article_selectors": [".Post", "h1", "h2", ".title"]
    },
    "twitter.com": {
        "method": "beautifulsoup",
        "target_strings": ["Trending", "Following", "For you"],
        "max_length": 15000,
        "article_selectors": [".tweet", ".content", "[data-testid='tweet']"]
    }
}


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace, normalizing Unicode, etc.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned text
    """
    # Decode HTML entities
    text = html.unescape(text)
    
    # Normalize Unicode characters
    text = unicodedata.normalize('NFKC', text)
    
    # Remove excess whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove duplicate newlines (but preserve paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove very short lines that are often menu items or UI elements
    lines = [line for line in text.split('\n') if len(line.strip()) > 20]
    text = '\n'.join(lines)
    
    return text.strip()


def similar_text(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """
    Check if two text strings are similar using a simple similarity metric.
    
    Args:
        text1: First text string
        text2: Second text string
        threshold: Similarity threshold (0-1)
        
    Returns:
        True if texts are similar, False otherwise
    """
    # Simple character-based similarity
    if len(text1) == 0 or len(text2) == 0:
        return False
    
    # If one string is much shorter than the other, they're not similar
    if len(text1) < len(text2) * 0.5 or len(text2) < len(text1) * 0.5:
        return False
    
    # Check for substring relationship
    if text1 in text2 or text2 in text1:
        return True
    
    # Simple character-based similarity for short strings
    if len(text1) < 200 and len(text2) < 200:
        shorter = text1 if len(text1) <= len(text2) else text2
        longer = text2 if len(text1) <= len(text2) else text1
        
        matches = sum(c1 == c2 for c1, c2 in zip(shorter, longer))
        return matches / len(shorter) >= threshold
    
    return False