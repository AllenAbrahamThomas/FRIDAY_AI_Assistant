import httpx
import logging

logger = logging.getLogger(__name__)

class WeatherService:
    async def get_local_weather(self) -> dict:
        """
        Retrieves user's city name and current weather data using public IP-location 
        and Open-Meteo API (requires no keys).
        """
        lat, lon, city = None, None, None
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                # 1. Try ipapi.co (highly robust HTTPS geolocator)
                try:
                    resp = await client.get("https://ipapi.co/json/", headers=headers)
                    if resp.status_code == 200:
                        loc = resp.json()
                        lat = loc.get("latitude")
                        lon = loc.get("longitude")
                        city = loc.get("city")
                except Exception as e:
                    logger.warning(f"ipapi.co failed: {e}")

                # 2. Try ipinfo.io (HTTPS geolocator fallback)
                if lat is None or lon is None:
                    try:
                        resp = await client.get("https://ipinfo.io/json", headers=headers)
                        if resp.status_code == 200:
                            loc = resp.json()
                            city = loc.get("city")
                            loc_str = loc.get("loc", "")
                            if "," in loc_str:
                                lat_str, lon_str = loc_str.split(",")
                                lat = float(lat_str)
                                lon = float(lon_str)
                    except Exception as e:
                        logger.warning(f"ipinfo.io failed: {e}")

                # 3. Try freeipapi.com (high reliability, high limit fallback)
                if lat is None or lon is None:
                    try:
                        resp = await client.get("https://freeipapi.com/api/json", headers=headers)
                        if resp.status_code == 200:
                            loc = resp.json()
                            lat = loc.get("latitude")
                            lon = loc.get("longitude")
                            city = loc.get("cityName")
                    except Exception as e:
                        logger.warning(f"freeipapi.com failed: {e}")

                # 4. Try ip-api.com (HTTP geolocator fallback)
                if lat is None or lon is None:
                    try:
                        resp = await client.get("http://ip-api.com/json/", headers=headers)
                        if resp.status_code == 200:
                            loc = resp.json()
                            if loc.get("status") == "success":
                                lat = loc.get("lat")
                                lon = loc.get("lon")
                                city = loc.get("city")
                    except Exception as e:
                        logger.warning(f"ip-api.com failed: {e}")

                if not city:
                    city = "your area"

                if lat is not None and lon is not None:
                    # 2. Query Open-Meteo for weather info
                    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
                    weather_resp = await client.get(weather_url, headers=headers)
                    if weather_resp.status_code == 200:
                        wdata = weather_resp.json()
                        current_data = wdata.get("current", {})
                        temp = current_data.get("temperature_2m")
                        code = current_data.get("weather_code", 0)
                        
                        # Convert code to description
                        desc = "clear skies"
                        if code in [1, 2, 3]:
                            desc = "partly cloudy"
                        elif code in [45, 48]:
                            desc = "foggy"
                        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                            desc = "showers"
                        elif code in [71, 73, 75, 77, 85, 86]:
                            desc = "snowy"
                        elif code in [95, 96, 99]:
                            desc = "thunderstorms"
                            
                        return {
                            "city": city,
                            "temp": temp,
                            "desc": desc,
                            "success": True
                        }
        except Exception as e:
            logger.error(f"Error fetching local weather: {e}")
            
        return {
            "city": city or "your area",
            "temp": 24.0,
            "desc": "clear conditions",
            "success": False
        }

weather_service = WeatherService()
