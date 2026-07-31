"""
Outbreaks routes — GET /outbreaks
Fetches WHO Disease Outbreak News RSS and returns parsed alerts.
"""
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.utils.logger import get_logger

logger = get_logger(__name__)
outbreaks_router = APIRouter(prefix="/outbreaks", tags=["Outbreaks"])

_cache: dict = {"data": None, "ts": 0}
CACHE_TTL = 1800  # 30 minutes

WHO_FEEDS = [
    "https://www.who.int/rss-feeds/news-releases.xml",
    "https://www.who.int/feeds/entity/csr/don/en/rss.xml",
]


def _fetch_who_feed() -> List[dict]:
    """Fetch and parse WHO RSS feeds."""
    try:
        import feedparser
        import requests
    except ImportError:
        raise RuntimeError("feedparser or requests not installed")

    alerts = []
    for feed_url in WHO_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10, headers={"User-Agent": "AfriHealth/1.0"})
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:15]:
                alerts.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:400],
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": "WHO",
                })
        except Exception as e:
            logger.warning("Failed to fetch feed %s: %s", feed_url, e)
    return alerts


@outbreaks_router.get("", summary="Get latest WHO disease outbreak alerts")
def get_outbreaks(region: Optional[str] = Query(None, description="Filter by region keyword")):
    """Returns disease outbreak news from WHO RSS feeds with 30-minute caching."""
    global _cache
    now = time.time()
    if _cache["data"] is None or (now - _cache["ts"]) > CACHE_TTL:
        try:
            _cache["data"] = _fetch_who_feed()
            _cache["ts"] = now
        except RuntimeError as exc:
            logger.error("Outbreak feed error: %s", exc)
            # Return empty list gracefully if network/deps unavailable
            _cache["data"] = []
            _cache["ts"] = now

    alerts = _cache["data"] or []
    if region:
        region_lower = region.lower()
        alerts = [a for a in alerts if region_lower in a["title"].lower() or region_lower in a["summary"].lower()]

    return {
        "alerts": alerts,
        "count": len(alerts),
        "cached": True,
        "source": "WHO RSS",
    }
