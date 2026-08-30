from __future__ import annotations

from jsonschema import Draft202012Validator


def normalize_payload(schema: dict, payload: dict) -> dict:
    """Coerce HTML form values into JSON Schema types so every catalog form can save."""
    properties: dict = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    normalized: dict = {}
    for key, spec in properties.items():
        if key in payload:
            value = _coerce(spec, payload[key])
        elif spec.get("type") == "boolean":
            value = False
        elif spec.get("type") == "array" and key in required:
            value = []
        else:
            continue
        if _should_omit(spec, value, required=key in required):
            continue
        normalized[key] = value
    return normalized


def validate_payload(schema: dict, payload: dict) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(p) for p in error.path) or '$'}: {error.message}"
        for error in validator.iter_errors(payload)
    ]


def _coerce(spec: dict, value: object) -> object:
    kind = spec.get("type")
    if kind == "integer":
        return _as_int(value)
    if kind == "boolean":
        return _as_bool(value)
    if kind == "array":
        return _as_list(value)
    if kind == "string":
        coerced = "" if value is None else str(value).strip()
        fmt = spec.get("format")
        if fmt == "time":
            return _as_time(coerced)
        if fmt == "date-time":
            return _as_datetime(coerced)
        return coerced
    return value


def _should_omit(spec: dict, value: object, *, required: bool) -> bool:
    if required:
        return False
    if spec.get("type") == "boolean":
        return False
    if spec.get("type") == "array":
        return value == []
    return value in ("", None)


def _as_int(value: object) -> int | object:
    if isinstance(value, bool) or value in ("", None):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            number = float(value)
        except ValueError:
            return value
        if number.is_integer():
            return int(number)
    return value


def _as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _as_list(value: object) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [item for item in value if item not in ("", None)]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [value]


def _as_time(value: str) -> str:
    if len(value) == 5 and value[2] == ":":
        return f"{value}:00"
    return value


def _as_datetime(value: str) -> str:
    if len(value) == 16 and value[10] == "T":
        return f"{value}:00"
    return value
