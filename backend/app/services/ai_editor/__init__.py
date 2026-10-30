"""AI requirements editor: a text or voice command in, updated design requirements out.

Voice is not handled here: the browser turns speech into text first (see frontend/js/ai-editor.js).
Claude is tried first when an API key is set; any failure falls back to the offline rules engine.
"""

import logging

from app.core.config import settings
from app.schemas.designs import DesignRequirements
from app.services.ai_editor import claude as claude_engine
from app.services.ai_editor.prompt import describe_changes, requirements_to_prompt
from app.services.ai_editor.rules import rules_edit

log = logging.getLogger(__name__)


def edit_requirements(command: str, current: DesignRequirements, language: str = "auto") -> dict:
    engine = "rules"
    new_req, reply = None, ""

    if settings.anthropic_api_key:
        try:
            new_req, reply = claude_engine.claude_edit(command, current, language)
            engine = "claude"
        except Exception as error:  # no internet, bad key, bad JSON...
            log.warning("Claude failed, using rules engine instead: %s", error)

    if new_req is None:
        new_req, reply = rules_edit(command, current, language)

    return {
        "requirements": new_req,
        "prompt": requirements_to_prompt(new_req),
        "reply": reply or "Done!",
        "changes": describe_changes(current, new_req),
        "engine": engine,
    }
