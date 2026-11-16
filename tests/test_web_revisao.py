"""The owner's review page: a signed link per draft; hold/release the edition, drop topics."""

import re
from datetime import timedelta

import pytest
from test_renderer import full_newsletter
from webkit import NOW, SECRET, make_client

from geral.models import Topic
from geral.web.tokens import make_token

OWNER = "dono@example.com"


@pytest.fixture
def owner(store, mailer, clock):
    return make_client(store, mailer, clock, NOTIFY_EMAIL=OWNER)


def link(when=NOW, purpose: str = "review", email: str = OWNER) -> str:
    return make_token(SECRET, purpose, email, when)


def newsletter():
    n = full_newsletter()
    rumor = Topic(title="Rumor de contratação", summary="Um meia é sondado.", importance=3)
    return n.model_copy(update={"topics": [*n.topics, rumor]})


def draft(store, send_in=timedelta(hours=5), kind: str = "news", team: str = "flamengo"):
    day = (NOW + send_in).date().isoformat()
    store.save_draft(
        team,
        kind,
        day,
        f"Notícias — {day}",
        newsletter().model_dump_json(),
        NOW,
        NOW + send_in,
    )
    return store.draft(team, kind, day)


def post(client, path: str, token: str | None = None):
    return client.post(path, data={"t": token or link()}, follow_redirects=False)


def test_review_page_lists_pending_drafts(owner, store) -> None:
    d = draft(store)

    page = owner.get(f"/revisao?t={link()}")

    assert page.status_code == 200
    assert "Urubu News" in page.text and d.label in page.text
    assert "Vitória no clássico" in page.text and "Rumor de contratação" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert page.headers["referrer-policy"] == "no-referrer"


def test_review_page_rejects_token_of_other_purpose(owner, store) -> None:
    draft(store)

    assert owner.get(f"/revisao?t={link(purpose='team-requests')}").status_code == 404
    assert owner.get(f"/revisao?t={link(email='outro@example.com')}").status_code == 404
    assert owner.get("/revisao").status_code == 404


def test_review_page_rejects_expired_token(owner) -> None:
    old = link(NOW - timedelta(days=8))

    assert owner.get(f"/revisao?t={old}").status_code == 404


def test_review_actions_reject_a_bad_token(owner, store) -> None:
    d = draft(store)

    response = post(owner, f"/revisao/{d.id}/segurar", link(purpose="team-requests"))

    assert response.status_code == 404
    assert store.draft_by_id(d.id).held is False


def test_hold_and_release_from_the_page(owner, store) -> None:
    d = draft(store)

    held = post(owner, f"/revisao/{d.id}/segurar")

    assert held.status_code == 303 and held.headers["location"].startswith("/revisao?t=")
    assert store.draft_by_id(d.id).held is True
    assert "segurada" in owner.get(f"/revisao?t={link()}").text.lower()

    post(owner, f"/revisao/{d.id}/soltar")
    assert store.draft_by_id(d.id).held is False


def test_remove_topic_from_the_page_hides_it_in_the_preview(owner, store) -> None:
    d = draft(store)

    assert post(owner, f"/revisao/{d.id}/topicos/0/tirar").status_code == 303

    assert store.draft_by_id(d.id).removed_topics == [0]
    preview = owner.get(f"/revisao/{d.id}/previa?t={link()}")
    assert preview.status_code == 200
    assert "Um meia é sondado." in preview.text
    assert "venceu o Fluminense por 1 a 0" not in preview.text

    post(owner, f"/revisao/{d.id}/topicos/0/voltar")
    assert store.draft_by_id(d.id).removed_topics == []


def test_remove_topic_after_sent_is_409(owner, store) -> None:
    d = draft(store)
    store.mark_draft_sent("flamengo", "news", d.day, NOW)

    assert post(owner, f"/revisao/{d.id}/topicos/0/tirar").status_code == 409
    assert post(owner, f"/revisao/{d.id}/segurar").status_code == 409
    assert store.draft_by_id(d.id).removed_topics == []


def test_remove_unknown_topic_is_404(owner, store) -> None:
    d = draft(store)

    assert post(owner, f"/revisao/{d.id}/topicos/7/tirar").status_code == 404
    assert post(owner, "/revisao/999/segurar").status_code == 404
    assert store.draft_by_id(d.id).removed_topics == []


def test_held_and_late_draft_can_still_be_changed(owner, store, clock) -> None:
    d = draft(store)
    post(owner, f"/revisao/{d.id}/segurar")
    clock.now = NOW + timedelta(hours=8)  # past its send time

    assert post(owner, f"/revisao/{d.id}/topicos/1/tirar", link(clock.now)).status_code == 303
    assert post(owner, f"/revisao/{d.id}/soltar", link(clock.now)).status_code == 303
    assert store.draft_by_id(d.id).released_at == clock.now


def test_release_after_a_newer_edition_is_409(owner, store, clock) -> None:
    d = draft(store)
    post(owner, f"/revisao/{d.id}/segurar")
    clock.now = NOW + timedelta(days=3)
    store.set_latest_edition("flamengo", "Urubu News — Notícias — x", "h", "t", clock.now)

    response = post(owner, f"/revisao/{d.id}/soltar", link(clock.now))

    assert response.status_code == 409
    assert store.draft_by_id(d.id).held is True


def test_review_page_says_when_nothing_is_pending(owner) -> None:
    page = owner.get(f"/revisao?t={link()}")

    assert page.status_code == 200
    assert re.search(r"nenhuma edição", page.text, re.I)
