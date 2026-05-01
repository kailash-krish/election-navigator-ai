"""
services/maps_service.py — Google Maps Places API (Nearby Search + Geocoding).
Finds voter registration offices and government centres near you.
NOTE: This does NOT show your personal polling booth assignment.
For your exact polling booth, use voters.eci.gov.in with your EPIC number.
"""

import logging
import json
import math
import urllib.parse
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
GEOCODE_URL       = "https://maps.googleapis.com/maps/api/geocode/json"

# Election-relevant search keywords ordered by relevance
_SEARCH_KEYWORDS = [
    "election office",
    "electoral registration office",
    "BLO booth level officer",
    "municipal corporation office",
    "government office",
]

_SEARCH_RADIUS = 8000   # metres


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    """Calculate great-circle distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2)**2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _directions_url(lat: float, lng: float, name: str) -> str:
    dest = urllib.parse.quote_plus(f"{name}, {lat},{lng}")
    return f"https://www.google.com/maps/dir/?api=1&destination={dest}"


class MapsService:
    """
    Google Maps Places + Geocoding integration.
    Finds nearby election/government offices relevant to voters.
    """

    def __init__(self, api_key: Optional[str]):
        self._key   = api_key
        self._ready = bool(api_key)
        if not api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not configured.")

    def is_ready(self) -> bool:
        return self._ready

    def find_voter_offices(
        self,
        pincode: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> dict:
        """
        Return nearby voter registration offices and government centres.
        Resolves pincode → lat/lng if needed.
        NOTE: For your exact polling booth on election day, visit voters.eci.gov.in.
        """
        if not self._ready:
            return self._no_key_response()

        if pincode and not (lat and lng):
            coords = self._geocode_pincode(pincode)
            if not coords:
                return {"error": "Could not resolve pincode to location", "results": []}
            lat, lng = coords

        if not (lat and lng):
            return {"error": "Location not found", "results": []}

        places = self._search_nearby(float(lat), float(lng))
        return {
            "lat":          lat,
            "lng":          lng,
            "results":      places,
            "maps_embed_key": self._key,
            "search_radius_km": _SEARCH_RADIUS / 1000,
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _geocode_pincode(self, pincode: str) -> Optional[tuple]:
        """Convert 6-digit pincode to lat/lng via Geocoding API."""
        params = urllib.parse.urlencode({
            "address": f"{pincode}, India",
            "region":  "in",
            "key":     self._key,
        })
        url = f"{GEOCODE_URL}?{params}"
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read())
            if data.get("status") == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                return float(loc["lat"]), float(loc["lng"])
            logger.warning("Geocode returned status: %s", data.get("status"))
        except Exception as e:
            logger.error("Geocode error: %s", e)
        return None

    def _search_nearby(self, lat: float, lng: float) -> list:
        """Search for election-relevant places across multiple keywords."""
        results: list = []
        seen: set = set()

        for kw in _SEARCH_KEYWORDS[:3]:  # cap at 3 keyword searches
            params = urllib.parse.urlencode({
                "location": f"{lat},{lng}",
                "radius":   _SEARCH_RADIUS,
                "keyword":  kw,
                "key":      self._key,
            })
            url = f"{PLACES_NEARBY_URL}?{params}"
            try:
                with urllib.request.urlopen(url, timeout=8) as resp:
                    data = json.loads(resp.read())

                if data.get("status") not in ("OK", "ZERO_RESULTS"):
                    logger.warning("Places API status: %s", data.get("status"))

                for p in data.get("results", [])[:5]:
                    pid = p.get("place_id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)

                    p_lat = p["geometry"]["location"]["lat"]
                    p_lng = p["geometry"]["location"]["lng"]
                    dist_km = _haversine_km(lat, lng, p_lat, p_lng)

                    results.append({
                        "name":           p.get("name", "Unknown"),
                        "address":        p.get("vicinity", ""),
                        "rating":         p.get("rating"),
                        "total_ratings":  p.get("user_ratings_total"),
                        "open_now":       p.get("opening_hours", {}).get("open_now"),
                        "lat":            p_lat,
                        "lng":            p_lng,
                        "place_id":       pid,
                        "distance_km":    round(dist_km, 2),
                        "directions_url": _directions_url(p_lat, p_lng, p.get("name", "")),
                        "maps_url":       f"https://www.google.com/maps/place/?q=place_id:{pid}",
                        "types":          p.get("types", [])[:3],
                    })
            except Exception as e:
                logger.error("Places search error ('%s'): %s", kw, e)

        # Sort by distance, deduplicate, cap at 8
        results.sort(key=lambda x: x.get("distance_km", 999))
        return results[:8]

    def _no_key_response(self) -> dict:
        return {
            "error":   "Maps API not configured",
            "results": [],
            "tip":     "Add GOOGLE_MAPS_API_KEY to .env to enable voter registration office finder.",
        }
