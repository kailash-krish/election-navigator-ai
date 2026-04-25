"""
services/maps_service.py — Google Maps Places API integration.
Finds nearby government/election offices and polling booth areas.
"""

import logging
import urllib.parse
import urllib.request
import json

logger = logging.getLogger(__name__)

PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
GEOCODE_URL       = "https://maps.googleapis.com/maps/api/geocode/json"


class MapsService:
    def __init__(self, api_key: str | None):
        self._key   = api_key
        self._ready = bool(api_key)
        if not api_key:
            logger.warning("GOOGLE_MAPS_API_KEY not configured.")

    def is_ready(self) -> bool:
        return self._ready

    def find_polling_booths(
        self,
        pincode: str | None = None,
        lat: float | None = None,
        lng: float | None = None
    ) -> dict:
        """Return nearby government offices relevant to elections."""

        if not self._ready:
            return self._no_key_response()

        # Resolve lat/lng from pincode if needed
        if pincode and not (lat and lng):
            coords = self._geocode_pincode(pincode)
            if not coords:
                return {"error": "Could not resolve pincode to location", "results": []}
            lat, lng = coords

        if not (lat and lng):
            return {"error": "Location not found", "results": []}

        places = self._search_nearby(lat, lng)
        return {
            "lat": lat,
            "lng": lng,
            "results": places,
            "maps_embed_key": self._key,
        }

    def _geocode_pincode(self, pincode: str) -> tuple | None:
        params = urllib.parse.urlencode({
            "address": f"{pincode}, India",
            "key": self._key,
        })
        url = f"{GEOCODE_URL}?{params}"
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = json.loads(resp.read())
            if data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                return loc["lat"], loc["lng"]
        except Exception as e:
            logger.error("Geocode error: %s", e)
        return None

    def _search_nearby(self, lat: float, lng: float) -> list:
        keywords = ["election office", "BLO", "government office", "municipal office"]
        results  = []
        seen     = set()

        for kw in keywords[:2]:  # limit API calls
            params = urllib.parse.urlencode({
                "location": f"{lat},{lng}",
                "radius":   5000,
                "keyword":  kw,
                "key":      self._key,
            })
            url = f"{PLACES_NEARBY_URL}?{params}"
            try:
                with urllib.request.urlopen(url, timeout=8) as resp:
                    data = json.loads(resp.read())
                for p in data.get("results", [])[:4]:
                    pid = p.get("place_id")
                    if pid in seen:
                        continue
                    seen.add(pid)
                    results.append({
                        "name":     p.get("name"),
                        "address":  p.get("vicinity"),
                        "rating":   p.get("rating"),
                        "open_now": p.get("opening_hours", {}).get("open_now"),
                        "lat":      p["geometry"]["location"]["lat"],
                        "lng":      p["geometry"]["location"]["lng"],
                        "place_id": pid,
                    })
            except Exception as e:
                logger.error("Places search error: %s", e)

        return results[:8]

    def _no_key_response(self) -> dict:
        return {
            "error": "Maps API not configured",
            "results": [],
            "tip": "Add GOOGLE_MAPS_API_KEY to .env to enable polling booth finder."
        }
