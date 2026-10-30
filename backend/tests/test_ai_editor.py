from app.core.config import settings
from app.schemas.designs import DesignRequirements
from app.services import ai_editor
from app.services.ai_editor import claude as claude_engine


def ai(client, token_headers, command, requirements=None, language="auto"):
    r = client.post(
        "/ai/edit-requirements",
        headers=token_headers,
        json={"command": command, "requirements": requirements or {}, "language": language},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_login_required_and_status(client):
    assert client.post("/ai/edit-requirements", json={"command": "hi"}).status_code == 401
    assert client.get("/ai/status").json()["engine"] == "rules"


def test_english(client, accounts):
    h = accounts.make("Ai Tester", "ai@gmail.com")["headers"]
    r = ai(client, h, "Make the wall green and set budget to 30,000", {"wall_color": "beige"})
    assert r["requirements"]["wall_color"] == "green" and r["requirements"]["budget_inr"] == 30000
    assert "green walls" in r["prompt"] and r["engine"] == "rules"
    assert ai(client, h, "budget 1.5 lakh")["requirements"]["budget_inr"] == 150000
    assert ai(client, h, "my 2 seater sofa budget 50k")["requirements"]["budget_inr"] == 50000
    assert ai(client, h, "Add a sofa and plants")["requirements"]["furniture"] == ["sofa", "indoor plants"]
    r = ai(client, h, "make the sofa blue", {"furniture": ["curved sofa", "rug"]})
    assert r["requirements"]["furniture"] == ["blue sofa", "rug"]  # edited, not duplicated
    r = ai(client, h, "remove the rug", {"furniture": ["blue sofa", "rug"]})
    assert r["requirements"]["furniture"] == ["blue sofa"]
    r = ai(client, h, "make it a luxury hotel with warm lights")
    assert (r["requirements"]["space_type"], r["requirements"]["style"]) == ("Hotel", "Luxury")
    assert r["requirements"]["lighting"] == "warm lighting"
    assert ai(client, h, "reset", {"wall_color": "red"})["requirements"]["wall_color"] == ""


def test_hindi_and_hinglish(client, accounts):
    h = accounts.make("Ai Tester", "ai@gmail.com")["headers"]
    r = ai(client, h, "दीवार का रंग हरा कर दो")
    assert r["requirements"]["wall_color"] == "green" and "बदलाव" in r["reply"]
    assert ai(client, h, "सोफे का रंग नीला कर दो")["requirements"]["furniture"] == ["blue sofa"]
    assert ai(client, h, "बजट 2 लाख रखो")["requirements"]["budget_inr"] == 200000
    assert ai(client, h, "कैफे बना दो")["requirements"]["space_type"] == "Cafe"
    assert ai(client, h, "पौधे जोड़ दो")["requirements"]["furniture"] == ["indoor plants"]
    assert ai(client, h, "सोफा हटा दो", {"furniture": ["blue sofa"]})["requirements"]["furniture"] == []

    assert ai(client, h, "deewar ka color laal kar do")["requirements"]["wall_color"] == "red"
    r = ai(client, h, "sofa ka color neela kar do, budget 1 lakh")
    assert r["requirements"]["furniture"] == ["blue sofa"] and r["requirements"]["budget_inr"] == 100000


def test_not_understood_and_validation(client, accounts):
    h = accounts.make("Ai Tester", "ai@gmail.com")["headers"]
    r = ai(client, h, "what is the weather", {"wall_color": "red"})
    assert r["requirements"]["wall_color"] == "red" and r["changes"] == [] and "Sorry" in r["reply"]
    assert "माफ़" in ai(client, h, "मौसम कैसा है")["reply"]
    assert client.post("/ai/edit-requirements", headers=h, json={"command": ""}).status_code == 422
    assert client.post("/ai/edit-requirements", headers=h, json={"command": "x" * 501}).status_code == 422


def test_claude_failure_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-fake-key")

    def broken(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(claude_engine, "claude_edit", broken)
    r = ai_editor.edit_requirements("make the wall green", DesignRequirements())
    assert r["engine"] == "rules" and r["requirements"].wall_color == "green"


def test_claude_path_with_fake_response(monkeypatch):
    """Our code must cope with Claude's JSON reply, even wrapped in markdown, without calling the internet."""
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-fake-key")

    class FakeMessages:
        def create(self, **kwargs):
            assert "CURRENT requirements" in kwargs["messages"][0]["content"]
            text = (
                '```json\n{"requirements": {"space_type": "Home", "wall_color": "sage green", '
                '"furniture": ["blue sofa"], "budget_inr": 100000}, "reply": "Theek hai, kar diya!"}\n```'
            )
            return type("R", (), {"content": [type("C", (), {"text": text})()]})()

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    r = ai_editor.edit_requirements(
        "deewar sage green kar do, sofa neela, budget 1 lakh", DesignRequirements()
    )
    assert r["engine"] == "claude" and r["requirements"].wall_color == "sage green"
    assert r["reply"] == "Theek hai, kar diya!" and r["requirements"].budget_inr == 100000
