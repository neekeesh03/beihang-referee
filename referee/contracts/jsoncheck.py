from __future__ import annotations
from typing import Any
import json
import re


def _matches_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def _stable_item_key(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return repr(value)


def validate_json_contract(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Dependency-free validator for the JSON-Schema subset used at LLM boundaries.

    This is intentionally stricter than a shape check: const/enum, numeric
    bounds, regex patterns, item uniqueness, item counts, string lengths, object
    requirements and additional-property rules are all enforced locally after a
    model response. Provider-side structured output is therefore not a trust
    boundary.
    """
    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: value does not equal const")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value not in enum")

    stype = schema.get("type")
    if isinstance(stype, list):
        if not any(_matches_type(value, t) for t in stype):
            return errors + [f"{path}: expected one of {stype}"]
    elif isinstance(stype, str) and not _matches_type(value, stype):
        return errors + [f"{path}: expected {stype}"]

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: required field missing")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}.{key}: additional property not allowed")
        for key, subschema in props.items():
            if key in value:
                errors.extend(validate_json_contract(value[key], subschema, f"{path}.{key}"))
        min_props = schema.get("minProperties")
        max_props = schema.get("maxProperties")
        if isinstance(min_props, int) and len(value) < min_props:
            errors.append(f"{path}: too few properties")
        if isinstance(max_props, int) and len(value) > max_props:
            errors.append(f"{path}: too many properties")

    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            errors.append(f"{path}: too many items")
        if schema.get("uniqueItems"):
            keys = [_stable_item_key(x) for x in value]
            if len(keys) != len(set(keys)):
                errors.append(f"{path}: duplicate items violate uniqueItems")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                errors.extend(validate_json_contract(item, item_schema, f"{path}[{i}]"))

    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string shorter than minLength")
        max_len = schema.get("maxLength")
        if isinstance(max_len, int) and len(value) > max_len:
            errors.append(f"{path}: string longer than maxLength")
        pattern = schema.get("pattern")
        if pattern and re.search(pattern, value) is None:
            errors.append(f"{path}: string does not match pattern")

    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: not above exclusiveMinimum")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: not below exclusiveMaximum")

    return errors
