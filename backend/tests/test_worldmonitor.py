import pytest
from unittest.mock import AsyncMock, patch
from app.services.worldmonitor_service import WorldMonitorService, COUNTRY_NAMES
from app.tools.registry import WorldMonitorTelemetryTool, WorldNewsFeedTool

@pytest.fixture
def mock_risk_scores_response():
    return {
        "ciiScores": [
            {
                "region": "MM",
                "staticBaseline": 45,
                "dynamicScore": 0,
                "combinedScore": 79.5,
                "trend": "TREND_DIRECTION_STABLE",
                "components": {"newsActivity": 0, "ciiContribution": 0, "geoConvergence": 0, "militaryActivity": 65},
                "computedAt": 1781240199451,
                "eventMultiplier": 1.8,
                "methodologyVersion": "v8",
                "advisoryLevel": "do-not-travel",
                "advisoryProvenance": "fallback"
            },
            {
                "region": "UA",
                "staticBaseline": 50,
                "dynamicScore": 3,
                "combinedScore": 74.0,
                "trend": "TREND_DIRECTION_RISING",
                "components": {"newsActivity": 0, "ciiContribution": 0, "geoConvergence": 0, "militaryActivity": 35},
                "computedAt": 1781240199451,
                "eventMultiplier": 0.8,
                "methodologyVersion": "v8",
                "advisoryLevel": "do-not-travel",
                "advisoryProvenance": "fallback"
            }
        ],
        "strategicRisks": [
            {
                "region": "global",
                "level": "SEVERITY_LEVEL_MEDIUM",
                "score": 66.0,
                "factors": ["MM", "UA"],
                "trend": "TREND_DIRECTION_STABLE"
            }
        ],
        "degraded": False,
        "stale": False
    }

@pytest.mark.asyncio
async def test_get_raw_risk_scores_success(mock_risk_scores_response):
    service = WorldMonitorService()
    
    # Mock httpx AsyncClient
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: mock_risk_scores_response
        mock_get.return_value = mock_response
        
        result = await service.get_raw_risk_scores()
        
        assert result == mock_risk_scores_response
        mock_get.assert_called_once_with(service.api_url, headers={})

@pytest.mark.asyncio
async def test_get_raw_risk_scores_failure():
    service = WorldMonitorService()
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = await service.get_raw_risk_scores()
        assert result == {}

@pytest.mark.asyncio
async def test_get_telemetry_success(mock_risk_scores_response):
    service = WorldMonitorService()
    
    with patch.object(service, "get_raw_risk_scores", return_value=mock_risk_scores_response):
        telemetry = await service.get_telemetry()
        
        assert telemetry["global_risk_index"] == 66.0
        assert telemetry["active_conflicts"] == 2
        assert telemetry["is_live"] is True
        assert telemetry["is_stale"] is False
        assert telemetry["data_as_of"] is not None
        assert telemetry["fetched_at"] is not None
        
        recent_events = telemetry["recent_events"]
        assert len(recent_events) == 2
        
        # Verify Ukraine detail mapping
        ua_event = next(e for e in recent_events if e["region"] == "Ukraine")
        assert ua_event["severity"] == "High"  # score 74.0 is >= 65 and < 75
        assert "Stability index evaluated at 74.0" in ua_event["description"]
        assert ua_event["risk_score"] == 74.0
        assert ua_event["source"] == "World Monitor"
        assert ua_event["is_live"] is True
        assert ua_event["data_as_of"] is not None
        assert "do-not-travel" in ua_event["description"]
        assert "militaryActivity" not in ua_event["description"] # lowercase components shouldn't be printed directly

@pytest.mark.asyncio
async def test_get_telemetry_handles_missing_region_code(mock_risk_scores_response):
    response = {
        **mock_risk_scores_response,
        "ciiScores": [{
            "region": None,
            "combinedScore": 47.5,
            "computedAt": 1781240199451,
            "trend": "TREND_DIRECTION_STABLE"
        }]
    }
    service = WorldMonitorService()
    with patch.object(service, "get_raw_risk_scores", return_value=response):
        telemetry = await service.get_telemetry()

    event = telemetry["recent_events"][0]
    assert event["region"] == "Unknown region"
    assert event["region_code"] is None
    assert event["id"] == "evt-unknown-0"

@pytest.mark.asyncio
async def test_get_telemetry_marks_stale_live_source(mock_risk_scores_response):
    stale_response = {**mock_risk_scores_response, "stale": True}
    service = WorldMonitorService()
    with patch.object(service, "get_raw_risk_scores", return_value=stale_response):
        telemetry = await service.get_telemetry()
    assert telemetry["is_live"] is True
    assert telemetry["is_stale"] is True
    assert "stale data" in telemetry["status_message"]

@pytest.mark.asyncio
async def test_get_telemetry_fallback():
    service = WorldMonitorService()
    
    with patch.object(service, "get_raw_risk_scores", return_value={}):
        telemetry = await service.get_telemetry()
        
        assert telemetry["global_risk_index"] == 72.4
        assert telemetry["active_conflicts"] == 14
        assert telemetry["is_live"] is False
        assert telemetry["is_stale"] is True
        assert telemetry["data_source"] == "static_fallback_sample"
        assert "not live" in telemetry["last_updated"]
        assert telemetry["data_as_of"] is None
        assert len(telemetry["recent_events"]) == 3

