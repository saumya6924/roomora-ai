import io

import pytest
from PIL import Image

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import DesignImage
from app.services.image_ai import ImageProviderError
from app.services.image_ai import mock as mock_module


def room_photo(color=(200, 190, 170)):
    out = io.BytesIO()
    Image.new("RGB", (160, 120), color).save(out, "PNG")
    return out.getvalue()


def upload(client, who, data=None):
    return client.post(
        "/studio/upload",
        headers=who["headers"],
        files={"file": ("room.png", data or room_photo(), "image/png")},
    )


def generate(client, who, source_id, prompt="make the wall green"):
    return client.post(
        "/studio/generate", headers=who["headers"], json={"source_id": source_id, "prompt": prompt}
    )


def test_upload_generate_and_version_chain(client, accounts):
    user = accounts.make("Asha", "asha@gmail.com")
    original = upload(client, user)
    assert (
        original.status_code == 201
        and original.json()["kind"] == "original"
        and original.json()["parent_id"] is None
    )
    oid = original.json()["id"]

    first = generate(client, user, oid)
    assert (
        first.status_code == 201 and first.json()["kind"] == "generated" and first.json()["parent_id"] == oid
    )
    assert first.json()["provider"] == "mock"
    second = generate(client, user, first.json()["id"], "add indoor plants")  # edit the previous result
    assert second.json()["parent_id"] == first.json()["id"]

    family = client.get(f"/studio/images/{second.json()['id']}/versions", headers=user["headers"]).json()
    assert [i["id"] for i in family] == [oid, first.json()["id"], second.json()["id"]]
    assert len(client.get("/studio/history", headers=user["headers"]).json()) == 3

    # the signed URL really serves the picture, and the generated one differs from the original
    pic = client.get(first.json()["url"].replace("http://testserver", ""))
    assert pic.status_code == 200 and pic.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(pic.content)).size[0] > 0
    assert pic.content != client.get(original.json()["url"].replace("http://testserver", "")).content


def test_original_is_never_modified(client, accounts):
    user = accounts.make("Asha", "asha@gmail.com")
    photo = room_photo()
    oid = upload(client, user, photo).json()["id"]
    generate(client, user, oid)
    original_url = client.get(f"/studio/images/{oid}", headers=user["headers"]).json()["url"]
    assert client.get(original_url.replace("http://testserver", "")).content == photo


def test_photos_are_private_to_their_owner(client, accounts):
    owner = accounts.make("Asha", "asha@gmail.com")
    other = accounts.make("Bina", "bina@gmail.com")
    oid = upload(client, owner).json()["id"]
    assert client.get(f"/studio/images/{oid}", headers=other["headers"]).status_code == 404
    assert generate(client, other, oid).status_code == 404
    assert client.delete(f"/studio/images/{oid}", headers=other["headers"]).status_code == 404
    assert client.get("/studio/history", headers=other["headers"]).json() == []
    assert client.get("/studio/history").status_code == 401
    assert client.get("/files?token=forged").status_code == 404  # a forged link serves nothing


def test_upload_validation(client, accounts):
    user = accounts.make("Asha", "asha@gmail.com")
    assert upload(client, user, b"not an image").status_code == 400
    gif = io.BytesIO()
    Image.new("RGB", (4, 4)).save(gif, "GIF")
    assert upload(client, user, gif.getvalue()).status_code == 400
    assert generate(client, user, 9999).status_code == 404
    oid = upload(client, user).json()["id"]
    assert (
        client.post(
            "/studio/generate", headers=user["headers"], json={"source_id": oid, "prompt": "x"}
        ).status_code
        == 422
    )


def test_hindi_prompt_is_translated_for_the_image_model(client, accounts, monkeypatch):
    user = accounts.make("Asha", "asha@gmail.com")
    oid = upload(client, user).json()["id"]
    seen = {}
    original = mock_module.MockProvider.edit

    def spy(self, image, prompt, strength):
        seen["prompt"] = prompt
        return original(self, image, prompt, strength)

    monkeypatch.setattr(mock_module.MockProvider, "edit", spy)
    r = generate(client, user, oid, "दीवार का रंग हरा कर दो")
    assert r.status_code == 201
    assert "green walls" in seen["prompt"]  # English went to the model
    assert r.json()["prompt"] == "दीवार का रंग हरा कर दो"  # the user's own words are what we keep


