import json

import httpx
import pytest
import respx
from tenacity import wait_none

from geral.config import Settings
from geral.send.recipients import (
    Recipient,
    latest_edition,
    publish_latest_edition,
    resolve_recipients,
)

API = "https://news.test/api/subscribers"
MAILTO = "mailto:news@fla.com?subject=Descadastrar"


def settings(token: str | None = "api-token", recipients: str = "dono@x.com") -> Settings:
    return Settings(
        NEWSLETTER_FROM="Flamengo News <news@fla.com>",
        NEWSLETTER_RECIPIENTS=recipients,
        PUBLIC_URL="https://news.test/",
        SUBSCRIBERS_API_TOKEN=token,
    )


def resolve(s: Settings):
    return resolve_recipients(s, "flamengo", client=httpx.Client(), wait=wait_none())


@respx.mock
def test_without_api_token_uses_only_the_fixed_list() -> None:
    route = respx.get(API, params={"team": "flamengo"})

    result = resolve(settings(token=None, recipients="dono@x.com, outro@x.com"))

    assert result.recipients == [
        Recipient("dono@x.com", MAILTO),
        Recipient("outro@x.com", MAILTO),
    ]
    assert result.from_api == 0
    assert not route.called


@respx.mock
def test_merges_fixed_list_with_subscribers_without_repeating() -> None:
    route = respx.get(API, params={"team": "flamengo"}).mock(
        return_value=httpx.Response(
            200,
            json=[
                {"email": "Dono@X.com", "unsubscribe_url": "https://news.test/unsubscribe?t=1"},
                {"email": "ana@y.com", "unsubscribe_url": "https://news.test/unsubscribe?t=2"},
            ],
        )
    )

    result = resolve(settings())

    assert route.calls.last.request.headers["Authorization"] == "Bearer api-token"
    assert result.recipients == [
        Recipient("dono@x.com", "https://news.test/unsubscribe?t=1"),
        Recipient("ana@y.com", "https://news.test/unsubscribe?t=2"),
    ]
    assert result.from_api == 2


@respx.mock
def test_api_failure_falls_back_to_the_fixed_list(caplog) -> None:
    route = respx.get(API, params={"team": "flamengo"}).mock(return_value=httpx.Response(503))

    with caplog.at_level("ERROR"):
        result = resolve(settings())

    assert result.recipients == [Recipient("dono@x.com", MAILTO)]
    assert result.from_api == 0
    assert route.call_count == 3
    assert "subscribers" in caplog.text.lower()


@respx.mock
def test_unauthorized_or_malformed_response_falls_back(caplog) -> None:
    respx.get(API, params={"team": "flamengo"}).mock(return_value=httpx.Response(401))
    assert resolve(settings()).from_api == 0

    respx.get(API, params={"team": "flamengo"}).mock(
        return_value=httpx.Response(200, json={"oops": True})
    )
    assert resolve(settings()).recipients == [Recipient("dono@x.com", MAILTO)]


@respx.mock
def test_network_error_falls_back() -> None:
    respx.get(API, params={"team": "flamengo"}).mock(side_effect=httpx.ConnectError("down"))

    assert resolve(settings()).recipients == [Recipient("dono@x.com", MAILTO)]


@respx.mock
def test_publish_latest_edition_puts_it_with_the_token() -> None:
    route = respx.put("https://news.test/api/teams/flamengo/latest-edition").mock(
        return_value=httpx.Response(204)
    )

    publish_latest_edition(
        settings(), "flamengo", "Assunto", "<p>h</p>", "t", client=httpx.Client()
    )

    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer api-token"
    assert json.loads(request.content) == {"subject": "Assunto", "html": "<p>h</p>", "text": "t"}


@respx.mock
def test_publish_latest_edition_raises_on_error() -> None:
    respx.put("https://news.test/api/teams/flamengo/latest-edition").mock(
        return_value=httpx.Response(401)
    )

    with pytest.raises(httpx.HTTPStatusError):
        publish_latest_edition(settings(), "flamengo", "A", "h", "t", client=httpx.Client())


@respx.mock
def test_latest_edition_reads_subject_and_send_time_with_the_token() -> None:
    body = {"subject": "Urubu News — Notícias", "published_at": "2026-10-16T19:11:00-03:00"}
    route = respx.get("https://news.test/api/teams/flamengo/latest-edition").mock(
        return_value=httpx.Response(200, json=body)
    )

    edition = latest_edition(settings(), "flamengo", client=httpx.Client())

    assert edition.subject == "Urubu News — Notícias"
    assert edition.published_at.isoformat() == "2026-10-16T19:11:00-03:00"
    assert route.calls.last.request.headers["Authorization"] == "Bearer api-token"


@respx.mock
def test_latest_edition_subject_is_none_when_nothing_was_published() -> None:
    respx.get("https://news.test/api/teams/flamengo/latest-edition").mock(
        return_value=httpx.Response(404)
    )

    assert latest_edition(settings(), "flamengo", client=httpx.Client()) is None


@respx.mock
def test_latest_edition_subject_raises_on_error() -> None:
    respx.get("https://news.test/api/teams/flamengo/latest-edition").mock(
        return_value=httpx.Response(500)
    )

    with pytest.raises(httpx.HTTPStatusError):
        latest_edition(settings(), "flamengo", client=httpx.Client())


