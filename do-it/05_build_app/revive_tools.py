"""
EV-specific tool definitions and execution for Revvive.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from openai import OpenAI
from qdrant_client import QdrantClient

from external_services import (
    charge_minutes_needed,
    estimate_energy,
    get_chargers_along_route,
    get_route,
    get_weather_along_route,
)
import revive_postgres as db
import revive_qdrant as providers


@dataclass
class ToolContext:
    qdrant: QdrantClient
    run_id: UUID | None
    vehicle_context: dict[str, Any] | None = None


def _openai_client() -> OpenAI | None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if api_key is None:
        return None
    kw: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kw["base_url"] = base_url
    return OpenAI(**kw)


def _parse_args(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw or not str(raw).strip():
        return {}
    return json.loads(raw)


def _safe_json_parse(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _llm_json_response(prompt: str, user_message: str) -> dict[str, Any]:
    client = _openai_client()
    if client is None:
        return {}
    model = os.environ.get("CHAT_MODEL", "").strip() or "gpt-4o-mini"
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )
    content = completion.choices[0].message.content or ""
    return _safe_json_parse(content)


def _embed_text(text: str) -> list[float] | None:
    client = _openai_client()
    if client is None:
        return None
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small").strip() or "text-embedding-3-small"
    try:
        response = client.embeddings.create(model=model, input=text)
        embedding = response.data[0].embedding
        return [float(x) for x in embedding]
    except Exception:
        return None


def _normalize_triage_output(parsed: dict[str, Any]) -> dict[str, Any]:
    subsystem_options = [
        "Battery/BMS",
        "Motor/Drivetrain",
        "Controller/Power Electronics",
        "Charging Circuit",
        "Brakes",
        "Suspension",
        "Electrical",
        "Software/Dashboard",
    ]
    severity_options = ["Low", "Medium", "High", "Critical"]
    subsystem = str(parsed.get("subsystem", "Electrical") or "Electrical").strip()
    symptom_category = str(parsed.get("symptom_category", "Unknown Fault") or "Unknown Fault").strip()
    severity = str(parsed.get("severity", "Medium") or "Medium").strip().title()
    explanation = str(parsed.get("explanation", "The issue needs a trained service provider to inspect further.")).strip()
    if subsystem not in subsystem_options:
        for option in subsystem_options:
            if option.lower() in subsystem.lower():
                subsystem = option
                break
        else:
            subsystem = "Electrical"
    if severity not in severity_options:
        if "critical" in severity.lower():
            severity = "Critical"
        elif "high" in severity.lower():
            severity = "High"
        elif "low" in severity.lower():
            severity = "Low"
        else:
            severity = "Medium"
    return {
        "subsystem": subsystem,
        "symptom_category": symptom_category,
        "severity": severity,
        "explanation": explanation,
    }


def _normalize_safety_output(parsed: dict[str, Any]) -> dict[str, Any]:
    safe = parsed.get("is_safe")
    urgency = parsed.get("urgency_override")
    risk = str(parsed.get("risk_level", "none") or "none").strip().lower()
    if isinstance(safe, str):
        safe = safe.strip().lower() in ("true", "yes", "safe")
    is_safe = bool(safe) if isinstance(safe, bool) else risk == "none"
    if risk not in ("none", "elevated", "critical"):
        if "critical" in risk:
            risk = "critical"
        elif "elevated" in risk or "high" in risk:
            risk = "elevated"
        else:
            risk = "none"
    advisory = str(parsed.get("safety_advisory", "")).strip()
    hazard_description = str(parsed.get("hazard_description", "")).strip()
    if not advisory and not is_safe:
        advisory = "Do not ride the vehicle and do not charge it. Move away from the vehicle and seek professional help."
    if not urgency and not is_safe:
        urgency = "Critical"
    if is_safe:
        risk = "none"
        urgency = ""
    return {
        "is_safe": is_safe,
        "risk_level": risk,
        "hazard_description": hazard_description,
        "safety_advisory": advisory,
        "urgency_override": urgency,
    }


def _compose_range_verdict(summary: dict[str, Any]) -> str:
    client = _openai_client()
    if client is None:
        return ""
    model = os.environ.get("CHAT_MODEL", "").strip() or "gpt-4o-mini"
    prompt = (
        "You are an EV assistant summarizing whether a planned route is reachable on current battery charge. "
        "Provide a concise recommendation and mention if the result is comfortable, tight, or not advisable. "
        "Include the confidence band and key drivers such as route distance, traffic, weather, and battery state. "
        "Return only the summary text."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(summary, default=str)},
    ]
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )
    return completion.choices[0].message.content or ""


def _compose_charger_reasoning(summary: dict[str, Any]) -> str:
    client = _openai_client()
    if client is None:
        return summary.get("message", "No charger recommendations available.")
    model = os.environ.get("CHAT_MODEL", "").strip() or "gpt-4o-mini"
    prompt = (
        "You are an EV assistant that explains charger recommendations for a low-range route. "
        "Given candidate chargers and whether the vehicle can reach them, produce a concise natural-language recommendation. "
        "If the destination can be reached without charging, say so. "
        "Return only the final user-facing text."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(summary, default=str)},
    ]
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
    )
    return completion.choices[0].message.content or summary.get("message", "No charger recommendations available.")


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "estimate_range",
            "description": "Estimate whether the EV can reach the destination on current battery charge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Address or lat,lng origin."},
                    "destination": {"type": "string", "description": "Address or lat,lng destination."},
                    "current_battery_percent": {"type": "number"},
                    "battery_capacity_kwh": {"type": "number"},
                    "battery_health_factor": {"type": "number", "description": "Fraction between 0 and 1 for degraded battery."},
                    "vehicle_make": {"type": "string"},
                    "vehicle_model": {"type": "string"},
                },
                "required": ["origin", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_chargers_on_route",
            "description": "Find reachable compatible charging locations along a route when range is tight.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_location": {"type": "string", "description": "Current location as lat,lng or address."},
                    "destination": {"type": "string", "description": "Destination as lat,lng, address, or home/office."},
                    "current_battery_percent": {"type": "number"},
                    "battery_capacity_kwh": {"type": "number"},
                    "battery_health_factor": {"type": "number", "description": "Fraction between 0 and 1."},
                    "vehicle_make": {"type": "string"},
                    "vehicle_model": {"type": "string"},
                    "connector_type": {"type": "string"},
                },
                "required": ["current_location", "destination", "current_battery_percent", "connector_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "triage_issue",
            "description": "Classify an EV fault description into a structured diagnosis for downstream safety and provider search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner_description": {"type": "string"},
                    "vehicle_make": {"type": "string"},
                    "vehicle_model": {"type": "string"},
                },
                "required": ["owner_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "safety_check",
            "description": "Evaluate an issue for safety risk and return a hazard advisory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "triage_output": {"type": "object"},
                    "owner_description": {"type": "string"},
                },
                "required": ["triage_output", "owner_description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_providers",
            "description": "Search EV service providers by issue type, brand, location, and urgency. "
                           "Use urgency=urgent when the situation is unsafe so emergency-capable providers are returned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subsystem": {"type": "string"},
                    "symptom_category": {"type": "string"},
                    "vehicle_brand": {"type": "string"},
                    "owner_location": {"type": "string"},
                    "radius_km": {"type": "number"},
                    "urgency": {"type": "string", "enum": ["routine", "urgent"]},
                },
                "required": ["subsystem", "vehicle_brand"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_provider_details",
            "description": "Retrieve detailed information for a specific provider.",
            "parameters": {
                "type": "object",
                "properties": {
                    "provider_id": {"type": "string"},
                },
                "required": ["provider_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_fair_price",
            "description": "Estimate a fair cost range for the diagnosed issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subsystem": {"type": "string"},
                    "symptom_category": {"type": "string"},
                    "severity": {"type": "string"},
                    "vehicle_make": {"type": "string"},
                    "vehicle_model": {"type": "string"},
                    "vehicle_category": {"type": "string"},
                    "region": {"type": "string"},
                },
                "required": ["subsystem", "symptom_category", "severity", "vehicle_category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "queue_booking",
            "description": "Queue a provider booking for human approval in the approvals dashboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "provider_id": {"type": "string"},
                    "provider_name": {"type": "string"},
                    "issue_summary": {"type": "string"},
                    "triage_json": {"type": "object"},
                    "estimated_cost_min": {"type": "number"},
                    "estimated_cost_max": {"type": "number"},
                    "urgency": {"type": "string"},
                    "owner_notes": {"type": "string"},
                },
                "required": ["provider_id", "provider_name", "issue_summary", "triage_json", "estimated_cost_min", "estimated_cost_max", "urgency"],
            },
        },
    },
]


def _default_from_context(ctx: ToolContext, key: str, fallback: Any = None) -> Any:
    if ctx.vehicle_context and key in ctx.vehicle_context:
        return ctx.vehicle_context[key]
    return fallback


def execute_tool(ctx: ToolContext, name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
    args = _parse_args(arguments)
    q = ctx.qdrant

    if name == "estimate_range":
        origin = args.get("origin") or _default_from_context(ctx, "location") or ""
        destination = args.get("destination") or _default_from_context(ctx, "destination") or ""
        battery = float(args.get("current_battery_percent") or _default_from_context(ctx, "battery_percent") or 20)
        capacity = float(args.get("battery_capacity_kwh") or _default_from_context(ctx, "battery_capacity_kwh") or 3.5)
        health = float(args.get("battery_health_factor") or _default_from_context(ctx, "battery_health_factor") or 0.95)

        route = get_route(origin, destination)
        weather = get_weather_along_route(route)

        elevation_profile = route.get("elevation_profile") or []
        total_gain = 0.0
        total_loss = 0.0
        for i in range(1, len(elevation_profile)):
            delta = elevation_profile[i]["elevation_m"] - elevation_profile[i - 1]["elevation_m"]
            if delta > 0:
                total_gain += delta
            else:
                total_loss += abs(delta)

        segments = route.get("segments") or [
            {
                "distance_km": route["distance_km"],
                "duration_min": route["duration_min"],
                "speed_kmh": route["distance_km"] / max(0.01, route["duration_min"] / 60.0),
                "start": route["origin"],
                "end": route["destination"],
            }
        ]

        total_needed = 0.0
        breakdown = {"base": 0.0, "traffic": 0.0, "weather": 0.0, "elevation": 0.0}
        segment_details: list[dict[str, Any]] = []

        for segment in segments:
            seg_distance = float(segment.get("distance_km", 0.0))
            seg_duration = float(segment.get("duration_min", max(0.1, seg_distance / 35.0 * 60.0)))
            seg_speed = float(segment.get("speed_kmh", seg_distance / max(0.01, seg_duration / 60.0)))
            energy = estimate_energy(
                distance_km=seg_distance,
                duration_min=seg_duration,
                temperature_c=weather["temperature_c"],
                wind_m_s=weather["wind_m_s"],
                elevation_gain_m=total_gain * (seg_distance / max(0.01, route["distance_km"])),
                elevation_loss_m=total_loss * (seg_distance / max(0.01, route["distance_km"])),
                battery_capacity_kwh=capacity,
                battery_health_factor=health,
            )
            segment_details.append(
                {
                    "distance_km": seg_distance,
                    "duration_min": seg_duration,
                    "speed_kmh": round(seg_speed, 1),
                    "energy_kwh": energy["consumption_kwh"],
                    "breakdown": {
                        "base": energy["base_consumption"],
                        "traffic": round((energy["traffic_factor"] - 1.0) * energy["consumption_kwh"], 2),
                        "weather": round((energy["weather_factor"] - 1.0) * energy["consumption_kwh"], 2),
                        "elevation": round((energy["elevation_factor"] - 1.0) * energy["consumption_kwh"], 2),
                    },
                }
            )
            total_needed += energy["consumption_kwh"]
            breakdown["base"] += energy["base_consumption"]
            breakdown["traffic"] += round((energy["traffic_factor"] - 1.0) * energy["consumption_kwh"], 2)
            breakdown["weather"] += round((energy["weather_factor"] - 1.0) * energy["consumption_kwh"], 2)
            breakdown["elevation"] += round((energy["elevation_factor"] - 1.0) * energy["consumption_kwh"], 2)

        available_kwh = capacity * (battery / 100.0)
        margin_kwh = available_kwh - total_needed
        predicted_arrival = max(0.0, round((margin_kwh / capacity) * 100.0, 1))
        if margin_kwh >= total_needed * 0.2:
            verdict = "Comfortable"
        elif margin_kwh >= 0:
            verdict = "Tight"
        else:
            verdict = "Not Advisable"

        summary_payload = {
            "verdict": verdict,
            "distance_km": route["distance_km"],
            "duration_min": route["duration_min"],
            "current_battery_percent": battery,
            "battery_capacity_kwh": capacity,
            "battery_health_factor": health,
            "available_kwh": round(available_kwh, 2),
            "needed_kwh": round(total_needed, 2),
            "margin_kwh": round(margin_kwh, 2),
            "best_case_percent": round(min(100.0, predicted_arrival + 8.0), 1),
            "worst_case_percent": round(max(0.0, predicted_arrival - 8.0), 1),
            "route_summary": route.get("summary", ""),
            "weather": weather,
            "breakdown": breakdown,
        }
        verdict_text = _compose_range_verdict(summary_payload)
        return {
            "ok": True,
            "verdict": verdict,
            "verdict_text": verdict_text,
            "predicted_arrival_percent": predicted_arrival,
            "consumption_kwh": round(total_needed, 2),
            "available_kwh": round(available_kwh, 2),
            "confidence": {
                "best_case": summary_payload["best_case_percent"],
                "worst_case": summary_payload["worst_case_percent"],
            },
            "route": route,
            "weather": weather,
            "breakdown": {
                "base": round(breakdown["base"], 2),
                "traffic": round(breakdown["traffic"], 2),
                "weather": round(breakdown["weather"], 2),
                "elevation": round(breakdown["elevation"], 2),
            },
            "segment_details": segment_details,
        }

    if name == "find_chargers_on_route":
        current_location = args.get("current_location") or args.get("origin") or _default_from_context(ctx, "location") or ""
        destination = args.get("destination") or _default_from_context(ctx, "destination") or ""
        battery = float(args.get("current_battery_percent") or _default_from_context(ctx, "battery_percent") or 15)
        capacity = float(args.get("battery_capacity_kwh") or _default_from_context(ctx, "battery_capacity_kwh") or 3.5)
        health = float(args.get("battery_health_factor") or _default_from_context(ctx, "battery_health_factor") or 0.95)
        connector = args.get("connector_type") or _default_from_context(ctx, "connector_type") or "Type 2"

        route = get_route(current_location, destination)
        weather = get_weather_along_route(route)
        total_needed = 0.0
        available_kwh = capacity * (battery / 100.0)

        for segment in route.get("segments", [
            {
                "distance_km": route["distance_km"],
                "duration_min": route["duration_min"],
                "speed_kmh": route["distance_km"] / max(0.01, route["duration_min"] / 60.0),
            }
        ]):
            energy = estimate_energy(
                distance_km=float(segment.get("distance_km", 0.0)),
                duration_min=float(segment.get("duration_min", 0.0)),
                temperature_c=weather["temperature_c"],
                wind_m_s=weather["wind_m_s"],
                elevation_gain_m=0.0,
                battery_capacity_kwh=capacity,
                battery_health_factor=health,
            )
            total_needed += energy["consumption_kwh"]

        margin = available_kwh - total_needed
        comfortable = margin >= total_needed * 0.2

        if comfortable:
            summary = {
                "message": "Your EV can comfortably reach the destination on current charge. No charging stop is needed before reaching the destination.",
                "verdict": "Comfortable",
                "route_distance_km": route.get("distance_km"),
                "remaining_percent": battery,
                "battery_capacity_kwh": capacity,
                "estimated_consumption_kwh": round(total_needed, 2),
                "available_kwh": round(available_kwh, 2),
            }
            return {
                "ok": True,
                "chargers": [],
                "message": _compose_charger_reasoning(summary),
                "suppressed": True,
            }

        chargers = get_chargers_along_route(route, connector)
        charger_results = []
        for charger in chargers:
            distance_km = float(charger.get("distance_km", 0.0))
            to_charger_energy = estimate_energy(
                distance_km=distance_km,
                duration_min=max(1.0, distance_km / 35.0 * 60.0),
                temperature_c=weather["temperature_c"],
                wind_m_s=weather["wind_m_s"],
                elevation_gain_m=0.0,
                battery_capacity_kwh=capacity,
                battery_health_factor=health,
            )
            if available_kwh < to_charger_energy["consumption_kwh"]:
                continue

            remaining_after_arrival = max(0.0, available_kwh - to_charger_energy["consumption_kwh"])
            target_remaining = max(0.0, min(capacity * 0.8, capacity) - remaining_after_arrival)
            charge_minutes = charge_minutes_needed(target_remaining, float(charger.get("power_kw", 7.0)))
            guidance = (
                f"Charge {charge_minutes} minutes at {float(charger.get('power_kw', 7.0)):.1f} kW to reach about "
                f"{round(min(80.0, (remaining_after_arrival + target_remaining) / capacity * 100.0), 1)}% battery and continue toward your destination."
            )
            charger_results.append(
                {
                    "name": charger.get("name"),
                    "location": charger.get("location"),
                    "address": charger.get("address"),
                    "distance_km": distance_km,
                    "connector_types": [c.get("connection_type") for c in charger.get("connectors", []) if c.get("connection_type")],
                    "power_rating": f"{float(charger.get('power_kw', 7.0)):.1f} kW",
                    "charge_minutes_needed": charge_minutes,
                    "reachable": True,
                    "guidance": guidance,
                }
            )

        summary_payload = {
            "message": "Found reachable chargers along the route.",
            "route_distance_km": route.get("distance_km"),
            "current_battery_percent": battery,
            "connector_type": connector,
            "charger_count": len(charger_results),
            "chargers": charger_results,
        }
        return {
            "ok": True,
            "chargers": charger_results,
            "message": _compose_charger_reasoning(summary_payload),
            "suppressed": False,
        }

    if name == "triage_issue":
        owner_description = (args.get("owner_description") or "").strip()
        vehicle_make = args.get("vehicle_make") or _default_from_context(ctx, "vehicle_make") or ""
        vehicle_model = args.get("vehicle_model") or _default_from_context(ctx, "vehicle_model") or ""
        prompt = (
            "You are an EV diagnostics assistant. Classify the owner's description into one of the following subsystems: "
            "Battery/BMS, Motor/Drivetrain, Controller/Power Electronics, Charging Circuit, Brakes, Suspension, Electrical, Software/Dashboard. "
            "Also assign a standard symptom_category label, a severity of Low, Medium, High, or Critical, and a plain-language explanation for the owner. "
            "Do not include any extra text or commentary. Return only a valid JSON object with keys: subsystem, symptom_category, severity, explanation. "
            "If the description mentions charging, assume Charging Circuit; if it mentions loss of power, use Motor/Drivetrain; if it mentions warning messages or touchscreen failures, use Software/Dashboard. "
            "Use vehicle_make and vehicle_model only to add relevant context, not to invent additional faults."
        )
        user_message = json.dumps(
            {
                "owner_description": owner_description,
                "vehicle_make": vehicle_make,
                "vehicle_model": vehicle_model,
            },
            ensure_ascii=False,
        )
        parsed = _llm_json_response(prompt, user_message)
        parsed = _normalize_triage_output(parsed if isinstance(parsed, dict) else {})
        return {"ok": True, "triage": parsed}

    if name == "safety_check":
        triage_output = args.get("triage_output") or {}
        owner_description = (args.get("owner_description") or "").strip()
        prompt = (
            "You are an EV safety analyst. Evaluate the issue using the structured triage output and the owner's original description. "
            "Look for high-risk indicators such as smoke, burning smell, battery swelling or deformation, sparking, leaking fluid, thermal runaway symptoms, exposed high-voltage components, and severe electrical faults. "
            "Return only a JSON object with these keys: is_safe (boolean), risk_level (none/elevated/critical), hazard_description, safety_advisory, urgency_override. "
            "If the issue is unsafe, urgency_override must be Critical. "
            "Safety advisory must be explicit and actionable, for example: 'Do not ride the vehicle', 'Do not charge the vehicle', or 'Move away from the vehicle'."
        )
        user_message = json.dumps(
            {
                "triage_output": triage_output,
                "owner_description": owner_description,
            },
            ensure_ascii=False,
        )
        parsed = _llm_json_response(prompt, user_message)
        result = _normalize_safety_output(parsed if isinstance(parsed, dict) else {})
        return {"ok": True, **result}

    if name == "search_providers":
        subsystem = args.get("subsystem") or ""
        symptom_category = args.get("symptom_category")
        vehicle_brand = args.get("vehicle_brand") or _default_from_context(ctx, "vehicle_make") or ""
        owner_location = args.get("owner_location")
        radius_km = float(args.get("radius_km") or 40.0)
        urgency = args.get("urgency") or "routine"
        location = None
        if isinstance(owner_location, str) and "," in owner_location:
            parts = [part.strip() for part in owner_location.split(",")]
            try:
                location = {"lat": float(parts[0]), "lng": float(parts[1])}
            except ValueError:
                location = None

        query_text = subsystem.strip()
        if symptom_category:
            query_text = f"{query_text} {symptom_category.strip()}".strip()
        if not query_text:
            query_text = "EV service provider for electric vehicle fault"

        query_vector = _embed_text(query_text)
        providers_list = providers.search_providers(
            q,
            query_vector=query_vector,
            query_text=query_text,
            subsystem=subsystem,
            symptom_category=symptom_category,
            vehicle_brand=vehicle_brand,
            owner_location=location,
            radius_km=radius_km,
            urgency=urgency,
            limit=5,
        )
        return {"ok": True, "providers": providers_list, "count": len(providers_list)}

    if name == "get_provider_details":
        provider_id = (args.get("provider_id") or "").strip()
        if not provider_id:
            return {"ok": False, "error": "provider_id is required"}
        details = providers.get_provider_details(q, provider_id)
        if not details:
            return {"ok": False, "error": "Provider not found"}
        return {"ok": True, "provider": details}

    if name == "estimate_fair_price":
        subsystem = args.get("subsystem") or "Unknown"
        symptom = args.get("symptom_category") or "General"
        severity = args.get("severity") or "Medium"
        vehicle_category = args.get("vehicle_category") or "two_wheeler"
        region = args.get("region") or "India"
        history = db.query_pricing_history(subsystem, symptom, vehicle_category, region)
        if history:
            cost_min = float(history["cost_min"] or 1000.0)
            cost_max = float(history["cost_max"] or cost_min * 1.3)
            source = "historical data"
        else:
            base = 2000.0
            severity_factor = {"Low": 0.8, "Medium": 1.0, "High": 1.3, "Critical": 1.6}.get(severity, 1.0)
            cost_min = round(base * severity_factor, 2)
            cost_max = round(cost_min * 1.35, 2)
            source = "model estimate"
        return {
            "ok": True,
            "cost_min": cost_min,
            "cost_max": cost_max,
            "breakdown": {
                "parts_min": round(cost_min * 0.5, 2),
                "parts_max": round(cost_max * 0.5, 2),
                "labour_min": round(cost_min * 0.35, 2),
                "labour_max": round(cost_max * 0.35, 2),
            },
            "data_source": source,
            "disclaimer": "This range is an estimate based on historical repair patterns and issue severity.",
        }

    if name == "queue_booking":
        provider_id = (args.get("provider_id") or "").strip()
        provider_name = (args.get("provider_name") or "").strip()
        issue_summary = (args.get("issue_summary") or "").strip()
        triage_json = args.get("triage_json") or {}
        estimated_cost_min = float(args.get("estimated_cost_min") or 0.0)
        estimated_cost_max = float(args.get("estimated_cost_max") or 0.0)
        urgency = args.get("urgency") or "routine"
        owner_notes = args.get("owner_notes") or ""
        if not provider_id or not provider_name:
            return {"ok": False, "error": "provider_id and provider_name are required"}
        pid = db.enqueue_booking_approval(
            ctx.run_id,
            provider_id,
            provider_name,
            issue_summary,
            triage_json,
            estimated_cost_min,
            estimated_cost_max,
            urgency,
            owner_notes,
        )
        return {
            "ok": True,
            "pending_action_id": str(pid),
            "message": "Booking queued for your approval. Please approve or reject.",
            "provider_id": provider_id,
            "provider_name": provider_name,
            "issue_summary": issue_summary,
            "triage_json": triage_json,
            "estimated_cost_min": estimated_cost_min,
            "estimated_cost_max": estimated_cost_max,
            "urgency": urgency,
        }

    return {"ok": False, "error": f"unknown tool: {name}"}
