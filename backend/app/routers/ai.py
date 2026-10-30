"""The AI requirements editor: POST /ai/edit-requirements."""

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.ratelimit import ai_limit
from app.core.security import get_current_user
from app.models import User
from app.schemas.designs import AIEditRequest, AIEditResponse
from app.services.ai_editor import edit_requirements

router = APIRouter(prefix="/ai", tags=["AI Editor"])


# A plain `def`: FastAPI runs it in a worker thread, so a slow Claude call does not block other users.
@router.post("/edit-requirements", response_model=AIEditResponse, dependencies=[Depends(ai_limit)])
def edit_with_ai(data: AIEditRequest, user: User = Depends(get_current_user)):
    return edit_requirements(data.command, data.requirements, data.language)


@router.get("/status")
def ai_status():
    """Is Claude connected, or are we on the simple rules engine?"""
    has_key = bool(settings.anthropic_api_key)
    return {"engine": "claude" if has_key else "rules", "model": settings.ai_model if has_key else None}
