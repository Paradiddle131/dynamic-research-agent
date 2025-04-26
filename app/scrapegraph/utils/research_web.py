import re
from typing import List
from langchain_community.tools import DuckDuckGoSearchResults
from .logging import get_logger
logger = get_logger(__name__)
def search_on_web(
    query: str,
    search_engine: str = "duckduckgo",
    max_results: int = 10,
) -> List[str]:
    if not query or not isinstance(query, str):
        logger.error("Search query must be a non-empty string.")
        return []
    search_engine = search_engine.lower()
    if search_engine != "duckduckgo":
        logger.warning(f"Search engine '{search_engine}' is not supported. Using DuckDuckGo.")
    try:
        logger.info(f"Performing DuckDuckGo search for: '{query}' (max_results={max_results})")
        research = DuckDuckGoSearchResults(num_results=max_results)
        res = research.run(query)
        urls = re.findall(r"https?://[^\s,\]]+", res)
        cleaned_urls = [url.strip('.,') for url in urls]
        filtered_urls = filter_non_html_links(cleaned_urls)
        if not filtered_urls:
             logger.warning(f"No valid URLs extracted from DuckDuckGo results for query: '{query}'")
        return filtered_urls[:max_results]
    except Exception as e:
        logger.error(f"DuckDuckGo search failed for query '{query}': {str(e)}")
        return []
def filter_non_html_links(links: List[str]) -> List[str]:
    non_html_extensions = {'.pdf', '.xml', '.json', '.csv', '.zip', '.rar', '.exe', '.dmg', '.mp3', '.mp4', '.avi', '.mov', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'}
    filtered = []
    for link in links:
        if not any(link.lower().endswith(ext) for ext in non_html_extensions):
            filtered.append(link)
    return filtered
