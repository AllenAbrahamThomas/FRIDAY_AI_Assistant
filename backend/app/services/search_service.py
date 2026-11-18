import html
import httpx
import xml.etree.ElementTree as ET
import urllib.parse
import logging
import re
from app.config import settings

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
            
            async with httpx.AsyncClient(timeout=settings.SEARCH_TIMEOUT_SECONDS) as client:
                # Crucial: follow redirects because Google News redirects to Ceid regions
                resp = await client.get(rss_url, headers=headers, follow_redirects=True)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    items = root.findall('.//item')
                    
                    for item in items[:max_results]:
                        title = item.find('title')
                        pub_date = item.find('pubDate')
                        source = item.find('source')
                        link = item.find('link')
                        description = item.find('description')
                        
                        title_text = title.text if title is not None else "No Title"
                        date_text = pub_date.text[:16] if pub_date is not None and pub_date.text else "Publication time unavailable"
                        source_text = source.text if source is not None else "News Source"
                        article_url = link.text.strip() if link is not None and link.text else ""
                        snippet = ""
                        if description is not None and description.text:
                            snippet = re.sub(
                                r"\s+",
                                " ",
                                re.sub(r"<[^>]+>", " ", html.unescape(description.text))
                            ).strip()
                        
                        results.append(
                            f"Publish Date: {date_text}\n"
                            f"Source: {source_text}\n"
                            f"News Headline: {title_text}\n"
                            f"URL: {article_url}\n"
                            f"Snippet: {snippet}\n"
                        )
        except Exception as e:
            logger.warning("Google News RSS search failed (%s)", type(e).__name__)

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
                                f"Publish Date: {date_str or 'Publication time unavailable'}\n"
                                f"Source: {r.get('source') or 'Unknown Source'}\n"
                                f"Title: {r.get('title')}\n"
                                f"URL: {r.get('url') or r.get('href') or ''}\n"
                                f"Snippet: {r.get('body')}\n"
                            )
                    except Exception:
                        # Fallback to general web text search
                        web_results = list(ddgs.text(query, max_results=max_results))
                        for r in web_results:
                            results.append(
                                f"Title: {r.get('title')}\n"
                                f"URL: {r.get('href') or r.get('url') or ''}\n"
                                f"Snippet: {r.get('body')}\n"
                            )
            except Exception as e:
                logger.error("DuckDuckGo fallback search failed (%s)", type(e).__name__)

        if results:
            return "\n---\n".join(results)
        
        return "No real-time search context could be retrieved for this query."

search_service = SearchService()
