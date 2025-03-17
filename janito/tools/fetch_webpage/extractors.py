"""
Content extraction methods for web pages.
"""

from typing import List, Dict, Union, Optional
from bs4 import BeautifulSoup
import trafilatura
from newspaper import Article
import re

from janito.tools.rich_console import print_info, print_success, print_warning
from janito.tools.fetch_webpage.utils import clean_text, similar_text


def extract_clean_text(html_content: str, method: str = 'trafilatura', 
                       url: Optional[str] = None, target_strings: List[str] = None) -> str:
    """
    Extract clean, relevant text from HTML content using various methods.
    
    Args:
        html_content: The HTML content to extract text from
        method: The extraction method to use ('trafilatura', 'newspaper', 'beautifulsoup', 'all')
        url: Optional URL for methods that require it (like newspaper)
        target_strings: Optional list of strings to target specific content sections
        
    Returns:
        Extracted text content
    """
    print_info(f"Extracting content using method: {method}", "Content Extraction")
    
    extracted_text = ""
    
    if method == 'trafilatura' or method == 'all':
        try:
            traf_text = trafilatura.extract(html_content, include_links=False, 
                                           include_tables=False, include_images=False,
                                           favor_precision=True)
            if traf_text and len(traf_text) > 100:
                if method == 'trafilatura':
                    print_success("Successfully extracted content with Trafilatura", "Content Extraction")
                    return clean_text(traf_text)
                extracted_text = traf_text
                print_success("Successfully extracted content with Trafilatura", "Content Extraction")
        except Exception as e:
            print_warning(f"Trafilatura extraction error: {str(e)}", "Content Extraction")
    
    if method == 'newspaper' or method == 'all':
        if not url:
            print_warning("URL required for newspaper extraction but not provided", "Content Extraction")
        else:
            try:
                article = Article(url)
                article.download(html_content)
                article.parse()
                np_text = article.text
                if np_text and len(np_text) > 100:
                    if method == 'newspaper':
                        print_success("Successfully extracted content with Newspaper3k", "Content Extraction")
                        return clean_text(np_text)
                    if not extracted_text or len(np_text) > len(extracted_text):
                        extracted_text = np_text
                        print_success("Successfully extracted content with Newspaper3k", "Content Extraction")
            except Exception as e:
                print_warning(f"Newspaper extraction error: {str(e)}", "Content Extraction")
    
    if method == 'beautifulsoup' or method == 'all':
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script, style, and other non-content elements
            for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
                element.decompose()
            
            # Extract text from paragraph and heading tags
            paragraphs = []
            for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'article']):
                text = tag.get_text(strip=True)
                if text and len(text) > 20:  # Skip very short pieces that might be UI elements
                    paragraphs.append(text)
            
            bs_text = "\n\n".join(paragraphs)
            if bs_text and len(bs_text) > 100:
                if method == 'beautifulsoup':
                    print_success("Successfully extracted content with BeautifulSoup", "Content Extraction")
                    return clean_text(bs_text)
                if not extracted_text or len(bs_text) > len(extracted_text):
                    extracted_text = bs_text
                    print_success("Successfully extracted content with BeautifulSoup", "Content Extraction")
        except Exception as e:
            print_warning(f"BeautifulSoup extraction error: {str(e)}", "Content Extraction")
    
    if not extracted_text:
        print_warning("Could not extract meaningful content with any method", "Content Extraction")
        # Fall back to the raw text with HTML tags removed
        extracted_text = BeautifulSoup(html_content, 'html.parser').get_text(separator='\n')
    
    return clean_text(extracted_text)


