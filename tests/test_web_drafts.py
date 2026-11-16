"""Drafts: each team edition is built first (kept on the page) and sent later."""

from datetime import datetime
from zoneinfo import ZoneInfo

from test_renderer import full_newsletter
from webkit import AUTH

from geral.models import Newsletter

TZ = ZoneInfo("America/Sao_Paulo")
URL = "/api/teams/vasco/drafts/news/2026-11-16"


def draft_in(**changes) -> dict:
    body = {
        "label": "Notícias — 16/11/2026",
        "newsletter": full_newsletter().model_dump(mode="json"),
        "build_at": datetime(2026, 11, 16, 8, 0, tzinfo=TZ).isoformat(),
        "send_at": datetime(2026, 11, 16, 13, 0, tzinfo=TZ).isoformat(),
    }
    return body | changes


def test_newsletter_survives_json_round_trip() -> None:
    newsletter = full_newsletter()

    assert Newsletter.model_validate_json(newsletter.model_dump_json()) == newsletter


def test_put_draft_then_get(client) -> None:
    assert client.put(URL, json=draft_in(), headers=AUTH).status_code == 204

    draft = client.get(URL, headers=AUTH).json()

    assert draft["label"] == "Notícias — 16/11/2026"
    assert Newsletter.model_validate(draft["newsletter"]) == full_newsletter()
    assert (draft["held"], draft["removed_topics"], draft["sent_at"]) == (False, [], None)


def test_put_draft_twice_is_409_and_keeps_first(client) -> None:
    client.put(URL, json=draft_in(), headers=AUTH)

    again = client.put(URL, json=draft_in(label="outro"), headers=AUTH)

    assert again.status_code == 409
    assert client.get(URL, headers=AUTH).json()["label"] == "Notícias — 16/11/2026"


def test_get_unknown_draft_is_404(client) -> None:
    assert client.get(URL, headers=AUTH).status_code == 404


def test_drafts_require_token(client) -> None:
    assert client.put(URL, json=draft_in()).status_code == 401
    assert client.get(URL).status_code == 401
    assert client.post(f"{URL}/sent").status_code == 401


def test_unknown_team_is_404(client) -> None:
    url = "/api/teams/xyz/drafts/news/2026-11-16"

    assert client.put(url, json=draft_in(), headers=AUTH).status_code == 404


def test_mark_sent_sets_sent_at(client) -> None:
    client.put(URL, json=draft_in(), headers=AUTH)

    assert client.post(f"{URL}/sent", headers=AUTH).status_code == 204
    assert client.get(URL, headers=AUTH).json()["sent_at"] is not None
    assert (
        client.post("/api/teams/vasco/drafts/pre/2026-11-16/sent", headers=AUTH).status_code == 404
    )


def test_drafts_are_kept_per_team_kind_and_day(client) -> None:
    client.put(URL, json=draft_in(), headers=AUTH)

    assert client.get("/api/teams/vasco/drafts/post/2026-11-16", headers=AUTH).status_code == 404
    assert client.get("/api/teams/abc/drafts/news/2026-11-16", headers=AUTH).status_code == 404
