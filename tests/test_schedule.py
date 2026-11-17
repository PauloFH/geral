from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from geral.schedule import Fixture, Slot, due, due_stage, due_stages, label_of, plan

TZ = ZoneInfo("America/Sao_Paulo")
UTC = ZoneInfo("UTC")


def at(day: str, hour: str = "08:00") -> datetime:
    return datetime.strptime(f"{day} {hour}", "%d/%m/%Y %H:%M").replace(tzinfo=TZ)


def fixture(
    kickoff: datetime, match_id: str = "1", time_valid: bool = True, state: str = "pre"
) -> Fixture:
    return Fixture(
        match_id=match_id,
        league="bra.1",
        kickoff=kickoff,
        time_valid=time_valid,
        state=state,
        home="Flamengo",
        away="Rival",
    )


def until_last_match(slots: list[Slot]) -> list[Slot]:
    """Drop the weekly news planned after the last known match."""
    last = max(i for i, s in enumerate(slots) if s.kind == "post")
    return slots[: last + 1]


def summary(slots: list[Slot]) -> list[tuple[str, str]]:
    return [(s.kind, s.send_at.astimezone(TZ).strftime("%d/%m %H:%M")) for s in slots]


OCTOBER = [
    fixture(datetime(2026, 10, 18, 21, 30, tzinfo=UTC), "bahia"),
    fixture(datetime(2026, 10, 23, 0, 30, tzinfo=UTC), "estudiantes"),
    fixture(datetime(2026, 10, 26, 23, 0, tzinfo=UTC), "atletico"),
    fixture(datetime(2026, 10, 29, 23, 0, tzinfo=UTC), "vasco"),
    fixture(datetime(2026, 11, 4, 22, 30, tzinfo=UTC), "gremio"),
    fixture(datetime(2026, 11, 18, 20, 0, tzinfo=UTC), "athletico", time_valid=False),
]
NOW = at("17/10/2026", "12:00")
LAST_SENT = at("16/10/2026", "19:11")


def test_plan_matches_the_real_october_calendar() -> None:
    slots = plan(OCTOBER, NOW, LAST_SENT)

    assert summary(slots) == [
        ("pre", "18/10 14:30"),
        ("post", "19/10 13:00"),
        ("news", "21/10 13:00"),
        ("pre", "22/10 17:30"),
        ("post", "23/10 13:00"),
        ("news", "25/10 13:00"),
        ("pre", "26/10 16:00"),
        ("post", "27/10 13:00"),
        ("pre", "29/10 16:00"),
        ("post", "30/10 13:00"),
        ("news", "02/11 13:00"),
        ("pre", "04/11 15:30"),
        ("post", "05/11 13:00"),
        ("news", "08/11 13:00"),
        ("news", "11/11 13:00"),
        ("news", "15/11 13:00"),
        ("pre", "18/11 10:00"),
        ("post", "19/11 13:00"),
    ]
    assert slots[0].label == "Pré-jogo — 18/10/2026"
    assert slots[1].label == "Pós-jogo — 19/10/2026"
    assert slots[2].label == "Notícias — 21/10/2026"
    assert (slots[0].match_id, slots[0].league) == ("bahia", "bra.1")
    assert slots[2].match_id is None


def builds(slots: list[Slot]) -> list[tuple[str, str, str]]:
    return [
        (s.kind, s.build_at.astimezone(TZ).strftime("%d/%m %H:%M"), s.send_at.strftime("%H:%M"))
        for s in slots
    ]


def test_news_and_post_build_at_8_send_at_13() -> None:
    slots = plan([fixture(at("18/10/2026", "20:00"))], NOW, LAST_SENT)

    assert builds(slots)[1:3] == [
        ("post", "19/10 08:00", "13:00"),
        ("news", "26/10 08:00", "13:00"),
    ]


@pytest.mark.parametrize(
    ("kickoff", "expected"),
    [
        # 6 h before the kick-off, out 2 h later (4 h before the game)
        (at("25/10/2026", "21:30"), ("pre", "25/10 15:30", "17:30")),
        (at("25/10/2026", "16:00"), ("pre", "25/10 10:00", "12:00")),
        # never built before 8am
        (at("25/10/2026", "12:00"), ("pre", "25/10 08:00", "10:00")),
        # a morning game: built at 18:00 and out at 20:00 the night before
        (at("25/10/2026", "10:00"), ("pre", "24/10 18:00", "20:00")),
    ],
)
def test_pre_game_builds_6h_before_sends_4h_before(kickoff, expected) -> None:
    slots = plan([fixture(kickoff)], at("23/10/2026"), at("23/10/2026"))

    assert builds(slots)[0] == expected
    assert slots[0].send_at.astimezone(TZ).strftime("%d/%m") == expected[1][:5]


def test_tbd_kickoff_builds_pre_game_at_8am_on_match_day() -> None:
    slots = plan([fixture(at("25/10/2026", "16:00"), time_valid=False)], NOW, LAST_SENT)

    assert [s for s in builds(slots) if s[0] != "news"][0] == ("pre", "25/10 08:00", "10:00")


