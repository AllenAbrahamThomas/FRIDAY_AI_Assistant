from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException


def get_optional_user_id(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID")
) -> Optional[str]:
    if x_user_id is None:
        return None
    try:
        return str(UUID(x_user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-User-ID must be a UUID") from exc


def get_required_user_id(
    user_id: Optional[str] = Header(default=None, alias="X-User-ID")
) -> str:
    if user_id is None:
        raise HTTPException(status_code=401, detail="X-User-ID is required for memory access")
    validated_user_id = get_optional_user_id(user_id)
    if validated_user_id is None:
        raise HTTPException(status_code=401, detail="X-User-ID is required for memory access")
    return validated_user_id
