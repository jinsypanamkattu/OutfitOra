"""Weather adapter. Open-Meteo is EU-hosted and aggregates national models
(including MET Nordic / SMHI-relevant data for Sweden). Swap the provider here
without touching the engine."""
import datetime as dt
import time
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import httpx

TZ = ZoneInfo("Europe/Stockholm")
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_TTL = 30 * 60
_cache: dict[tuple[float, float], tuple[float, list["Hour"]]] = {}


@dataclass
class Hour:
    time: dt.datetime   # start of the hour, tz-aware (Europe/Stockholm)
    temp: float         # °C
    feels: float        # apparent temperature, °C
    precip: float       # mm in that hour
    pop: float          # precipitation probability, %
    wind: float         # m/s
    uv: float
    cloud: float


def _grid(v: float) -> float:
    return round(v * 20) / 20  # ~5 km grid, improves cache hits


async def fetch_forecast(lat: float, lon: float) -> list[Hour]:
    key = (_grid(lat), _grid(lon))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]

    params = {
        "latitude": key[0],
        "longitude": key[1],
        "hourly": "temperature_2m,apparent_temperature,precipitation,"
                  "precipitation_probability,wind_speed_10m,uv_index,cloud_cover",
        "wind_speed_unit": "ms",
        "timezone": "Europe/Stockholm",
        "forecast_days": 3,
    }
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "weather-outfit-judge/0.1"}) as client:
        r = await client.get(FORECAST_URL, params=params)
        r.raise_for_status()
        h = r.json()["hourly"]

    def val(name: str, i: int) -> float:
        v = h[name][i]
        return 0.0 if v is None else float(v)

    hours = [
        Hour(
            time=dt.datetime.fromisoformat(t).replace(tzinfo=TZ),
            temp=val("temperature_2m", i),
            feels=val("apparent_temperature", i),
            precip=val("precipitation", i),
            pop=val("precipitation_probability", i),
            wind=val("wind_speed_10m", i),
            uv=val("uv_index", i),
            cloud=val("cloud_cover", i),
        )
        for i, t in enumerate(h["time"])
    ]
    _cache[key] = (time.time(), hours)
    return hours


async def geocode(q: str) -> list[dict]:
    params = {"name": q, "count": 5, "language": "en", "format": "json", "countryCode": "SE"}
    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "weather-outfit-judge/0.1"}) as client:
        r = await client.get(GEOCODE_URL, params=params)
        r.raise_for_status()
    return [
        {"name": x["name"], "region": x.get("admin1", ""), "lat": x["latitude"], "lon": x["longitude"]}
        for x in r.json().get("results", [])
    ]