def test_latest_edition_topic_titles_come_from_the_news_section() -> None:
    from geral.send.recipients import LatestEdition

    text = (
        "URUBU NEWS\n\n== Notícias ==\n\n* Empate em La Plata\nResumo.\n  - ge: https://x\n\n"
        "* Jorginho volta\nResumo.\n\n== Saiba mais ==\n\n* [Basquete] Título\n"
    )
    edition = LatestEdition(subject="s", published_at="2026-10-16T19:11:00-03:00", text=text)

    assert edition.topic_titles == ["Empate em La Plata", "Jorginho volta"]
    assert LatestEdition(subject="s", published_at="2026-10-16T19:11:00-03:00").topic_titles == []


BOLAO = "https://news.test/api/teams/vasco/bolao/matches"
SUMMARY = {"our_goals": 2, "their_goals": 1, "exact": ["Ana"], "top": [], "king": None}


@respx.mock
def test_subscribers_carry_their_bet_token() -> None:
    respx.get(API, params={"team": "flamengo"}).mock(
        return_value=httpx.Response(
            200, json=[{"email": "ana@y.com", "unsubscribe_url": "u", "bet_token": "BET"}]
        )
    )

    [ana] = resolve(settings(recipients="")).recipients

    assert ana.bet_token == "BET"


@respx.mock
def test_register_match_and_report_result_go_to_the_team_bolao() -> None:
    from datetime import UTC, datetime

    from geral.send.recipients import preview_summary, register_match, report_result

    put = respx.put(f"{BOLAO}/m1").mock(return_value=httpx.Response(204))
    result = respx.put(f"{BOLAO}/m1/result").mock(return_value=httpx.Response(200, json=SUMMARY))
    preview = respx.get(f"{BOLAO}/m1/summary", params={"ours": 2, "theirs": 1}).mock(
        return_value=httpx.Response(200, json=SUMMARY)
    )
    kickoff = datetime(2026, 11, 15, 21, 30, tzinfo=UTC)
    client = httpx.Client()

    register_match(settings(), "vasco", "m1", "Bahia", True, kickoff, client=client)
    summary = report_result(settings(), "vasco", "m1", 2, 1, client=client)
    previewed = preview_summary(settings(), "vasco", "m1", 2, 1, client=client)

    assert json.loads(put.calls.last.request.content) == {
        "opponent": "Bahia",
        "home": True,
        "kickoff": kickoff.isoformat(),
    }
    assert json.loads(result.calls.last.request.content) == {"our_goals": 2, "their_goals": 1}
    assert summary.exact == ["Ana"] and previewed == summary and preview.called


# --- drafts --------------------------------------------------------------------------------

DRAFT_URL = "https://news.test/api/teams/vasco/drafts/news/2026-11-16"


def draft_newsletter():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from fakes import FLAMENGO

    from geral.models import Edition, Newsletter

    tz = ZoneInfo("America/Sao_Paulo")
    edition = Edition(
        kind="news",
        start=datetime(2026, 11, 9, 13, tzinfo=tz),
        end=datetime(2026, 11, 16, 13, tzinfo=tz),
        label="Notícias — 16/11/2026",
    )
    return Newsletter(team=FLAMENGO, edition=edition, intro="Semana sem jogos.")


@respx.mock
def test_save_draft_puts_the_newsletter_under_kind_and_send_day() -> None:
    from datetime import datetime

    from geral.send.recipients import save_draft

    route = respx.put(DRAFT_URL).mock(return_value=httpx.Response(204))
    newsletter = draft_newsletter()

    assert save_draft(settings(), "vasco", newsletter, datetime(2026, 11, 16, 11, 0)) is True

    body = json.loads(route.calls.last.request.content)
    assert body["label"] == "Notícias — 16/11/2026"
    assert body["newsletter"]["intro"] == "Semana sem jogos."
    assert body["send_at"].startswith("2026-11-16T13:00")
    assert route.calls.last.request.headers["authorization"] == "Bearer api-token"


@respx.mock
def test_save_draft_already_there_is_false() -> None:
    from datetime import datetime

    from geral.send.recipients import save_draft

    respx.put(DRAFT_URL).mock(return_value=httpx.Response(409))

    assert save_draft(settings(), "vasco", draft_newsletter(), datetime(2026, 11, 16, 11)) is False


@respx.mock
def test_fetch_draft_reads_the_newsletter_and_the_review() -> None:
    from geral.send.recipients import fetch_draft

    newsletter = draft_newsletter()
    respx.get(DRAFT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "label": "Notícias — 16/11/2026",
                "newsletter": newsletter.model_dump(mode="json"),
                "held": True,
                "removed_topics": [1],
                "sent_at": None,
            },
        )
    )

    draft = fetch_draft(settings(), "vasco", newsletter.edition)

    assert draft.newsletter == newsletter
    assert (draft.held, draft.removed_topics, draft.sent_at) == (True, [1], None)


@respx.mock
def test_fetch_draft_missing_is_none_and_page_down_raises() -> None:
    from geral.send.recipients import fetch_draft

    edition = draft_newsletter().edition
    respx.get(DRAFT_URL).mock(return_value=httpx.Response(404))
    assert fetch_draft(settings(), "vasco", edition) is None

    respx.get(DRAFT_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(httpx.HTTPError):
        fetch_draft(settings(), "vasco", edition)


@respx.mock
def test_mark_draft_sent_posts_to_the_draft() -> None:
    from geral.send.recipients import mark_draft_sent

    route = respx.post(f"{DRAFT_URL}/sent").mock(return_value=httpx.Response(204))

    mark_draft_sent(settings(), "vasco", draft_newsletter().edition)

    assert route.called
