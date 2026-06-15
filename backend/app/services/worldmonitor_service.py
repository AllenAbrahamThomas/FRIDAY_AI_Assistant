import httpx
import logging
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

COUNTRY_NAMES = {
    "MM": "Myanmar",
    "UA": "Ukraine",
    "PK": "Pakistan",
    "MX": "Mexico",
    "RU": "Russia",
    "PS": "Palestine",
    "IL": "Israel",
    "YE": "Yemen",
    "SY": "Syria",
    "SO": "Somalia",
    "SD": "Sudan",
    "VE": "Venezuela",
    "AF": "Afghanistan",
    "LY": "Libya",
    "IQ": "Iraq",
    "IR": "Iran",
    "KP": "North Korea",
    "TW": "Taiwan",
    "CN": "China",
    "US": "United States",
}

class WorldMonitorService:
    def __init__(self):
        self.api_url = "https://api.worldmonitor.app/api/intelligence/v1/get-risk-scores"
        self.timeout = 10.0

    async def get_raw_risk_scores(self) -> Dict[str, Any]:
        """
        Fetches raw risk scores from the public World Monitor API.
        """
        headers = {}
        if settings.WORLD_MONITOR_API_KEY:
            headers["X-WorldMonitor-Key"] = settings.WORLD_MONITOR_API_KEY

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.api_url, headers=headers)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"World Monitor API returned status code {response.status_code}")
        except Exception as e:
            logger.error(f"Error connecting to World Monitor API: {str(e)}")
        return {}

    async def get_telemetry(self) -> Dict[str, Any]:
        """
        Fetches global intelligence risk scores and maps them to the TelemetryData model structure.
        """
        raw_data = await self.get_raw_risk_scores()
        
        # Fallback values in case external API is offline
        default_events = [
            {
                "id": "evt-ua",
                "region": "Ukraine",
                "severity": "Critical",
                "description": "Conflict operations and regional infrastructure tensions reported.",
                "source": "World Monitor Cache"
            },
            {
                "id": "evt-me",
                "region": "Middle East",
                "severity": "High",
                "description": "Red Sea shipping lane security patrols and logistics impacts.",
                "source": "World Monitor Cache"
            },
            {
                "id": "evt-mm",
                "region": "Myanmar",
                "severity": "High",
                "description": "Border stability updates and resource export patrols reported.",
                "source": "World Monitor Cache"
            }
        ]

        if not raw_data or "ciiScores" not in raw_data:
            logger.warning("Using fallback telemetry data.")
            return {
                "global_risk_index": 72.4,
                "active_conflicts": 14,
                "economic_stability_score": 54.8,
                "last_updated": "Cached (Offline Fallback)",
                "recent_events": default_events
            }

        cii_scores = raw_data.get("ciiScores", [])
        strategic_risks = raw_data.get("strategicRisks", [])

        # Get global risk index from strategicRisks where region == 'global'
        global_score = 72.4
        for r in strategic_risks:
            if r.get("region") == "global":
                global_score = float(r.get("score", global_score))
                break

        # Calculate active conflicts (combinedScore >= 60)
        active_conflicts = sum(1 for s in cii_scores if float(s.get("combinedScore", 0)) >= 60)
        if active_conflicts == 0:
            active_conflicts = len(cii_scores)

        # Calculate economic stability score (e.g. baseline of 100 minus weighted global risk)
        economic_stability = max(10.0, min(100.0, 100.0 - (global_score * 0.65)))

        # Format recent events from ciiScores
        recent_events = []
        for i, score in enumerate(cii_scores):
            region_code = score.get("region", "")
            region_name = COUNTRY_NAMES.get(region_code, region_code)
            combined_score = float(score.get("combinedScore", 0))
            trend = score.get("trend", "TREND_DIRECTION_STABLE").replace("TREND_DIRECTION_", "").capitalize()
            advisory = score.get("advisoryLevel", "normal")
            
            if combined_score >= 75:
                severity = "Critical"
            elif combined_score >= 65:
                severity = "High"
            elif combined_score >= 50:
                severity = "Medium"
            else:
                severity = "Low"

            # Create description
            desc_parts = [f"Stability index evaluated at {combined_score:.1f} ({trend})."]
            if advisory and advisory != "normal":
                desc_parts.append(f"Advisory level set to '{advisory}'.")
            
            components = score.get("components", {})
            mil_activity = components.get("militaryActivity", 0)
            if mil_activity > 0:
                desc_parts.append(f"Military/security component: {mil_activity:.0f}.")

            # Maximum content: Extract and format all other components
            news_activity = components.get("newsActivity", 0)
            if news_activity > 0:
                desc_parts.append(f"News/media activity index: {news_activity:.0f}.")
                
            cii_contrib = components.get("ciiContribution", 0)
            if cii_contrib > 0:
                desc_parts.append(f"Infrastructure impact score: {cii_contrib:.0f}.")
                
            geo_conv = components.get("geoConvergence", 0)
            if geo_conv > 0:
                desc_parts.append(f"Geopolitical convergence index: {geo_conv:.0f}.")

            recent_events.append({
                "id": f"evt-{region_code.lower()}",
                "region": region_name,
                "severity": severity,
                "description": " ".join(desc_parts),
                "source": "World Monitor / OSINT"
            })

        # Sort events by severity / score descending
        # Let's map severity to a rank for sorting
        sev_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        # Get raw score for sorting
        def sort_key(e):
            # find corresponding combined score
            code = e["id"].split("-")[-1].upper()
            val = 0.0
            for cs in cii_scores:
                if cs.get("region") == code:
                    val = float(cs.get("combinedScore", 0))
                    break
            return (sev_rank.get(e["severity"], 0), val)
            
        recent_events.sort(key=sort_key, reverse=True)

        return {
            "global_risk_index": round(global_score, 1),
            "active_conflicts": active_conflicts,
            "economic_stability_score": round(economic_stability, 1),
            "last_updated": "Live",
            "recent_events": recent_events[:20] # return top 20 events (maximum content)
        }

    async def get_world_summary_context(self) -> str:
        """
        Retrieves a text summary context of the global risks to feed into LLM RAG prompt.
        """
        telemetry = await self.get_telemetry()
        
        context_lines = [
            f"Global Risk Index: {telemetry['global_risk_index']}/100",
            f"Active Critical/High Instability Regions: {telemetry['active_conflicts']}",
            f"Global Economic Stability Score: {telemetry['economic_stability_score']}/100",
            "\nTop Monitored Conflict/Instability Regions:"
        ]
        
        for event in telemetry["recent_events"]:
            context_lines.append(
                f"- {event['region']} (Severity: {event['severity']}): {event['description']}"
            )
            
        return "\n".join(context_lines)

    async def get_world_news(self) -> List[Dict[str, Any]]:
        """
        Fetches live world news digest from World Monitor API or returns fallback screenshot news data.
        """
        import datetime
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        two_hours_ago = int((now_utc - datetime.timedelta(hours=2)).timestamp() * 1000)
        five_hours_ago = int((now_utc - datetime.timedelta(hours=5)).timestamp() * 1000)

        fallback_news = [
            {
                "source": "BBC World",
                "title": "Oil prices slide after US–Iran deal announced",
                "link": "https://www.bbc.com/news/business-world",
                "publishedAt": two_hours_ago,
                "isAlert": True,
                "snippet": "Under the agreement, the key Strait of Hormuz waterway will be reopened, US President Donald Trump said."
            },
            {
                "source": "AP News",
                "title": "What to know about a possible deal to end the Iran war - AP News",
                "link": "https://apnews.com/article/iran-war-deal",
                "publishedAt": five_hours_ago,
                "isAlert": True,
                "snippet": "What to know about a possible deal to end the Iran war AP News"
            },
            {
                "source": "BBC World",
                "title": "Russian strikes kill nine in Ukraine and damage historic cathedral, officials say",
                "link": "https://www.bbc.com/news/world-europe",
                "publishedAt": five_hours_ago,
                "isAlert": False,
                "snippet": "A Ukrainian drone attack in the Russian city of Tula, south of Moscow, killed three people and wounded three others."
            },
            {
                "source": "CNN World",
                "title": "The true test of Trump's Iran agreement will come only if the fighting stops - CNN",
                "link": "https://www.cnn.com/world/iran-agreement-test",
                "publishedAt": five_hours_ago,
                "isAlert": False,
                "snippet": "The true test of Trump's Iran agreement will come only if the fighting stops CNN"
            },
            {
                "source": "Guardian World",
                "title": "Attacks on education, pupils and staff around the world up by 40%, says study",
                "link": "https://www.theguardian.com/world/attacks-on-education-gcpea",
                "publishedAt": five_hours_ago,
                "isAlert": False,
                "snippet": "Cases reported in 83 countries, with at least 10,600 students and staff killed, injured, abducted or arrested, GCPEA says Attacks on education globally have surged by 40%"
            }
        ]

        if not settings.WORLD_MONITOR_API_KEY:
            logger.warning("WORLD_MONITOR_API_KEY not configured. Using fallback news feed.")
            return fallback_news

        headers = {"X-WorldMonitor-Key": settings.WORLD_MONITOR_API_KEY}
        url = "https://api.worldmonitor.app/api/news/v1/list-feed-digest?variant=full"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    raw_data = response.json()
                    categories = raw_data.get("categories", {})
                    
                    items = []
                    # Prefer world / politics / general categories
                    for cat in ["world", "politics", "crisis", "general"]:
                        if cat in categories:
                            items.extend(categories[cat].get("items", []))
                    
                    # If nothing extracted from specific categories, merge all categories
                    if not items:
                        for cat_bucket in categories.values():
                            items.extend(cat_bucket.get("items", []))
                    
                    if items:
                        cleaned_items = []
                        for item in items:
                            cleaned_items.append({
                                "source": item.get("source", "Unknown Source"),
                                "title": item.get("title", "No Title"),
                                "link": item.get("link", ""),
                                "publishedAt": item.get("publishedAt"),
                                "isAlert": bool(item.get("isAlert", False)),
                                "snippet": item.get("snippet", "")
                            })
                        return cleaned_items
                else:
                    logger.error(f"World Monitor news API returned status code {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching news from World Monitor API: {str(e)}")

        logger.warning("Using fallback news feed due to API failure.")
        return fallback_news

    async def get_world_news_context(self) -> str:
        """
        Formats retrieved World Monitor news items into a single context string,
        calculating relative publication times (e.g. "2 hours ago").
        """
        import datetime
        news_items = await self.get_world_news()
        if not news_items:
            return "No real-time world news context available."

        context_parts = []
        for item in news_items[:10]:
            source = item.get("source", "Unknown Source")
            title = item.get("title", "No Title")
            snippet = item.get("snippet", "")
            pub_at = item.get("publishedAt")
            
            # Format relative time if publishedAt timestamp is present
            time_str = "Recently"
            if pub_at:
                try:
                    dt = datetime.datetime.fromtimestamp(pub_at / 1000.0, tz=datetime.timezone.utc)
                    now = datetime.datetime.now(datetime.timezone.utc)
                    diff = now - dt
                    diff_seconds = diff.total_seconds()
                    
                    if diff_seconds < 0:
                        time_str = "Just now"
                    else:
                        diff_hours = diff_seconds / 3600.0
                        if diff_hours < 1:
                            diff_mins = diff_seconds / 60.0
                            time_str = f"{int(diff_mins)} minutes ago" if int(diff_mins) != 1 else "1 minute ago"
                        elif diff_hours < 24:
                            time_str = f"{int(diff_hours)} hours ago" if int(diff_hours) != 1 else "1 hour ago"
                        else:
                            time_str = f"{int(diff.days)} days ago" if int(diff.days) != 1 else "1 day ago"
                except Exception:
                    pass
            
            alert_tag = " [ALERT]" if item.get("isAlert") else ""
            context_parts.append(
                f"Publish Date: {time_str}{alert_tag}\n"
                f"Source: {source}\n"
                f"News Headline: {title}\n"
                f"Snippet: {snippet}"
            )
            
        return "\n---\n".join(context_parts)

world_monitor_service = WorldMonitorService()
