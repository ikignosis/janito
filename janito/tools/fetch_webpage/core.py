"""
Core functionality for fetching web pages and extracting content.
"""

import requests
from typing import Tuple, List, Optional
from urllib.parse import urlparse
from janito.tools.rich_console import print_info, print_success, print_error, print_warning
from janito.tools.usage_tracker import track_usage

from janito.tools.fetch_webpage.extractors import extract_clean_text
# Import moved to fetch_and_extract function to avoid circular imports
from janito.tools.fetch_webpage.utils import SITE_SPECIFIC_STRATEGIES


@track_usage('web_requests')
def fetch_webpage(url: str, headers: dict = None, timeout: int = 30, max_size: int = 5000000, 
                 target_strings: List[str] = None) -> Tuple[str, bool]:
    """
    Fetch the content of a web page from a given URL.
    
    Args:
        url: The URL of the web page to fetch
        headers: Optional HTTP headers to include in the request (default: None)
        timeout: Request timeout in seconds (default: 30)
        max_size: Maximum size in bytes to download (default: 5MB)
        target_strings: Optional list of strings to target specific content sections
        
    Returns:
        A tuple containing (message, is_error)
    """
    print_info(f"Fetching content from URL: {url}", "Web Fetch")
    
    try:
        # Set default headers if none provided
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        
        # Make the HTTP request with streaming enabled
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        
        # Raise an exception for HTTP errors
        response.raise_for_status()
        
        # Check content length before downloading fully
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > max_size:
            warning_msg = f"Content size ({int(content_length)/1000000:.1f}MB) exceeds max size ({max_size/1000000:.1f}MB). Aborting download."
            print_warning(warning_msg, "Web Fetch")
            return warning_msg, True
            
        # Download content with size limit
        content_bytes = b''
        for chunk in response.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
            content_bytes += chunk
            if len(content_bytes) > max_size:
                warning_msg = f"Download exceeded max size ({max_size/1000000:.1f}MB). Truncating."
                print_warning(warning_msg, "Web Fetch")
                break
                
        # Get the content
        content = content_bytes.decode('utf-8', errors='replace')
        
        # If target strings are provided, extract only the relevant sections
        if target_strings and len(target_strings) > 0:
            print_info(f"Targeting specific content using {len(target_strings)} search strings", "Web Fetch")
            from janito.tools.fetch_webpage.extractors import extract_targeted_content
            targeted_content = extract_targeted_content(content, target_strings)
            
            if targeted_content:
                print_success(f"Successfully targeted specific content based on search strings", "Web Fetch")
                # Create a summary with first 300 chars of targeted content
                content_preview = targeted_content[:300] + "..." if len(targeted_content) > 300 else targeted_content
                summary = f"Successfully fetched targeted content from {url}\n\nContent preview:\n{content_preview}"
                print_success(f"Successfully fetched targeted content from {url} ({len(targeted_content)} bytes)", "Web Fetch")
                return targeted_content, False
            else:
                print_warning(f"Could not find content matching the target strings. Returning full content.", "Web Fetch")
        
        # Create a summary message with first 300 chars of content
        content_preview = content[:300] + "..." if len(content) > 300 else content
        summary = f"Successfully fetched content from {url}\n\nContent preview:\n{content_preview}"
        
        print_success(f"Successfully fetched content from {url} ({len(content)} bytes)", "Web Fetch")
        
        # Return the full content
        return content, False
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching web page: {str(e)}"
        print_error(error_msg, "Web Fetch Error")
        return error_msg, True


@track_usage('web_content')
def fetch_and_extract(url: str, extract_method: str = 'trafilatura', 
                     max_length: int = 10000,
                     target_strings: List[str] = None) -> Tuple[str, bool]:
    """
    Fetch a webpage and extract its main content in a format suitable for LLM processing.
    
    Args:
        url: The URL to fetch
        extract_method: Content extraction method ('trafilatura', 'newspaper', 'beautifulsoup', 'all')
        max_length: Maximum length of text to return
        target_strings: Optional list of strings to target specific content sections
        
    Returns:
        A tuple containing (extracted_content, is_error)
    """
    # Check if this is a news aggregator site that needs special handling
    domain = urlparse(url).netloc
    for site_domain in SITE_SPECIFIC_STRATEGIES.keys():
        if site_domain in domain:
            print_info(f"Detected news aggregator site: {domain}. Using specialized extraction.", "Content Extraction")
            # Import here to avoid circular imports
            from janito.tools.fetch_webpage.news import fetch_and_extract_news_aggregator
            return fetch_and_extract_news_aggregator(url)
    
    # If target strings are provided, pass them directly to fetch_webpage for efficiency
    if target_strings and len(target_strings) > 0:
        html_content, is_error = fetch_webpage(url, target_strings=target_strings)
    else:
        html_content, is_error = fetch_webpage(url)
    
    if is_error:
        return html_content, True
    
    extracted_text = extract_clean_text(html_content, method=extract_method, url=url)
    
    if not extracted_text or len(extracted_text) < 100:
        return f"Could not extract meaningful content from {url}", True
        
    # If target strings were provided but not already handled by fetch_webpage
    if target_strings and len(target_strings) > 0 and not any(target in extracted_text for target in target_strings if len(target) > 3):
        from janito.tools.fetch_webpage.extractors import extract_targeted_content
        targeted_content = extract_targeted_content(html_content, target_strings)
        if targeted_content:
            print_success(f"Successfully extracted targeted content based on {len(target_strings)} search strings", 
                         "Targeted Extraction")
            extracted_text = targeted_content
    
    # Truncate if needed
    if len(extracted_text) > max_length:
        print_info(f"Truncating content from {len(extracted_text)} to {max_length} characters", "Content Extraction")
        extracted_text = extracted_text[:max_length] + "..."
        
    # Check if the content is still too large for an LLM (rough estimate)
    estimated_tokens = len(extracted_text.split())
    if estimated_tokens > 10000:  # Conservative estimate for token limits
        print_warning(f"Extracted content still very large (~{estimated_tokens} words). Consider using chunk_large_content()", 
                     "Content Extraction")
    
    print_success(f"Successfully extracted {len(extracted_text)} characters of content", "Content Extraction")
    return extracted_text, False