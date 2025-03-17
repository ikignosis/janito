"""
Specialized functionality for handling news aggregator sites.
"""

from typing import Tuple, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re

from janito.tools.rich_console import print_info, print_success, print_warning
from janito.tools.usage_tracker import track_usage
from janito.tools.fetch_webpage.utils import SITE_SPECIFIC_STRATEGIES
# Import moved to function to avoid circular imports
from janito.tools.fetch_webpage.extractors import extract_clean_text
from janito.tools.fetch_webpage.chunking import chunk_large_content


@track_usage('web_content')
def fetch_and_extract_news_aggregator(url: str, max_stories: int = 15) -> Tuple[str, bool]:
    """
    Specialized extraction for news aggregator sites like Google News.
    
    Args:
        url: The URL of the news aggregator site
        max_stories: Maximum number of stories to extract
        
    Returns:
        A tuple containing (extracted_content, is_error)
    """
    domain = urlparse(url).netloc
    
    # Check if we have a specific strategy for this domain
    strategy = None
    for site_domain, site_strategy in SITE_SPECIFIC_STRATEGIES.items():
        if site_domain in domain:
            strategy = site_strategy
            break
    
    if not strategy:
        print_warning(f"No specific strategy found for {domain}. Using general extraction.", "News Extraction")
        from janito.tools.fetch_webpage.core import fetch_and_extract
        return fetch_and_extract(url)
    
    print_info(f"Using specialized extraction for {domain}", "News Extraction")
    
    # Import here to avoid circular imports
    from janito.tools.fetch_webpage.core import fetch_webpage
    
    # Fetch the page
    html_content, is_error = fetch_webpage(url, max_size=2000000)  # Limit to 2MB for news sites
    
    if is_error:
        return html_content, True
    
    # Extract content using the site-specific strategy
    extracted_text = extract_clean_text(
        html_content, 
        method=strategy.get("method", "beautifulsoup"),
        url=url,
        target_strings=strategy.get("target_strings", [])
    )
    
    if not extracted_text or len(extracted_text) < 100:
        return f"Could not extract meaningful content from {url}", True
    
    # Get article titles and snippets using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    article_titles = []
    article_snippets = []
    
    # Use site-specific selectors
    selectors = strategy.get("article_selectors", ["article", "h3", "h4"])
    
    # Find article elements
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements[:max_stories*2]:  # Get more than we need, then filter
            text = element.get_text(strip=True)
            if text and len(text) > 15:
                if len(text) < 200:  # Likely a title
                    if text not in article_titles:
                        article_titles.append(text)
                else:  # Likely a snippet
                    if text not in article_snippets:
                        article_snippets.append(text)
    
    # Limit to requested number of stories
    article_titles = article_titles[:max_stories]
    article_snippets = article_snippets[:max_stories]
    
    # Format the result
    result = ["# Top Stories\n"]
    
    # Add titles and snippets
    for i, title in enumerate(article_titles):
        result.append(f"## {title}")
        # Try to find a matching snippet
        snippet_added = False
        for snippet in article_snippets:
            # Check if any significant words from title appear in snippet
            title_words = set(re.findall(r'\b\w{5,}\b', title.lower()))
            if any(word in snippet.lower() for word in title_words if len(word) > 4):
                result.append(f"{snippet[:300]}...")
                snippet_added = True
                break
        
        if not snippet_added and i < len(article_snippets):
            result.append(f"{article_snippets[i][:300]}...")
        
        result.append("")  # Add spacing between articles
    
    # If we didn't get enough specific articles, add some generic extracted content
    if len(article_titles) < 3:
        # Chunk the generic extracted content
        chunks = chunk_large_content(extracted_text, chunk_size=2000, overlap=200)
        relevant_chunks = []
        
        # Find chunks that look like news
        for chunk in chunks[:10]:
            if any(marker in chunk for marker in [":", " - ", "reports", "according to", "says"]):
                relevant_chunks.append(chunk)
        
        if relevant_chunks:
            result.append("# Additional News Content\n")
            result.append("\n".join(relevant_chunks[:3]))
    
    max_length = strategy.get("max_length", 15000)
    final_text = "\n".join(result)
    
    # Truncate if needed
    if len(final_text) > max_length:
        print_info(f"Truncating content from {len(final_text)} to {max_length} characters", "News Extraction")
        final_text = final_text[:max_length] + "..."
    
    print_success(f"Successfully extracted {len(article_titles)} news stories", "News Extraction")
    return final_text, False