def test_daily_cap_and_provider_failure(client, accounts, monkeypatch):
    user = accounts.make("Asha", "asha@gmail.com")
    oid = upload(client, user).json()["id"]

    def broken(self, image, prompt, strength):
        raise ImageProviderError("The image service is busy right now. Please try again in a minute.")

    with monkeypatch.context() as m:
        m.setattr(mock_module.MockProvider, "edit", broken)
        r = generate(client, user, oid)
        assert r.status_code == 502 and "busy" in r.json()["detail"]
    with SessionLocal() as db:
        assert db.query(DesignImage).count() == 1  # a failed generation leaves nothing behind

    monkeypatch.setattr(settings, "studio_daily_limit", 1)
    assert generate(client, user, oid).status_code == 201
    capped = generate(client, user, oid)
    assert capped.status_code == 429 and "today's limit" in capped.json()["detail"]


def test_generation_is_rate_limited_per_minute(client, accounts, monkeypatch):
    user = accounts.make("Asha", "asha@gmail.com")
    oid = upload(client, user).json()["id"]
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    codes = [generate(client, user, oid, f"idea {i}").status_code for i in range(6)]
    assert codes[:5] == [201] * 5 and codes[5] == 429


def test_deleting_an_original_removes_its_versions(client, accounts):
    user = accounts.make("Asha", "asha@gmail.com")
    oid = upload(client, user).json()["id"]
    child = generate(client, user, oid).json()["id"]
    keep = upload(client, user).json()["id"]
    assert client.delete(f"/studio/images/{child}", headers=user["headers"]).status_code == 200
    assert client.get(f"/studio/images/{oid}", headers=user["headers"]).status_code == 200  # parent stays
    generate(client, user, oid)
    assert client.delete(f"/studio/images/{oid}", headers=user["headers"]).status_code == 200
    ids = [i["id"] for i in client.get("/studio/history", headers=user["headers"]).json()]
    assert ids == [keep]


def test_cloudflare_provider_builds_the_request(monkeypatch):
    """No network: check the adapter sends the model call it should and reads an image reply."""
    from app.services.image_ai import cloudflare

    monkeypatch.setattr(settings, "cf_account_id", "acct123")
    monkeypatch.setattr(settings, "cf_api_token", "tok")
    sent = {}

    class Reply:
        status_code = 200
        headers = {"content-type": "image/png"}
        content = b"PNGDATA"
        text = ""

        def json(self):
            raise ValueError("not json")

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, json=json, headers=headers)
        return Reply()

    monkeypatch.setattr(cloudflare.httpx, "post", fake_post)
    assert cloudflare.CloudflareProvider().edit(room_photo(), "green walls", 0.7) == b"PNGDATA"
    assert sent["url"].endswith("/accounts/acct123/ai/run/@cf/runwayml/stable-diffusion-v1-5-img2img")
    assert sent["headers"]["Authorization"] == "Bearer tok"
    assert (
        sent["json"]["prompt"] == "green walls"
        and sent["json"]["strength"] == 0.7
        and sent["json"]["image_b64"]
    )

    Reply.status_code = 429
    with pytest.raises(ImageProviderError, match="busy"):
        cloudflare.CloudflareProvider().edit(room_photo(), "x", 0.5)


def test_cloudflare_rejection_is_logged_with_cloudflares_reason(monkeypatch, caplog):
    """A 403 must tell the admin what Cloudflare said, without leaking anything to the customer."""
    from app.services.image_ai import cloudflare

    monkeypatch.setattr(settings, "cf_account_id", "acct123")
    monkeypatch.setattr(settings, "cf_api_token", "secret-token")

    class Rejected:
        status_code = 403
        headers = {"content-type": "application/json"}
        text = ""

        def json(self):
            return {"errors": [{"code": 10000, "message": "Authentication error"}]}

    monkeypatch.setattr(cloudflare.httpx, "post", lambda *a, **k: Rejected())
    with caplog.at_level("WARNING"), pytest.raises(ImageProviderError, match="administrator needs to check"):
        cloudflare.CloudflareProvider().edit(room_photo(), "x", 0.5)
    assert "10000: Authentication error" in caplog.text
    assert "secret-token" not in caplog.text
