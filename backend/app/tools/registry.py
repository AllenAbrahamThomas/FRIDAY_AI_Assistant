import logging
from typing import Dict, Any, List, Optional
from app.tools.base_tool import BaseTool
from app.services.worldmonitor_service import world_monitor_service
from app.services.search_service import search_service
from app.services.weather_service import weather_service

logger = logging.getLogger(__name__)

class WorldMonitorTelemetryTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="world_monitor_telemetry",
            description="Retrieves global geopolitical risk index, active conflict hotzones, and strategic stability metrics from World Monitor.",
            timeout=10.0
        )

    async def _run(self, **kwargs) -> Dict[str, Any]:
        telemetry = await world_monitor_service.get_telemetry()
        summary_context = await world_monitor_service.get_world_summary_context()
        return {
            "telemetry": telemetry,
            "summary_context": summary_context
        }

class WorldNewsFeedTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="world_news_feed",
            description="Retrieves live global intelligence news digest and breaking alerts from the World Monitor news network.",
            timeout=10.0
        )

    async def _run(self, **kwargs) -> Dict[str, Any]:
        news = await world_monitor_service.get_world_news()
        news_context = await world_monitor_service.get_world_news_context()
        return {
            "articles": news,
            "news_context": news_context
        }

class WebSearchTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="web_search",
            description="Searches real-time web news and fact databases (via Google News RSS and DuckDuckGo fallback).",
            timeout=12.0
        )

    async def _run(self, query: str = "", max_results: int = 4, **kwargs) -> str:
        if not query:
            return "No search query provided."
        return await search_service.search(query=query, max_results=max_results)

class WeatherTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="weather_and_location",
            description="Retrieves the user's current city location and meteorological weather observations.",
            timeout=8.0
        )

    async def _run(self, **kwargs) -> Dict[str, Any]:
        return await weather_service.get_local_weather()

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register(WorldMonitorTelemetryTool())
        self.register(WorldNewsFeedTool())
        self.register(WebSearchTool())
        self.register(WeatherTool())

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self._tools.values()
        ]

    async def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self.get(name)
        if not tool:
            return {
                "tool_name": name,
                "success": False,
                "data": None,
                "error": f"Tool '{name}' not found in registry",
                "duration_seconds": 0.0
            }
        return await tool.run(**kwargs)

tool_registry = ToolRegistry()
