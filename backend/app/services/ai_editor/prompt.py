"""Helpers shared by both engines."""

from app.schemas.designs import DesignRequirements


def has_hindi(text: str) -> bool:
    """True if the text contains Devanagari letters (the Hindi script)."""
    return any("ऀ" <= ch <= "ॿ" for ch in text)


def describe_changes(old: DesignRequirements, new: DesignRequirements) -> list[str]:
    """Compare old and new requirements and list what changed."""
    changes = []
    old_data, new_data = old.model_dump(), new.model_dump()
    for field in old_data:
        if old_data[field] != new_data[field]:
            before = old_data[field] if old_data[field] not in ("", [], None) else "(empty)"
            after = new_data[field] if new_data[field] not in ("", [], None) else "(empty)"
            changes.append(f"{field}: {before} -> {after}")
    return changes


def requirements_to_prompt(req: DesignRequirements) -> str:
    """One English sentence for the "Describe your dream design" box and the image AI.

    Image models understand English best, so this is always English.
    """
    first = f"Create a {req.style + ' ' if req.style else ''}{req.space_type.lower()} interior design"
    if req.wall_color:
        first += f" with {req.wall_color} walls"
    parts = [first]
    if req.main_colors:
        parts.append("main colors: " + ", ".join(req.main_colors))
    if req.furniture:
        parts.append("furniture: " + ", ".join(req.furniture))
    if req.materials:
        parts.append("materials: " + ", ".join(req.materials))
    if req.lighting:
        parts.append("lighting: " + req.lighting)
    if req.budget_inr:
        parts.append(f"budget around Rs {req.budget_inr:,}")
    if req.extra_notes:
        parts.append(req.extra_notes)
    return ", ".join(parts) + "."
