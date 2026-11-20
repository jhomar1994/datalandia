"""Reglas puras compartidas por Beam y pruebas, sin llamadas a GCP."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math

UTC = dt.timezone.utc


class InvalidEvent(ValueError):
    """Evento que debe enviarse a cuarentena."""


def object_json(raw):
    try:
        value = json.loads(raw)
    except (ValueError, TypeError) as error:
        raise InvalidEvent("json_invalido") from error
    if not isinstance(value, dict):
        raise InvalidEvent("json_no_es_objeto")
    return value


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise InvalidEvent("campo_ausente_" + field)
    return value.strip()


def number(value):
    if isinstance(value, bool):
        raise InvalidEvent("valor_no_numerico")
    try:
        result = float(value)
    except (ValueError, TypeError) as error:
        raise InvalidEvent("valor_no_numerico") from error
    if not math.isfinite(result):
        raise InvalidEvent("valor_no_finito")
    return result


def timestamp(value, field, aware):
    text(value, field)
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InvalidEvent("timestamp_invalido_" + field) from error
    if aware and result.tzinfo is None:
        raise InvalidEvent("timestamp_sin_zona_" + field)
    if not aware and result.tzinfo is not None:
        raise InvalidEvent("timestamp_local_con_zona_" + field)
    return result.astimezone(UTC) if aware else result


def digest(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def reject(source, reason, raw, batch_id=None):
    try:
        identity = object_json(raw)
        identity = {k: v for k, v in identity.items() if k not in {"published_at", "processed_at"}}
    except InvalidEvent:
        identity = raw
    return {
        "rejection_id": digest([source, str(reason), identity]),
        "source": source, "reason": str(reason), "raw_payload": raw,
        "processed_at": dt.datetime.now(UTC).isoformat(), "batch_id": batch_id,
    }


def validate_trip(raw, start_date="2024-01-01", end_date="2024-02-01"):
    r = object_json(raw)
    trip_id = text(r.get("trip_id"), "trip_id")
    zones = []
    for name in ("origin_id", "destination_id"):
        value = number(r.get(name))
        if not value.is_integer() or not 1 <= value <= 263:
            raise InvalidEvent("zona_invalida_" + name)
        zones.append(int(value))
    pickup = timestamp(r.get("pickup_local"), "pickup_local", aware=False)
    dropoff = timestamp(r.get("dropoff_local"), "dropoff_local", aware=False)
    start = dt.datetime.combine(dt.date.fromisoformat(start_date), dt.time())
    end = dt.datetime.combine(dt.date.fromisoformat(end_date), dt.time())
    if not start <= pickup < end:
        raise InvalidEvent("fecha_fuera_periodo")
    seconds = (dropoff - pickup).total_seconds()
    if not 0 < seconds <= 14400:
        raise InvalidEvent("duracion_invalida")
    miles = number(r.get("distance_miles"))
    amount = number(r.get("total_usd"))
    if not 0.3 <= miles <= 120:
        raise InvalidEvent("distancia_invalida")
    if amount <= 0:
        raise InvalidEvent("importe_invalido")
    result = {
        "trip_id": trip_id, "origin_id": zones[0], "destination_id": zones[1],
        "pickup_local": pickup.isoformat(), "dropoff_local": dropoff.isoformat(),
        "distance_km": miles * 1.609344, "total_usd": amount,
    }
    result["payload_hash"] = digest(result)
    return result


def validate_sensor(raw, nodes, sensors, event_start, event_end, shift_days=2191):
    r = object_json(raw)
    fields = ("event_id", "node_id", "subsystem", "sensor", "parameter", "unit")
    values = {field: text(r.get(field), field) for field in fields}
    if values["node_id"] not in nodes:
        raise InvalidEvent("nodo_no_homologado")
    key = tuple(values[field] for field in ("subsystem", "sensor", "parameter"))
    if key not in sensors:
        raise InvalidEvent("sensor_no_catalogado")
    catalog = sensors[key]
    if not catalog["unit"] or catalog["unit"] == "id":
        raise InvalidEvent("metrica_no_numerica")
    if values["unit"] != catalog["unit"]:
        raise InvalidEvent("unidad_no_coincide_catalogo")
    original = timestamp(r.get("original_ts"), "original_ts", aware=True)
    event = timestamp(r.get("event_ts"), "event_ts", aware=True)
    published = timestamp(r.get("published_at"), "published_at", aware=True)
    if event - original != dt.timedelta(days=shift_days):
        raise InvalidEvent("desplazamiento_temporal_invalido")
    if not event_start <= event < event_end:
        raise InvalidEvent("fecha_fuera_periodo")
    value = number(r.get("value"))
    low, high = catalog.get("min_value"), catalog.get("max_value")
    outside = None if low is None and high is None else bool(
        (low is not None and value < low) or (high is not None and value > high)
    )
    result = {
        **values, "zone_id": nodes[values["node_id"]], "value": value,
        "original_ts": original.isoformat(), "event_ts": event.isoformat(),
    }
    result["payload_hash"] = digest(result)
    result.update(published_at=published.isoformat(), out_of_range=outside)
    return result