def test_postponed_match_has_no_slots() -> None:
    match = fixture(at("19/10/2026", "20:00"), state="postponed")

    assert all(s.match_id != match.match_id for s in plan([match], NOW, LAST_SENT))


def test_no_news_when_gap_is_72h_or_less() -> None:
    games = [fixture(at("18/10/2026", "20:00"), "a"), fixture(at("21/10/2026", "20:00"), "b")]

    kinds = [k for k, _ in summary(until_last_match(plan(games, NOW, LAST_SENT)))]

    assert kinds == ["pre", "post", "pre", "post"]


def test_long_gap_spreads_news_evenly() -> None:
    games = [fixture(at("18/10/2026", "20:00"), "a"), fixture(at("31/10/2026", "20:00"), "b")]

    news = [d for k, d in summary(until_last_match(plan(games, NOW, LAST_SENT))) if k == "news"]

    # 19/10 13:00 -> 31/10 16:00 is 291 h: 3 editions, one every ~72.75 h
    assert news == ["22/10 13:00", "25/10 13:00", "28/10 13:00"]


def test_no_fixtures_means_weekly_monday_news() -> None:
    news = summary(plan([], NOW, LAST_SENT))

    assert news == [("news", "26/10 13:00"), ("news", "02/11 13:00"), ("news", "09/11 13:00")]


def test_window_starts_when_the_previous_edition_was_built() -> None:
    # The draft collects news up to its build: what comes out until the send goes in the next one.
    slots = plan(OCTOBER, NOW, LAST_SENT)

    assert slots[0].window_start == LAST_SENT - timedelta(hours=5)  # a news/post went at 13:00
    assert all(b.window_start == a.build_at for a, b in zip(slots, slots[1:], strict=False))


def test_window_after_a_pre_game_starts_2h_before_its_send() -> None:
    sent = at("18/10/2026", "14:31")

    slots = plan(OCTOBER, at("18/10/2026", "15:00"), sent, "Pré-jogo — 18/10/2026")

    assert slots[0].window_start == sent - timedelta(hours=2)


def test_utc_midnight_kickoff_uses_local_date() -> None:
    slots = plan([OCTOBER[1]], at("20/10/2026"), at("20/10/2026"))

    assert summary(slots)[:2] == [("pre", "22/10 17:30"), ("post", "23/10 13:00")]


def test_due_returns_slot_only_inside_grace_window() -> None:
    slots = plan(OCTOBER, NOW, LAST_SENT)

    assert due(slots, at("18/10/2026", "14:29")) is None
    assert due(slots, at("18/10/2026", "14:30")).label == "Pré-jogo — 18/10/2026"
    assert due(slots, at("18/10/2026", "17:29")).label == "Pré-jogo — 18/10/2026"
    assert due(slots, at("18/10/2026", "17:30")) is None


def test_due_ignores_slots_before_last_send() -> None:
    # The pre-game went out at 14:31; a reschedule must not make it due again.
    sent = at("18/10/2026", "14:31")
    slots = plan(OCTOBER, at("18/10/2026", "15:00"), sent)

    assert due(slots, at("18/10/2026", "15:00")) is None
    assert slots[0].kind == "post" and slots[0].window_start == sent - timedelta(hours=5)


def test_due_picks_the_latest_when_two_are_inside_the_window() -> None:
    morning = at("21/10/2026", "07:00")
    late = Slot(
        kind="news",
        build_at=morning,
        send_at=at("21/10/2026", "09:00"),
        window_start=NOW,
        label="b",
    )
    early = Slot(
        kind="post",
        build_at=morning,
        send_at=at("21/10/2026", "08:00"),
        window_start=NOW,
        label="a",
    )

    assert due([early, late], at("21/10/2026", "09:30")) == late


def test_now_defaults_to_last_sent_window_start_when_never_sent() -> None:
    slots = plan(OCTOBER[:1], NOW, None)

    assert slots[0].window_start == NOW - timedelta(days=3)


def test_weekly_news_after_the_last_known_match() -> None:
    games = [fixture(at("18/10/2026", "20:00"))]

    news = [d for k, d in summary(plan(games, NOW, LAST_SENT)) if k == "news"]

    assert news == ["26/10 13:00", "02/11 13:00", "09/11 13:00"]


def test_rescheduled_kickoff_does_not_resend_the_pre_game() -> None:
    # 18/11 had no time: the pre-game went out early. ESPN then confirms 20:00 (pre-game 16:00).
    confirmed = fixture(datetime(2026, 11, 18, 23, 0, tzinfo=UTC), "athletico")
    sent_at = at("18/11/2026", "08:04")

    slots = plan([confirmed], at("18/11/2026", "14:05"), sent_at, "Pré-jogo — 18/11/2026")

    assert due(slots, at("18/11/2026", "14:05")) is None
    assert slots[0].kind == "post" and slots[0].window_start == sent_at - timedelta(hours=2)