def extract_targeted_content(html_content: str, target_strings: List[str], 
                          context_size: int = 500) -> str:
    """
    Extract content sections that contain specific target strings.
    
    Args:
        html_content: The HTML content to search within
        target_strings: List of strings to search for in the content
        context_size: Number of characters to include before and after each match
        
    Returns:
        Extracted content focusing on sections containing target strings
    """
    if not target_strings:
        return ""
    
    print_info(f"Extracting content targeted around {len(target_strings)} search strings", "Targeted Extraction")
    
    # First clean the HTML to make text extraction easier
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, and other non-content elements
    for element in soup(['script', 'style', 'header', 'footer', 'nav']):
        element.decompose()
    
    # Get the full text content
    full_text = soup.get_text(' ', strip=True)
    full_text = re.sub(r'\s+', ' ', full_text)  # Normalize whitespace
    
    matched_sections = []
    for target in target_strings:
        if not target or len(target) < 3:
            continue
            
        # Try exact match first
        if target in full_text:
            indices = [m.start() for m in re.finditer(re.escape(target), full_text)]
            for idx in indices:
                start = max(0, idx - context_size)
                end = min(len(full_text), idx + len(target) + context_size)
                section = full_text[start:end]
                # Add ellipsis if we're showing a fragment
                if start > 0:
                    section = "..." + section
                if end < len(full_text):
                    section = section + "..."
                matched_sections.append(section)
        else:
            # Try fuzzy search if no exact match (looking for words in the target string)
            words = [w for w in target.lower().split() if len(w) > 3]
            if words:
                for word in words:
                    pattern = r'\b' + re.escape(word) + r'\b'
                    matches = list(re.finditer(pattern, full_text.lower()))
                    for match in matches[:3]:  # Limit to first 3 matches per word
                        idx = match.start()
                        start = max(0, idx - context_size)
                        end = min(len(full_text), idx + len(word) + context_size)
                        section = full_text[start:end]
                        if start > 0:
                            section = "..." + section
                        if end < len(full_text):
                            section = section + "..."
                        matched_sections.append(section)
    
    # Deduplicate similar sections
    unique_sections = []
    for section in matched_sections:
        if not any(similar_text(section, existing, threshold=0.7) for existing in unique_sections):
            unique_sections.append(section)
    
    if not unique_sections:
        print_warning("No content sections found matching the target strings", "Targeted Extraction")
        return ""
    
    # Join the sections with paragraph breaks
    result = "\n\n".join(unique_sections)
    print_success(f"Found {len(unique_sections)} relevant content sections", "Targeted Extraction")
    
    return clean_text(result)


def extract_structured_content(html_content: str, url: str = None, 
                              target_strings: List[str] = None) -> Dict[str, Union[str, List[str]]]:
    """
    Extract structured content from a webpage, including title, main text, and key points.
    
    Args:
        html_content: The HTML content to extract from
        url: Optional URL for methods that require it
        target_strings: Optional list of strings to target specific content sections
        
    Returns:
        Dictionary with structured content elements
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title = ""
    if soup.title:
        title = soup.title.text.strip()
    
    # Try to get more specific title from h1 if title looks generic
    if not title or len(title) < 10:
        h1_tags = soup.find_all('h1')
        if h1_tags and len(h1_tags[0].text.strip()) > 10:
            title = h1_tags[0].text.strip()
    
    # Extract main content using trafilatura (our primary extractor)
    main_text = extract_clean_text(html_content, method='trafilatura', url=url)
    
    # If target strings are provided, prioritize content around those strings
    targeted_text = ""
    if target_strings:
        targeted_text = extract_targeted_content(html_content, target_strings)
        if targeted_text:
            main_text = targeted_text
    
    # Extract key points (using headers)
    key_points = []
    for header in soup.find_all(['h1', 'h2', 'h3']):
        text = header.text.strip()
        if text and len(text) > 5 and text not in key_points:
            key_points.append(text)
    
    # For news aggregators like Google News, look for news article titles specifically
    if url and ('news.google.com' in url or 'news.yahoo.com' in url or 'msn.com/news' in url):
        print_info("Detected news aggregator site, searching for article titles", "Content Extraction")
        
        # Look for common news article title patterns
        article_titles = []
        
        # Google News specific article elements
        articles = soup.find_all('article')
        for article in articles[:20]:  # Limit to first 20 articles
            # Try to find the headline
            headline = article.find(['h3', 'h4'])
            if headline:
                title = headline.text.strip()
                if title and len(title) > 15 and title not in article_titles:  # Skip short titles
                    article_titles.append(title)
                    
        # Add these to our key points
        if article_titles:
            key_points = article_titles + key_points
            
    # Limit key points to most important ones
    key_points = key_points[:15]
    
    # Extract potential highlights (often in <strong>, <b>, <em> tags)
    highlights = []
    for tag in soup.find_all(['strong', 'b', 'em']):
        text = tag.text.strip()
        if text and len(text) > 15 and text not in highlights:
            highlights.append(text)
    
    # Limit highlights to most important ones
    highlights = highlights[:5]
    
    # Create a summary of the extracted content
    summary = ""
    if len(main_text) > 200:
        # Extract first paragraph or two for summary
        paragraphs = main_text.split('\n\n')
        summary = '\n\n'.join(paragraphs[:2])
        if len(summary) > 500:
            summary = summary[:500] + "..."
    
    return {
        "title": title,
        "main_text": main_text,
        "key_points": key_points,
        "highlights": highlights,
        "summary": summary,
        "word_count": len(main_text.split()),
        "targeted_extraction": bool(target_strings and targeted_text)
    }