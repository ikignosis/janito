"""
Webpage Content Extractor Package

A comprehensive tool for extracting clean, relevant content from web pages
for processing with LLMs. Features include:
- General content extraction with multiple methods
- Specialized handling for news aggregator sites
- Targeted extraction based on specific search strings
- Chunking for large content
- Structured content extraction

Dependencies:
- requests
- beautifulsoup4
- trafilatura
- newspaper3k

Author: Claude (Anthropic)
"""

from janito.tools.fetch_webpage.core import fetch_webpage, fetch_and_extract
from janito.tools.fetch_webpage.news import fetch_and_extract_news_aggregator
from janito.tools.fetch_webpage.extractors import extract_clean_text, extract_targeted_content, extract_structured_content
from janito.tools.fetch_webpage.chunking import chunk_large_content

__all__ = [
    'fetch_webpage',
    'fetch_and_extract',
    'fetch_and_extract_news_aggregator',
    'extract_clean_text',
    'extract_targeted_content',
    'extract_structured_content',
    'chunk_large_content'
]