def test_back_to_back_days_keep_the_post_game_and_drop_the_next_pre_game() -> None:
    games = [fixture(at("24/10/2026", "18:30"), "a"), fixture(at("25/10/2026", "13:00"), "b")]

    slots = until_last_match(plan(games, at("23/10/2026"), at("23/10/2026")))

    assert summary(slots) == [
        ("pre", "24/10 14:30"),
        ("post", "25/10 13:00"),
        ("post", "26/10 13:00"),
    ]
    assert [s.match_id for s in slots] == ["a", "a", "b"]


def test_morning_kickoff_the_day_after_a_game_also_drops_its_pre_game() -> None:
    games = [fixture(at("24/10/2026", "18:30"), "a"), fixture(at("25/10/2026", "10:00"), "b")]

    slots = until_last_match(plan(games, at("23/10/2026"), at("23/10/2026")))

    assert [(s.kind, s.match_id) for s in slots] == [("pre", "a"), ("post", "a"), ("post", "b")]
    assert all(b.window_start < b.send_at for b in slots)


def test_label_of_reads_the_label_from_a_subject() -> None:
    assert (
        label_of("Novidades! Urubu News — Pré-jogo — 18/10/2026: Bahia") == "Pré-jogo — 18/10/2026"
    )
    assert label_of("Urubu News — Notícias — 21/10/2026") == "Notícias — 21/10/2026"
    assert label_of("Urubu News — Edição de Sexta — 16/10/2026: x") is None


def test_due_stage_build_window_is_not_send() -> None:
    slots = plan([fixture(at("18/10/2026", "20:00"))], NOW, LAST_SENT)

    slot, stage = due_stage(slots, at("19/10/2026", "10:00"))

    assert (slot.label, stage) == ("Pós-jogo — 19/10/2026", "build")
    assert due_stage(slots, at("19/10/2026", "12:59")) is None  # build is over, send not yet


def test_due_stage_send_after_13() -> None:
    slots = plan([fixture(at("18/10/2026", "20:00"))], NOW, LAST_SENT)

    assert due_stage(slots, at("19/10/2026", "07:59")) is None
    assert due_stage(slots, at("19/10/2026", "13:00"))[1] == "send"
    assert due_stage(slots, at("19/10/2026", "15:59"))[1] == "send"
    assert due_stage(slots, at("19/10/2026", "16:00")) is None


def test_due_stage_pre_game_send_wins_over_its_build_window() -> None:
    # build 14:00 (until 17:00), send 16:00: at 16:30 both are inside their windows
    slots = plan([fixture(at("18/10/2026", "20:00"))], NOW, LAST_SENT)

    assert due_stage(slots, at("18/10/2026", "14:10"))[1] == "build"
    assert due_stage(slots, at("18/10/2026", "16:30"))[1] == "send"


def test_a_later_build_does_not_hide_a_send_that_did_not_go_out() -> None:
    # Post-game of yesterday's game at 13:00 (it failed); today's 19:30 game builds at 13:30.
    games = [fixture(at("17/10/2026", "20:00"), "a"), fixture(at("18/10/2026", "19:30"), "b")]
    slots = plan(games, at("17/10/2026", "12:00"), at("17/10/2026", "12:00"))

    due_now = due_stages(slots, at("18/10/2026", "13:40"))

    assert [(s.kind, s.match_id, stage) for s, stage in due_now] == [
        ("post", "a", "send"),
        ("pre", "b", "build"),
    ]
    slot, stage = due_stage(slots, at("18/10/2026", "13:40"))
    assert (slot.kind, stage) == ("post", "send")  # the backup retries the send first


MON_THU = (0, 3)


def test_specials_get_monday_and_thursday_in_the_offseason() -> None:
    news = summary(plan([], NOW, LAST_SENT, weekdays=MON_THU))

    assert news[:4] == [
        ("news", "22/10 13:00"),
        ("news", "26/10 13:00"),
        ("news", "29/10 13:00"),
        ("news", "02/11 13:00"),
    ]


def test_thursday_respects_the_72h_gap() -> None:
    # a game on Sunday 18/10: post-game Monday 19/10 13:00; Thursday 22/10 13:00 is exactly 72 h
    games = [fixture(at("18/10/2026", "16:00"))]

    news = [d for k, d in summary(plan(games, NOW, LAST_SENT, weekdays=MON_THU)) if k == "news"]

    assert news[:2] == ["22/10 13:00", "26/10 13:00"]
    late = [fixture(at("20/10/2026", "20:00"))]  # post-game Wednesday 21/10: no Thursday 22/10
    news = [d for k, d in summary(plan(late, NOW, LAST_SENT, weekdays=MON_THU)) if k == "news"]
    assert "22/10 13:00" not in news and "26/10 13:00" in news


def test_teams_without_specials_keep_mondays_only() -> None:
    assert summary(plan([], NOW, LAST_SENT)) == summary(plan([], NOW, LAST_SENT, weekdays=(0,)))
