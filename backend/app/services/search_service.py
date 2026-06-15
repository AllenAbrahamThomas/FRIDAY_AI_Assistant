import httpx
import xml.etree.ElementTree as ET
import urllib.parse
import logging

logger = logging.getLogger(__name__)

class SearchService:
    async def search(self, query: str, max_results: int = 4) -> str:
        """
        Retrieves real-time context by querying Google News RSS Search first (highly robust, 
        no rate limits), and falling back to DuckDuckGo search if needed.
        """
        results = []
        
        # 1. Primary: Google News RSS Search (Free, fast, never ratelimited, returns 2026 news)
        try:
            encoded_query = urllib.parse.quote_plus(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            async with httpx.AsyncClient(timeout=8.0) as client:
                # Crucial: follow redirects because Google News redirects to Ceid regions
                resp = await client.get(rss_url, headers=headers, follow_redirects=True)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    items = root.findall('.//item')
                    
                    for item in items[:max_results]:
                        title = item.find('title')
                        pub_date = item.find('pubDate')
                        source = item.find('source')
                        
                        title_text = title.text if title is not None else "No Title"
                        date_text = pub_date.text[:16] if pub_date is not None else "Recent"
                        source_text = source.text if source is not None else "News Source"
                        
                        results.append(
                            f"Publish Date: {date_text}\n"
                            f"Source: {source_text}\n"
                            f"News Headline: {title_text}\n"
                        )
        except Exception as e:
            logger.warning(f"Google News RSS context query failed: {e}")

        # 2. Secondary Fallback: DuckDuckGo Search (in case RSS parsing fails)
        if not results:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    try:
                        # Attempt DDG News
                        news_results = list(ddgs.news(query, max_results=max_results))
                        for r in news_results:
                            date_str = r.get('date', '')[:10]
                            results.append(
                                f"Source: {r.get('source')} ({date_str})\n"
                                f"Title: {r.get('title')}\n"
                                f"Snippet: {r.get('body')}\n"
                            )
                    except Exception:
                        # Fallback to general web text search
                        web_results = list(ddgs.text(query, max_results=max_results))
                        for r in web_results:
                            results.append(
                                f"Title: {r.get('title')}\n"
                                f"Snippet: {r.get('body')}\n"
                            )
            except Exception as e:
                logger.error(f"DuckDuckGo fallback search failed: {e}")

        if results:
            return "\n---\n".join(results)
        
        return "No real-time search context could be retrieved for this query."

search_service = SearchService()
