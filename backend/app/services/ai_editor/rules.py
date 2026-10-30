"""Engine 2: simple word rules. No internet and no API key needed."""

import re

from app.schemas.designs import DesignRequirements
from app.services.ai_editor.prompt import describe_changes, has_hindi
from app.services.ai_editor.vocab import (
    BUDGET_WORDS,
    COLORS,
    FURNITURE,
    LIGHT_STYLES,
    LIGHT_WORDS,
    MULTIPLIERS,
    REMOVE_WORDS,
    RESET_WORDS,
    SPACES,
    STYLES,
    WALL_WORDS,
)


def normalize(text: str) -> list[str]:
    """'Make the WALL green!' -> ['make', 'the', 'wall', 'green']"""
    text = text.lower()
    for mark in ",.!?;:()\"'।-":
        text = text.replace(mark, " ")
    return text.split()


def find_budget(command: str) -> int | None:
    """Find a rupee amount like 50000, 50,000, 50k, 1.5 lakh, 2 लाख.

    The number right AFTER the word 'budget' wins, so '2 seater sofa, budget 50000' works.
    """
    text = command.lower().replace(",", "").replace("₹", " ")
    text = re.sub(r"\brs\.?", " ", text)

    for word in BUDGET_WORDS:
        position = text.find(word)
        if position != -1:
            text = (
                text[position + len(word) :] + " " + text[:position]
            )  # after-part first, before-part as backup
            break

    match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Zऀ-ॿ]+)?", text)
    if not match:
        return None
    number = float(match.group(1))
    word = match.group(2) or ""
    return int(number * MULTIPLIERS.get(word, 1))


def rules_edit(command: str, current: DesignRequirements, language: str) -> tuple[DesignRequirements, str]:
    req = current.model_copy(deep=True)
    tokens = normalize(command)
    hindi = language == "hi" or has_hindi(command)

    if any(t in RESET_WORDS for t in tokens):
        return DesignRequirements(), ("सब कुछ रीसेट कर दिया गया।" if hindi else "Everything has been reset.")

    removing = any(t in REMOVE_WORDS for t in tokens)
    colors = [COLORS[t] for t in tokens if t in COLORS]
    furniture = list(dict.fromkeys(FURNITURE[t] for t in tokens if t in FURNITURE))

    if any(t in BUDGET_WORDS for t in tokens):
        amount = find_budget(command)
        if amount:
            req.budget_inr = amount

    for token in tokens:
        if token in SPACES:
            req.space_type = SPACES[token]
        if token in STYLES:
            req.style = STYLES[token]

    if any(t in LIGHT_WORDS for t in tokens):
        adjectives = [LIGHT_STYLES[t] for t in tokens if t in LIGHT_STYLES]
        if adjectives:
            req.lighting = " ".join(dict.fromkeys(adjectives)) + " lighting"

    if removing and furniture:
        for name in furniture:
            req.furniture = [item for item in req.furniture if name not in item]
    elif colors:
        color = colors[-1]  # "beige se green kar do" -> the LAST colour is the new one
        if any(t in WALL_WORDS for t in tokens):
            req.wall_color = color
        elif furniture:
            for name in furniture:
                new_list, found = [], False
                for item in req.furniture:
                    if name in item:  # "curved sofa" + sofa -> "green sofa"
                        new_list.append(f"{color} {name}")
                        found = True
                    else:
                        new_list.append(item)
                if not found:
                    new_list.append(f"{color} {name}")
                req.furniture = new_list
        else:
            req.main_colors = [color]
    elif furniture:
        for name in furniture:
            if not any(name in item for item in req.furniture):
                req.furniture.append(name)

    if not describe_changes(current, req):
        if hindi:
            return req, "माफ़ कीजिए, मैं समझ नहीं पाया। जैसे कहें: 'दीवार का रंग हरा कर दो' या 'बजट 50000 रखो'।"
        return req, "Sorry, I did not understand. Try: 'make the wall green' or 'set budget to 50000'."
    if hindi:
        return req, "ठीक है, बदलाव कर दिए गए हैं।"
    return req, "Done! I updated your requirements."
