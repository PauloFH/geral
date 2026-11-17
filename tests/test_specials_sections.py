"""Which special sections an edition gets (a seeded draw) and how they enter the build."""

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import respx
from test_build_newsletter import ARTICLE, SETTINGS, FakeStats, good_llm

from geral import pipeline
from geral.config import Settings
from geral.models import Edition, Story
from geral.specials import sections
from geral.specials.sections import Sections, pick_sections
from geral.teams import get_team

TZ = ZoneInfo("America/Sao_Paulo")
NAUTICO = get_team("nautico")
STORY = {
    "id": 7,
    "kind": "clube",
    "title": "Como o Náutico virou Timbu",
    "body": "Em 19 de agosto de 1934…",
    "summary": "A provocação que virou mascote.",
    "fact_date": "1934-08-19",
    "source_title": "Clube Náutico Capibaribe — Mascote",
    "source_url": "https://pt.wikipedia.org/wiki/Clube_N%C3%A1utico_Capibaribe",
}
FACT = {"date": "1934-08-19", "title": "Timbu", "summary": "O Náutico ganhou o apelido de Timbu."}


def edition(kind: str = "news", label: str = "Notícias — 17/08/2026") -> Edition:
    end = datetime(2026, 8, 17, 13, tzinfo=TZ)
    return Edition(kind=kind, start=end.replace(day=10), end=end, label=label)


def always(draws: list):
    def draw():
        draws.append(1)
        return STORY

    return draw


def test_news_edition_gets_a_story_and_caps_topics_at_6(monkeypatch) -> None:
    monkeypatch.setattr(sections, "STORY_CHANCE", 1.0)

    picked = pick_sections(edition(), NAUTICO, draw=always([]), facts=lambda: [])

    assert picked.story == Story(**STORY)
    assert picked.max_topics == 6


def test_pre_and_post_get_only_on_this_day(monkeypatch) -> None:
    monkeypatch.setattr(sections, "STORY_CHANCE", 1.0)
    monkeypatch.setattr(sections, "ON_THIS_DAY_CHANCE", 1.0)
    draws: list = []

    picked = pick_sections(edition("pre"), NAUTICO, draw=always(draws), facts=lambda: [FACT])

    assert picked.story is None and draws == []
    assert picked.on_this_day == ["Há 92 anos, em 19/08/1934: O Náutico ganhou o apelido de Timbu."]


def test_draw_is_seeded_by_the_label() -> None:
    def outcome(label: str) -> tuple:
        p = pick_sections(edition(label=label), NAUTICO, draw=lambda: STORY, facts=lambda: [FACT])
        return (p.story is not None, bool(p.on_this_day))

    labels = [f"Notícias — {d:02d}/08/2026" for d in range(1, 29)]
    assert [outcome(label) for label in labels] == [outcome(label) for label in labels]
    assert len({outcome(label) for label in labels}) > 1  # a draw, not always the same


def test_on_this_day_lines_count_the_years() -> None:
    new_year = Edition(
        kind="news",
        start=datetime(2026, 12, 23, 13, tzinfo=TZ),
        end=datetime(2026, 12, 30, 13, tzinfo=TZ),
        label="x",
    )
    fact = {"date": "1968-01-02", "title": "Hexa", "summary": "O hexa."}

    assert (
        sections.on_this_day_line(fact, new_year.end.date()) == "Há 59 anos, em 02/01/1968: O hexa."
    )


class NoMatch(FakeStats):
    def get_last_match(self, start, end):
        return None


def build(specials, articles):
    return pipeline.build_newsletter(
        edition(),
        NAUTICO,
        SETTINGS,
        collect=lambda edition, settings: articles,
        stats_client=NoMatch(),
        llm=good_llm(),
        candidates=lambda edition, settings: ([], []),
        specials=specials,
    )


def test_section_caps_news_at_6_topics(monkeypatch) -> None:
    seen = {}
    real = pipeline.summarize_edition

    def spy(*args, **kwargs):
        seen["max_topics"] = kwargs["max_topics"]
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline, "summarize_edition", spy)
    picked = Sections(story=Story(**STORY), max_topics=6)

    newsletter = build(lambda e, t, second_chance=False: picked, [ARTICLE])

    assert seen["max_topics"] == 6
    assert newsletter.story.title == "Como o Náutico virou Timbu"


def test_story_is_forced_when_there_is_no_news() -> None:
    calls = []

    def specials(e, t, second_chance=False):
        calls.append(second_chance)
        return Sections(story=Story(**STORY)) if second_chance else Sections()

    newsletter = build(specials, [])

    assert calls == [False, True]
    assert newsletter.story is not None


@respx.mock
def test_build_without_stories_or_page_has_no_section() -> None:
    settings = Settings(SUBSCRIBERS_API_TOKEN="t", PUBLIC_URL="https://geral.test", DRY_RUN=False)
    respx.post("https://geral.test/api/teams/nautico/stories/draw").mock(
        return_value=httpx.Response(503)
    )
    respx.get("https://geral.test/api/teams/nautico/stories/on-this-day").mock(
        return_value=httpx.Response(204)
    )

    picked = sections.from_page(settings)(edition(), NAUTICO, second_chance=True)

    assert picked == Sections()


def test_story_only_edition_is_not_empty() -> None:
    newsletter = build(lambda e, t, second_chance=False: Sections(story=Story(**STORY)), [])

    assert not pipeline.is_empty(newsletter)


def test_a_failing_on_this_day_keeps_the_reserved_story(monkeypatch) -> None:
    monkeypatch.setattr(sections, "STORY_CHANCE", 1.0)
    monkeypatch.setattr(sections, "ON_THIS_DAY_CHANCE", 1.0)

    def facts():
        raise httpx.ConnectError("down")

    picked = sections.pick_sections(edition(), NAUTICO, draw=lambda: STORY, facts=facts)

    assert picked.story is not None and picked.on_this_day == []


def test_a_bad_answer_from_the_page_leaves_the_section_out() -> None:
    picked = sections.pick_sections(
        edition(), NAUTICO, draw=lambda: {"id": "x"}, facts=lambda: [], force_story=True
    )

    assert picked == Sections()


def test_on_this_day_skips_facts_of_this_year_and_sorts_by_date(monkeypatch) -> None:
    monkeypatch.setattr(sections, "ON_THIS_DAY_CHANCE", 1.0)
    found = [
        {"date": "1968-08-18", "title": "b", "summary": "B."},
        {"date": "2026-08-16", "title": "c", "summary": "C."},
        {"date": "1934-08-19", "title": "a", "summary": "A."},
    ]

    picked = pick_sections(edition("pre"), NAUTICO, draw=lambda: None, facts=lambda: found)

    assert [line[-2:] for line in picked.on_this_day] == ["A.", "B."]
