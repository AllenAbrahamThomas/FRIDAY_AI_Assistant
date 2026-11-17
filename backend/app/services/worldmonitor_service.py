import httpx
import logging
import datetime
from typing import Dict, Any, List, Optional
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
        self.timeout = settings.WORLD_MONITOR_TIMEOUT_SECONDS

    async def get_raw_risk_scores(self) -> Dict[str, Any]:
        """
        Fetches raw risk scores from the public World Monitor API with retry logic.
        """
        headers = {}
        if settings.WORLD_MONITOR_API_KEY:
            headers["X-WorldMonitor-Key"] = settings.WORLD_MONITOR_API_KEY

        retryable_statuses = {408, 429, 500, 502, 503, 504}
        for attempt in range(max(1, settings.WORLD_MONITOR_RETRY_COUNT + 1)):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(self.api_url, headers=headers)
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 401:
                        logger.warning("World Monitor API requires authorization or a valid key (HTTP 401). Using static sample data.")
                        return {}
                    else:
                        logger.error(f"World Monitor API returned status code {response.status_code}")
                        if response.status_code not in retryable_statuses:
                            return {}
            except httpx.TimeoutException:
                logger.warning(f"World Monitor API timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Error connecting to World Monitor API (attempt {attempt + 1}): {e}")
        return {}

    async def get_telemetry(self) -> Dict[str, Any]:
        """
        Fetches global intelligence risk scores and maps them to the TelemetryData model structure,
        clearly tracking whether data is live or cached offline fallback.
        """
        raw_data = await self.get_raw_risk_scores()
        fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Fallback values in case external API is offline or unauthenticated
        default_events = [
            {
                "id": "evt-ua",
                "region": "Ukraine",
                "region_code": "UA",
                "severity": "Critical",
                "description": "Conflict operations and regional infrastructure tensions reported.",
                "risk_score": None,
                "trend": "Unavailable",
                "source": "Static Sample",
                "source_url": None,
                "data_as_of": None,
                "is_live": False,
                "data_source": "static_fallback_sample"
            },
            {
                "id": "evt-me",
                "region": "Middle East",
                "region_code": None,
                "severity": "High",
                "description": "Red Sea shipping lane security patrols and logistics impacts.",
                "risk_score": None,
                "trend": "Unavailable",
                "source": "Static Sample",
                "source_url": None,
                "data_as_of": None,
                "is_live": False,
                "data_source": "static_fallback_sample"
            },
            {
                "id": "evt-mm",
                "region": "Myanmar",
                "region_code": "MM",
                "severity": "High",
                "description": "Border stability updates and resource export patrols reported.",
                "risk_score": None,
                "trend": "Unavailable",
                "source": "Static Sample",
                "source_url": None,
                "data_as_of": None,
                "is_live": False,
                "data_source": "static_fallback_sample"
            }
        ]

        if not raw_data or "ciiScores" not in raw_data:
            logger.info("Using static sample telemetry data because no live data was available.")
            return {
                "global_risk_index": 72.4,
                "active_conflicts": 14,
                "economic_stability_score": 54.8,
                "last_updated": "Static fallback sample (not live)",
                "fetched_at": fetched_at,
                "data_as_of": None,
                "recent_events": default_events,
                "is_live": False,
                "is_stale": True,
                "data_source": "static_fallback_sample",
                "status_message": "Static sample data; not a current live reading."
            }

        cii_scores = raw_data.get("ciiScores", [])
        strategic_risks = raw_data.get("strategicRisks", [])
        computed_at_values = [
            score.get("computedAt")
            for score in cii_scores
            if isinstance(score.get("computedAt"), (int, float))
        ]
        data_as_of = None
        if computed_at_values:
            data_as_of = datetime.datetime.fromtimestamp(
                max(computed_at_values) / 1000,
                tz=datetime.timezone.utc
            ).isoformat()
        is_stale = bool(raw_data.get("stale", False))

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
            region_code = str(score.get("region") or "").strip().upper()
            region_name = COUNTRY_NAMES.get(region_code, region_code or "Unknown region")
            combined_score = float(score.get("combinedScore", 0))
            trend = score.get("trend", "TREND_DIRECTION_STABLE").replace("TREND_DIRECTION_", "").capitalize()
            advisory = score.get("advisoryLevel", "normal")
            event_data_as_of = self._to_iso_timestamp(score.get("computedAt"))
            
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
                "id": f"evt-{region_code.lower()}" if region_code else f"evt-unknown-{i}",
                "region": region_name,
                "region_code": region_code or None,
                "severity": severity,
                "description": " ".join(desc_parts),
                "risk_score": round(combined_score, 1),
                "trend": trend,
                "source": "World Monitor",
                "source_url": "https://worldmonitor.app",
                "data_as_of": event_data_as_of,
                "is_live": True,
                "data_source": "live_worldmonitor_api"
            })

        # Sort events by severity / score descending
        sev_rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        def sort_key(e):
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
            "last_updated": data_as_of or fetched_at,
            "fetched_at": fetched_at,
            "data_as_of": data_as_of,
            "recent_events": recent_events[:20],
            "is_live": True,
            "is_stale": is_stale,
            "data_source": "live_worldmonitor_api",
            "status_message": (
                "Connected to live World Monitor feed; source reports stale data."
                if is_stale
                else "Connected to live World Monitor feed."
            )
        }

    @staticmethod
    def _to_iso_timestamp(value: Any) -> Optional[str]:
        if isinstance(value, (int, float)):
            try:
                return datetime.datetime.fromtimestamp(
                    value / 1000,
                    tz=datetime.timezone.utc
                ).isoformat()
            except (OverflowError, OSError, ValueError):
                return None
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _data_status(item: Dict[str, Any]) -> str:
        if item.get("is_live") is True:
            return "LIVE"
        if item.get("is_live") is False or item.get("data_source") == "static_fallback_sample":
            return "STATIC SAMPLE — NOT LIVE"
        return "STATUS UNAVAILABLE"

    async def get_world_summary_context(
        self,
        telemetry: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Retrieves a text summary context of the global risks to feed into LLM RAG prompt.
        """
        if telemetry is None:
            telemetry = await self.get_telemetry()
        
        status_label = "LIVE" if telemetry.get("is_live") else "STATIC SAMPLE — NOT LIVE"
        context_lines = [
            f"World Monitor Data Status: {status_label}",
            f"Data freshness: {'STALE' if telemetry.get('is_stale') else 'CURRENT'}",
            f"Data as of: {telemetry.get('data_as_of') or 'not supplied by source'}",
            f"Global Risk Index: {telemetry['global_risk_index']}/100",
            f"Active Critical/High Instability Regions: {telemetry['active_conflicts']}",
            f"Global Economic Stability Score: {telemetry['economic_stability_score']}/100",
            "\nTop Monitored Conflict/Instability Regions:"
        ]
        
        for event in telemetry.get("recent_events", []):
            context_lines.append(
                f"- {event['region']} (Severity: {event['severity']}): {event['description']}"
            )
            
        return "\n".join(context_lines)

    async def get_world_news(self) -> List[Dict[str, Any]]:
        """
        Fetches live world news digest or explicitly marked static sample data.
        """
        fallback_news = [
            {
                "source": "BBC World",
                "title": "Oil prices slide after US–Iran deal announced",
                "link": "https://www.bbc.com/news/business-world",
                "publishedAt": None,
                "isAlert": True,
                "snippet": "Under the agreement, the key Strait of Hormuz waterway will be reopened, US President Donald Trump said."
            },
            {
                "source": "AP News",
                "title": "What to know about a possible deal to end the Iran war - AP News",
                "link": "https://apnews.com/article/iran-war-deal",
                "publishedAt": None,
                "isAlert": True,
                "snippet": "What to know about a possible deal to end the Iran war AP News"
            },
            {
                "source": "BBC World",
                "title": "Russian strikes kill nine in Ukraine and damage historic cathedral, officials say",
                "link": "https://www.bbc.com/news/world-europe",
                "publishedAt": None,
                "isAlert": False,
                "snippet": "A Ukrainian drone attack in the Russian city of Tula, south of Moscow, killed three people and wounded three others."
            },
            {
                "source": "CNN World",
                "title": "The true test of Trump's Iran agreement will come only if the fighting stops - CNN",
                "link": "https://www.cnn.com/world/iran-agreement-test",
                "publishedAt": None,
                "isAlert": False,
                "snippet": "The true test of Trump's Iran agreement will come only if the fighting stops CNN"
            },
            {
                "source": "Guardian World",
                "title": "Attacks on education, pupils and staff around the world up by 40%, says study",
                "link": "https://www.theguardian.com/world/attacks-on-education-gcpea",
                "publishedAt": None,
                "isAlert": False,
                "snippet": "Cases reported in 83 countries, with at least 10,600 students and staff killed, injured, abducted or arrested, GCPEA says Attacks on education globally have surged by 40%"
            }
        ]

        if not settings.WORLD_MONITOR_API_KEY:
            return self._mark_news_as_fallback(fallback_news)

        headers = {"X-WorldMonitor-Key": settings.WORLD_MONITOR_API_KEY}
        url = "https://api.worldmonitor.app/api/news/v1/list-feed-digest?variant=full"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    raw_data = response.json()
                    categories = raw_data.get("categories", {})
                    
                    items = []
                    for cat in ["world", "politics", "crisis", "general"]:
                        if cat in categories:
                            items.extend(categories[cat].get("items", []))
                    
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
                                "published_at": self._to_iso_timestamp(item.get("publishedAt")),
                                "isAlert": bool(item.get("isAlert", False)),
                                "snippet": item.get("snippet", ""),
                                "is_live": True,
                                "data_source": "live_worldmonitor_api"
                            })
                        return cleaned_items
                else:
                    logger.error(f"World Monitor news API returned status code {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching news from World Monitor API: {str(e)}")

        return self._mark_news_as_fallback(fallback_news)

    @staticmethod
    def _mark_news_as_fallback(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                **item,
                "published_at": WorldMonitorService._to_iso_timestamp(item.get("publishedAt")),
                "is_live": False,
                "data_source": "static_fallback_sample",
                "status_message": "Static sample news; publication time is not verified."
            }
            for item in items
        ]

    async def get_world_news_context(
        self,
        news_items: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Formats retrieved World Monitor news items into a single context string,
        calculating relative publication times (e.g. "2 hours ago").
        """
        if news_items is None:
            news_items = await self.get_world_news()
        if not news_items:
            return "No real-time world news context available."

        context_parts = []
        for item in news_items[:10]:
            source = item.get("source", "Unknown Source")
            title = item.get("title", "No Title")
            snippet = item.get("snippet", "")
            pub_at = item.get("publishedAt")
            published_at = item.get("published_at") or self._to_iso_timestamp(pub_at)
            
            time_str = "Publication time unavailable"
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
                f"Data Status: {self._data_status(item)}\n"
                f"Data Source: {item.get('data_source', 'unknown')}\n"
                f"Publish Date: {time_str}{alert_tag}\n"
                f"Published at (UTC): {published_at or 'not supplied by source'}\n"
                f"Source: {source}\n"
                f"URL: {item.get('link') or 'not supplied by source'}\n"
                f"News Headline: {title}\n"
                f"Snippet: {snippet}"
            )
            
        return "\n---\n".join(context_parts)

world_monitor_service = WorldMonitorService()
