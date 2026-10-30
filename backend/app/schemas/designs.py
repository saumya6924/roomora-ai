from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DesignRequirements(BaseModel):
    """What the user wants in their room. The AI editor changes this object."""

    space_type: str = "Home"
    style: str = ""
    wall_color: str = ""
    main_colors: list[str] = Field(default_factory=list)
    furniture: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    lighting: str = ""
    budget_inr: int | None = None
    extra_notes: str = ""


class AIEditRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)  # typed, or spoken and already converted to text
    requirements: DesignRequirements = Field(default_factory=DesignRequirements)
    language: str = "auto"  # "en", "hi" or "auto"


class AIEditResponse(BaseModel):
    requirements: DesignRequirements
    prompt: str  # ready-to-use text for the "Describe your dream design" box
    reply: str  # short message in the user's language
    changes: list[str]
    engine: str  # "claude" or "rules"


class SavedDesignCreate(BaseModel):
    title: str = Field(default="My design", max_length=150)
    prompt: str = ""
    space_type: str = "Home"
    requirements: DesignRequirements = Field(default_factory=DesignRequirements)
    image_url: str = ""
    design_image_id: int | None = None


class SavedDesignOut(ORMModel):
    id: int
    title: str
    prompt: str
    space_type: str
    requirements: dict
    image_url: str
    design_image_id: int | None
    created_at: datetime
