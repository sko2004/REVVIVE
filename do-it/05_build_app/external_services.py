"""
External route, weather, and energy estimation helpers for Revvive.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
OPENROUTESERVICE_API_KEY = os.environ.get("OPENROUTESERVICE_API_KEY", "").strip()
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "").strip()
OPENCHARGEMAP_API_KEY = os.environ.get("OPENCHARGEMAP_API_KEY", "").strip()


def haversine_distance(origin: dict[str, float], destination: dict[str, float]) -> float:
    lat1, lon1 = origin["lat"], origin["lng"]
    lat2, lon2 = destination["lat"], destination["lng"]
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def normalize_location(location: Any) -> dict[str, float] | None:
    if not location:
        return None
    if isinstance(location, dict) and "lat" in location and "lng" in location:
        return {"lat": float(location["lat"]), "lng": float(location["lng"])}
    if isinstance(location, str) and "," in location:
        parts = [part.strip() for part in location.split(",")]
        if len(parts) >= 2:
            try:
                return {"lat": float(parts[0]), "lng": float(parts[1])}
            except ValueError:
                return None
    return None


def _route_from_google(origin: str, destination: str) -> dict[str, Any] | None:
    if not GOOGLE_MAPS_API_KEY:
        return None
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": GOOGLE_MAPS_API_KEY,
        "region": "in",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "alternatives": "false",
    }
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") != "OK":
        return None
    route = data["routes"][0]
    leg = route["legs"][0]

    steps = []
    for step in leg.get("steps", []):
        start = {
            "lat": step["start_location"]["lat"],
            "lng": step["start_location"]["lng"],
        }
        end = {
            "lat": step["end_location"]["lat"],
            "lng": step["end_location"]["lng"],
        }
        distance_km = step["distance"]["value"] / 1000.0
        duration_min = step["duration"]["value"] / 60.0
        speed_kmh = distance_km / max(0.01, duration_min / 60.0)
        steps.append(
            {
                "distance_km": distance_km,
                "duration_min": duration_min,
                "speed_kmh": round(speed_kmh, 1),
                "start": start,
                "end": end,
                "travel_mode": step.get("travel_mode", "DRIVING"),
                "html_instructions": step.get("html_instructions", ""),
            }
        )

    return {
        "distance_km": leg["distance"]["value"] / 1000.0,
        "duration_min": leg["duration"]["value"] / 60.0,
        "summary": route.get("summary", ""),
        "polyline": route.get("overview_polyline", {}).get("points", ""),
        "start_address": leg.get("start_address", ""),
        "end_address": leg.get("end_address", ""),
        "origin": {
            "lat": leg["start_location"]["lat"],
            "lng": leg["start_location"]["lng"],
        },
        "destination": {
            "lat": leg["end_location"]["lat"],
            "lng": leg["end_location"]["lng"],
        },
        "segments": steps,
    }


def _route_from_openrouteservice(origin: dict[str, float], destination: dict[str, float]) -> dict[str, Any] | None:
    if not OPENROUTESERVICE_API_KEY:
        return None
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    coords = [[origin["lng"], origin["lat"]], [destination["lng"], destination["lat"]]]
    headers = {"Authorization": OPENROUTESERVICE_API_KEY, "Content-Type": "application/json"}
    body = {"coordinates": coords, "units": "km"}
    resp = requests.post(url, json=body, headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if not data.get("features"):
        return None
    segment = data["features"][0]["properties"]
    geometry = data["features"][0].get("geometry", {})
    return {
        "distance_km": segment.get("summary", {}).get("distance", 0.0),
        "duration_min": segment.get("summary", {}).get("duration", 0.0) / 60.0,
        "summary": "ORS route fallback",
        "polyline": geometry,
        "origin": origin,
        "destination": destination,
        "segments": [
            {
                "distance_km": segment.get("summary", {}).get("distance", 0.0),
                "duration_min": segment.get("summary", {}).get("duration", 0.0) / 60.0,
                "speed_kmh": segment.get("summary", {}).get("distance", 0.0) / max(0.01, segment.get("summary", {}).get("duration", 0.0) / 60.0),
                "start": origin,
                "end": destination,
                "travel_mode": "DRIVING",
            }
        ],
    }


def _decode_polyline(polyline_str: str) -> list[dict[str, float]]:
    if not polyline_str:
        return []
    coords: list[dict[str, float]] = []
    index = 0
    lat = 0
    lng = 0

    while index < len(polyline_str):
        shift = 0
        result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat

        shift = 0
        result = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng
        coords.append({"lat": lat / 1e5, "lng": lng / 1e5})

    return coords


def _sample_route_points(route: dict[str, Any], sample_count: int = 3) -> list[dict[str, float]]:
    if not route:
        return []
    if route.get("polyline") and isinstance(route["polyline"], str):
        coords = _decode_polyline(route["polyline"])
        if coords:
            if len(coords) <= sample_count:
                return coords
            points = [coords[0]]
            for i in range(1, sample_count - 1):
                idx = int((len(coords) - 1) * i / (sample_count - 1))
                points.append(coords[idx])
            points.append(coords[-1])
            return points
    return [route.get("origin", {}), route.get("destination", {})]


def _elevation_profile_from_google(points: list[dict[str, float]]) -> list[dict[str, Any]]:
    if not GOOGLE_MAPS_API_KEY or not points:
        return []
    if len(points) > 100:
        points = points[:100]
    url = "https://maps.googleapis.com/maps/api/elevation/json"
    locations = "|".join(f"{p['lat']},{p['lng']}" for p in points)
    params = {"locations": locations, "key": GOOGLE_MAPS_API_KEY}
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if data.get("status") != "OK":
        return []
    return [
        {"lat": r["location"]["lat"], "lng": r["location"]["lng"], "elevation_m": r["elevation"]}
        for r in data.get("results", [])
    ]


def get_route(origin: str | dict[str, float], destination: str | dict[str, float]) -> dict[str, Any]:
    origin_coord = normalize_location(origin) if isinstance(origin, str) else origin
    destination_coord = normalize_location(destination) if isinstance(destination, str) else destination
    origin_str = origin if isinstance(origin, str) else f"{origin_coord['lat']},{origin_coord['lng']}"
    destination_str = destination if isinstance(destination, str) else f"{destination_coord['lat']},{destination_coord['lng']}"

    route = _route_from_google(origin_str, destination_str)
    if route:
        route_points = _sample_route_points(route, sample_count=5)
        route["elevation_profile"] = _elevation_profile_from_google(route_points)
        return route

    if origin_coord and destination_coord:
        route = _route_from_openrouteservice(origin_coord, destination_coord)
        if route:
            route["elevation_profile"] = []
            return route

    if origin_coord and destination_coord:
        distance_km = haversine_distance(origin_coord, destination_coord)
        duration_min = max(1.0, distance_km / 35.0 * 60.0)
        return {
            "distance_km": distance_km,
            "duration_min": duration_min,
            "summary": "Direct distance fallback",
            "polyline": "",
            "origin": origin_coord,
            "destination": destination_coord,
            "segments": [
                {
                    "distance_km": distance_km,
                    "duration_min": duration_min,
                    "speed_kmh": distance_km / max(0.01, duration_min / 60.0),
                    "start": origin_coord,
                    "end": destination_coord,
                    "travel_mode": "DRIVING",
                }
            ],
            "elevation_profile": [],
        }

    raise ValueError("Unable to compute route: please provide valid lat,lng pairs or supported addresses.")


def _weather_for_point(point: dict[str, float]) -> dict[str, Any]:
    if not WEATHER_API_KEY or not point:
        return {"temperature_c": 25.0, "wind_m_s": 3.0, "precipitation_mm": 0.0, "description": "clear"}
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": point["lat"], "lon": point["lng"], "appid": WEATHER_API_KEY, "units": "metric"}
    resp = requests.get(url, params=params, timeout=10)
    if resp.status_code != 200:
        return {"temperature_c": 25.0, "wind_m_s": 3.0, "precipitation_mm": 0.0, "description": "clear"}
    data = resp.json()
    weather = data.get("weather", [{}])[0]
    return {
        "temperature_c": data.get("main", {}).get("temp", 25.0),
        "wind_m_s": data.get("wind", {}).get("speed", 3.0),
        "precipitation_mm": float(data.get("rain", {}).get("1h", 0.0) or data.get("snow", {}).get("1h", 0.0) or 0.0),
        "description": weather.get("main", "clear"),
    }


def get_weather_along_route(route: dict[str, Any]) -> dict[str, Any]:
    points = _sample_route_points(route, sample_count=3)
    snapshots = []
    for p in points:
        weather = _weather_for_point(p)
        snapshots.append({"location": p, **weather})

    if not snapshots:
        return {"temperature_c": 25.0, "wind_m_s": 3.0, "precipitation_mm": 0.0, "description": "clear", "samples": []}

    avg_temp = sum(w["temperature_c"] for w in snapshots) / len(snapshots)
    avg_wind = sum(w["wind_m_s"] for w in snapshots) / len(snapshots)
    return {
        "temperature_c": round(avg_temp, 1),
        "wind_m_s": round(avg_wind, 1),
        "precipitation_mm": round(sum(w["precipitation_mm"] for w in snapshots) / len(snapshots), 2),
        "description": ", ".join(sorted({w["description"] for w in snapshots if w["description"]})) or "clear",
        "samples": snapshots,
    }


def _charger_from_poi(poi: dict[str, Any]) -> dict[str, Any]:
    address = poi.get("AddressInfo", {})
    connectors: list[dict[str, Any]] = []
    max_power_kw = 0.0
    for connection in poi.get("Connections", []) or []:
        power_kw = float(connection.get("PowerKW") or 0.0)
        if power_kw > max_power_kw:
            max_power_kw = power_kw
        connectors.append(
            {
                "connection_type": connection.get("ConnectionType", {}).get("Title", ""),
                "level": connection.get("Level", {}).get("Title", ""),
                "power_kw": power_kw,
                "quantity": connection.get("Quantity"),
                "current_type": connection.get("CurrentType", {}).get("Title", ""),
            }
        )
    return {
        "id": str(poi.get("ID") or ""),
        "name": address.get("Title", "Unknown Charger"),
        "address": address.get("AddressLine1", ""),
        "location": {
            "lat": address.get("Latitude"),
            "lng": address.get("Longitude"),
        },
        "distance_km": float(address.get("Distance", 0.0) or 0.0),
        "connectors": connectors,
        "power_kw": max(7.0, max_power_kw or 7.0),
        "usage_type": poi.get("UsageType", {}).get("Title", ""),
        "status": poi.get("StatusType", {}).get("Title", ""),
    }


def _openchargemap_search(center: dict[str, float], radius_km: float = 20.0, max_results: int = 20) -> list[dict[str, Any]]:
    if not OPENCHARGEMAP_API_KEY or not center:
        return []
    url = "https://api.openchargemap.io/v3/poi/"
    params = {
        "output": "json",
        "latitude": center["lat"],
        "longitude": center["lng"],
        "distance": radius_km,
        "distanceunit": "KM",
        "maxresults": max_results,
        "compact": "true",
        "verbose": "false",
        "key": OPENCHARGEMAP_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        return []
    pois = resp.json()
    return [_charger_from_poi(poi) for poi in pois if poi]


def get_chargers_along_route(
    route: dict[str, Any],
    connector_type: str,
    radius_km: float = 20.0,
    max_results: int = 12,
) -> list[dict[str, Any]]:
    if not route:
        return []
    points = _sample_route_points(route, sample_count=5)
    seen: set[str] = set()
    chargers: list[dict[str, Any]] = []
    for point in points:
        if not point:
            continue
        pois = _openchargemap_search(point, radius_km=radius_km, max_results=max_results)
        for poi in pois:
            fid = poi.get("id")
            if not fid or fid in seen:
                continue
            if connector_type:
                normalized = connector_type.lower()
                matches = any(
                    normalized in (c.get("connection_type", "") or "").lower()
                    or normalized in (c.get("level", "") or "").lower()
                    for c in poi["connectors"]
                )
                if not matches:
                    continue
            seen.add(fid)
            chargers.append(poi)
            if len(chargers) >= max_results:
                break
        if len(chargers) >= max_results:
            break
    chargers.sort(key=lambda p: float(p.get("distance_km", 9999.0)))
    return chargers[:max_results]


def charge_minutes_needed(needed_kwh: float, power_kw: float, efficiency: float = 0.9) -> int:
    if needed_kwh <= 0.0:
        return 0
    effective_kw = max(1.0, power_kw) * efficiency
    return int(round(max(5.0, (needed_kwh / effective_kw) * 60.0)))


def estimate_energy(
    distance_km: float,
    duration_min: float,
    temperature_c: float,
    wind_m_s: float,
    elevation_gain_m: float = 0.0,
    elevation_loss_m: float = 0.0,
    battery_capacity_kwh: float = 3.5,
    battery_health_factor: float = 1.0,
) -> dict[str, Any]:
    base_consumption = max(0.02, 0.14) * distance_km
    traffic_factor = max(1.0, min(1.5, 1.0 + max(0.0, 40.0 - (distance_km / max(0.01, duration_min / 60.0))) * 0.01))
    weather_factor = 1.0 + min(0.35, max(0.0, (wind_m_s - 3.0) * 0.02 + max(0.0, 25.0 - temperature_c) * 0.003))
    elevation_factor = 1.0 + max(0.0, elevation_gain_m / max(1.0, distance_km * 100.0)) * 0.15
    regen_savings = min(0.15, max(0.0, elevation_loss_m / max(1.0, distance_km * 100.0)))
    consumption_kwh = base_consumption * traffic_factor * weather_factor * elevation_factor
    consumption_kwh = max(0.0, consumption_kwh * (1.0 - regen_savings))
    available_kwh = battery_capacity_kwh * min(1.0, battery_health_factor)
    return {
        "distance_km": round(distance_km, 2),
        "duration_min": round(duration_min, 1),
        "consumption_kwh": round(consumption_kwh, 2),
        "available_kwh": round(available_kwh, 2),
        "base_consumption": round(base_consumption, 2),
        "traffic_factor": round(traffic_factor, 2),
        "weather_factor": round(weather_factor, 2),
        "elevation_factor": round(elevation_factor, 2),
        "regen_savings": round(regen_savings * consumption_kwh, 2),
        "elevation_gain_m": elevation_gain_m,
        "elevation_loss_m": elevation_loss_m,
    }


def describe_energy_breakdown(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "base": round(max(0.0, 0.14 * data["distance_km"]), 2),
        "traffic": round(data["consumption_kwh"] * 0.12, 2),
        "weather": round(data["consumption_kwh"] * 0.08, 2),
        "elevation": round(max(0.0, data["consumption_kwh"] - 0.14 * data["distance_km"]), 2),
    }


def charger_reachability(remaining_percent: float, battery_capacity_kwh: float, distance_km: float) -> bool:
    available_kwh = battery_capacity_kwh * (remaining_percent / 100.0)
    estimate = estimate_energy(distance_km, distance_km / 35.0 * 60.0, 25.0, 3.0, 0.0, 0.0, battery_capacity_kwh)
    return estimate["consumption_kwh"] <= available_kwh
