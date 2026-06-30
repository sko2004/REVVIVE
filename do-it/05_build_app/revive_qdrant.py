"""
EV provider store and search utilities for Revvive.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams, PointIdsList

from external_services import haversine_distance

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

VECTOR_SIZE = 1536
DUMMY_VECTOR: list[float] = [0.0] * VECTOR_SIZE


def _openai_client() -> OpenAI | None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if api_key is None:
        return None
    kw: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kw["base_url"] = base_url
    return OpenAI(**kw)


def _embed_text(text: str) -> list[float] | None:
    client = _openai_client()
    if client is None:
        return None
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small").strip() or "text-embedding-3-small"
    try:
        response = client.embeddings.create(model=model, input=text)
        return [float(x) for x in response.data[0].embedding]
    except Exception:
        return None


def _provider_profile_embedding(
    name: str,
    address: str,
    brand_certifications: list[str],
    subsystem_specialisations: list[str],
    equipment: list[str],
    description: str,
) -> list[float]:
    prompt = (
        f"{name}. "
        f"Address: {address}. "
        f"Brands: {', '.join(brand_certifications)}. "
        f"Specialisations: {', '.join(subsystem_specialisations)}. "
        f"Equipment: {', '.join(equipment)}. "
        f"Summary: {description}."
    )
    embedding = _embed_text(prompt)
    return embedding if embedding is not None else DUMMY_VECTOR


def _new_client() -> QdrantClient:
    path = os.environ.get("QDRANT_PATH", "").strip()
    if path:
        return QdrantClient(path=path)
    url = os.environ.get("QDRANT_URL", "").strip()
    api_key = os.environ.get("QDRANT_API_KEY", "").strip() or None
    if not url:
        raise ValueError(
            "Set QDRANT_URL and QDRANT_API_KEY in do-it/.env (hosted), or QDRANT_PATH (local folder) for Qdrant."
        )
    port = int(os.environ.get("QDRANT_PORT", "").strip() or "443")
    return QdrantClient(url=url, api_key=api_key, port=port, check_compatibility=False)


def collection_name() -> str:
    return os.environ.get("COLLECTION_NAME", "").strip() or "ev_providers"


def ensure_collection(client: QdrantClient | None = None) -> QdrantClient:
    c = client or _new_client()
    name = collection_name()
    existing = {x.name for x in c.get_collections().collections}
    if name not in existing:
        c.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    return c


def _point_to_provider(pid: str | int, payload: dict[str, Any] | None) -> dict[str, Any]:
    p = payload or {}
    return {
        "id": str(pid),
        "name": p.get("name", ""),
        "address": p.get("address", ""),
        "location": p.get("location", {}),
        "phone": p.get("phone", ""),
        "brand_certifications": p.get("brand_certifications", []),
        "subsystem_specialisations": p.get("subsystem_specialisations", []),
        "equipment": p.get("equipment", []),
        "rating": float(p.get("rating", 0.0) or 0.0),
        "review_count": int(p.get("review_count", 0) or 0),
        "emergency_available": bool(p.get("emergency_available", False)),
        "hours": p.get("hours", ""),
        "pricing_tier": p.get("pricing_tier", "mid"),
        "service_history_summary": p.get("service_history_summary", ""),
        "connector_types": p.get("connector_types", []),
        "description": p.get("description", ""),
        "created": p.get("created", ""),
    }


def list_providers(client: QdrantClient, page_size: int = 256) -> list[dict[str, Any]]:
    name = collection_name()
    out: list[dict[str, Any]] = []
    offset = None
    while True:
        records, offset = client.scroll(
            collection_name=name,
            limit=page_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for r in records:
            out.append(_point_to_provider(r.id, r.payload))
        if offset is None:
            break
    out.sort(key=lambda x: x.get("rating", 0.0), reverse=True)
    return out


def add_provider(
    client: QdrantClient,
    name: str,
    address: str,
    location: dict[str, float],
    phone: str,
    brand_certifications: list[str],
    subsystem_specialisations: list[str],
    equipment: list[str],
    rating: float,
    review_count: int,
    emergency_available: bool,
    hours: str,
    pricing_tier: str,
    service_history_summary: str,
    connector_types: list[str],
    description: str = "",
) -> str:
    pid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    vector = _provider_profile_embedding(
        name=name,
        address=address,
        brand_certifications=brand_certifications,
        subsystem_specialisations=subsystem_specialisations,
        equipment=equipment,
        description=description,
    )
    client.upsert(
        collection_name=collection_name(),
        points=[
            PointStruct(
                id=pid,
                vector=vector,
                payload={
                    "name": name,
                    "address": address,
                    "location": location,
                    "phone": phone,
                    "brand_certifications": brand_certifications,
                    "subsystem_specialisations": subsystem_specialisations,
                    "equipment": equipment,
                    "rating": rating,
                    "review_count": review_count,
                    "emergency_available": emergency_available,
                    "hours": hours,
                    "pricing_tier": pricing_tier,
                    "service_history_summary": service_history_summary,
                    "connector_types": connector_types,
                    "description": description,
                    "created": now,
                },
            )
        ],
    )
    return pid


def get_provider_details(client: QdrantClient, provider_id: str) -> dict[str, Any] | None:
    name = collection_name()
    r = client.retrieve(collection_name=name, ids=[provider_id], with_payload=True)
    if not r:
        return None
    return _point_to_provider(r[0].id, r[0].payload)


def search_providers(
    client: QdrantClient,
    query_vector: list[float] | None = None,
    query_text: str | None = None,
    subsystem: str = "",
    symptom_category: str | None = None,
    vehicle_brand: str | None = None,
    owner_location: dict[str, float] | None = None,
    radius_km: float = 40.0,
    urgency: str = "routine",
    limit: int = 5,
) -> list[dict[str, Any]]:
    name = collection_name()
    providers: list[dict[str, Any]] = []
    qfilters = []
    if vehicle_brand:
        qfilters.append(FieldCondition(key="brand_certifications", match=MatchValue(value=vehicle_brand)))
    if urgency and urgency.lower() == "urgent":
        qfilters.append(FieldCondition(key="emergency_available", match=MatchValue(value=True)))
    qfilter = Filter(must=qfilters) if qfilters else None

    if query_vector:
        try:
            result = client.search(
                collection_name=name,
                query_vector=query_vector,
                limit=max(limit * 3, 10),
                with_payload=True,
                filter=qfilter,
            )
            for hit in result:
                p = _point_to_provider(hit.id, hit.payload)
                p["match_score"] = float(hit.score or 0.0)
                providers.append(p)
        except Exception:
            providers = []

    if not providers:
        providers = list_providers(client)

    if subsystem:
        query = subsystem.lower()
        providers = [
            p
            for p in providers
            if query in p["name"].lower()
            or any(query in s.lower() for s in p["subsystem_specialisations"])
            or any(query in e.lower() for e in p["equipment"])
            or query in p.get("description", "").lower()
        ]
    if vehicle_brand:
        brand = vehicle_brand.lower()
        providers = [
            p for p in providers if any(brand in b.lower() for b in p["brand_certifications"])
        ]
    if urgency and urgency.lower() == "urgent":
        providers = [p for p in providers if p.get("emergency_available")]
    if owner_location:
        filtered = []
        for p in providers:
            loc = p.get("location") or {}
            if not loc or "lat" not in loc or "lng" not in loc:
                continue
            distance = haversine_distance(owner_location, {"lat": float(loc["lat"]), "lng": float(loc["lng"])})
            if distance <= radius_km:
                p["distance_km"] = round(distance, 1)
                filtered.append(p)
        providers = filtered

    providers.sort(
        key=lambda p: (
            -float(p.get("match_score", 0.0)),
            -float(p.get("rating", 0.0)),
            float(p.get("distance_km", 9999)),
        )
    )
    return providers[:limit]


def ensure_sample_providers(client: QdrantClient) -> None:
    existing = list_providers(client, page_size=20)
    if existing:
        return
    add_provider(
        client,
        name="Bengaluru EV Care Center",
        address="Koramangala 5th Block, Bengaluru",
        location={"lat": 12.9352, "lng": 77.6177},
        phone="+91 80 1234 5678",
        brand_certifications=["Ather", "Ola", "TVS"],
        subsystem_specialisations=["Battery/BMS", "Motor/Drivetrain", "Controller/Power Electronics"],
        equipment=["HV safety kit", "Ather diagnostics", "High-current charger"],
        rating=4.7,
        review_count=128,
        emergency_available=True,
        hours="08:00-20:00",
        pricing_tier="mid",
        service_history_summary="Trusted Bengaluru shop for battery, motor, and controller repairs.",
        connector_types=["Type 2", "CCS"],
        description="Specialises in fast EV diagnostics and emergency service for battery and motor faults.",
    )
    add_provider(
        client,
        name="Delhi EV Rescue",
        address="Sector 45, Gurugram",
        location={"lat": 28.4595, "lng": 77.0266},
        phone="+91 124 9876 5432",
        brand_certifications=["Ola", "Hero", "Bajaj"],
        subsystem_specialisations=["Charging Circuit", "Electrical", "Software/Dashboard"],
        equipment=["Battery charger", "OBD-II scanner", "Fast diagnostics"],
        rating=4.6,
        review_count=94,
        emergency_available=True,
        hours="07:00-22:00",
        pricing_tier="mid",
        service_history_summary="Emergency on-road support and scheduled repair for scooters and small cars.",
        connector_types=["Type 2"],
        description="Rapid-response team for charging and electrical issues in the Delhi-NCR region.",
    )
    add_provider(
        client,
        name="Hyderabad E-Mobility Hub",
        address="Banjara Hills, Hyderabad",
        location={"lat": 17.4323, "lng": 78.3971},
        phone="+91 40 2468 1357",
        brand_certifications=["Ather", "Ola", "Mahindra"],
        subsystem_specialisations=["Battery/BMS", "Motor/Drivetrain", "Suspension"],
        equipment=["High-voltage safety gear", "Motor test bench"],
        rating=4.8,
        review_count=110,
        emergency_available=False,
        hours="09:00-18:00",
        pricing_tier="premium",
        service_history_summary="Premium service centre focused on serious battery and drivetrain work.",
        connector_types=["CCS", "Type 2"],
        description="Well-equipped centre for in-depth EV diagnostics and repairs.",
    )
