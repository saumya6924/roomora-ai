from enum import Enum

from fastapi import HTTPException


def parse_enum[E: Enum](enum_cls: type[E], value: str, label: str = "Status") -> E:
    """Turn a string from the request body into an enum member, or answer 400 listing the allowed values."""
    try:
        return enum_cls(value)
    except ValueError:
        allowed = ", ".join(m.value for m in enum_cls)
        raise HTTPException(status_code=400, detail=f"{label} must be one of: {allowed}") from None