@pytest.mark.asyncio
async def test_get_world_summary_context(mock_risk_scores_response):
    service = WorldMonitorService()
    
    with patch.object(service, "get_raw_risk_scores", return_value=mock_risk_scores_response):
        context = await service.get_world_summary_context()
        
        assert "Global Risk Index: 66.0/100" in context
        assert "Ukraine" in context
        assert "Myanmar" in context

@pytest.mark.asyncio
async def test_get_world_news_fallback():
    # If API key is not set, we should immediately return the fallback news feed
    with patch("app.services.worldmonitor_service.settings.WORLD_MONITOR_API_KEY", ""):
        service = WorldMonitorService()
        news = await service.get_world_news()
        
        assert len(news) == 5
        assert news[0]["source"] == "BBC World"
        assert "Oil prices slide" in news[0]["title"]
        assert news[0]["isAlert"] is True
        assert news[0]["is_live"] is False
        assert news[0]["data_source"] == "static_fallback_sample"
        assert news[0]["publishedAt"] is None
        assert news[2]["source"] == "BBC World"
        assert news[2]["isAlert"] is False
        assert "STATIC SAMPLE — NOT LIVE" in await service.get_world_news_context()

@pytest.mark.asyncio
async def test_get_world_news_success():
    # Mock successful response from https://api.worldmonitor.app/api/news/v1/list-feed-digest?variant=full
    mock_news_response = {
        "categories": {
            "world": {
                "items": [
                    {
                        "source": "Al Jazeera",
                        "title": "Tensions ease in regional borders",
                        "link": "https://aljazeera.com/tensions-ease",
                        "publishedAt": 1781534400000,
                        "isAlert": True,
                        "snippet": "Diplomatic efforts lead to reduction of regional military activity."
                    }
                ]
            }
        }
    }
    
    with patch("app.services.worldmonitor_service.settings.WORLD_MONITOR_API_KEY", "wm_1234567890abcdef1234567890abcdef12345678"):
        service = WorldMonitorService()
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: mock_news_response
            mock_get.return_value = mock_response
            
            news = await service.get_world_news()
            assert len(news) == 1
            assert news[0]["source"] == "Al Jazeera"
            assert news[0]["title"] == "Tensions ease in regional borders"
            assert news[0]["isAlert"] is True
            assert news[0]["published_at"] is not None

@pytest.mark.asyncio
async def test_get_world_news_context():
    service = WorldMonitorService()
    
    # We patch get_world_news to return fixed items for testing formatting and relative time
    import datetime
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    two_hours_ago = int((now_utc - datetime.timedelta(hours=2)).timestamp() * 1000)
    five_hours_ago = int((now_utc - datetime.timedelta(hours=5)).timestamp() * 1000)
    
    mock_items = [
        {
            "source": "BBC News",
            "title": "Gold spikes higher",
            "link": "https://bbc.com/gold",
            "publishedAt": two_hours_ago,
            "isAlert": True,
            "snippet": "Markets react to economic news."
        },
        {
            "source": "AP News",
            "title": "Ceasefire talks resume",
            "link": "https://ap.org/ceasefire",
            "publishedAt": five_hours_ago,
            "isAlert": False,
            "snippet": "Envoys meet in Geneva."
        }
    ]
    
    with patch.object(service, "get_world_news", return_value=mock_items):
        context = await service.get_world_news_context()
        
        # Verify relative time calculation: two_hours_ago -> "2 hours ago", five_hours_ago -> "5 hours ago"
        assert "2 hours ago" in context
        assert "5 hours ago" in context
        assert "BBC News" in context
        assert "https://bbc.com/gold" in context
        assert "Published at (UTC):" in context
        assert "Data Source: unknown" in context
        assert "Gold spikes higher" in context
        assert "[ALERT]" in context
        assert "AP News" in context
        assert "Ceasefire talks resume" in context

@pytest.mark.asyncio
async def test_world_monitor_tool_formats_the_fetched_snapshot_once():
    telemetry = {"global_risk_index": 61.0}
    with patch(
        "app.tools.registry.world_monitor_service.get_telemetry",
        AsyncMock(return_value=telemetry)
    ) as get_telemetry, patch(
        "app.tools.registry.world_monitor_service.get_world_summary_context",
        AsyncMock(return_value="Risk: 61")
    ) as get_context:
        result = await WorldMonitorTelemetryTool().run()
    get_telemetry.assert_awaited_once()
    get_context.assert_awaited_once_with(telemetry)
    assert result["success"] is True

@pytest.mark.asyncio
async def test_world_news_tool_formats_the_fetched_snapshot_once():
    news = [{"title": "Sample", "is_live": False}]
    with patch(
        "app.tools.registry.world_monitor_service.get_world_news",
        AsyncMock(return_value=news)
    ) as get_news, patch(
        "app.tools.registry.world_monitor_service.get_world_news_context",
        AsyncMock(return_value="Static sample")
    ) as get_context:
        result = await WorldNewsFeedTool().run()
    get_news.assert_awaited_once()
    get_context.assert_awaited_once_with(news)
    assert result["success"] is True
