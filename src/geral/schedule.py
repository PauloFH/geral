"""When each edition goes out: pre-game, post-game and news slots from the match calendar.

Pure functions (no network): the ESPN client supplies the fixtures and the subscription page
supplies when the last edition was really sent. See docs/features/edicoes-por-jogo.md.
"""

import re
from datetime import date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

TZ = ZoneInfo("America/Sao_Paulo")
# Each edition is built first (a draft the owner reviews) and sent later.
BUILD_TIME = time(8, 0)
SEND_TIME = time(13, 0)  # news and post-game: the morning is the review window
PRE_GAME_LEAD = timedelta(hours=6)  # the pre-game is built 6 h before the kick-off...
REVIEW_TIME = timedelta(hours=2)  # ...and sent 2 h later
MORNING_REVIEW = timedelta(hours=5)  # news and post-game: BUILD_TIME to SEND_TIME
EARLY_KICKOFF = time(11, 0)  # before this, the pre-game goes out the night before
EARLY_BUILD = time(18, 0)
NIGHT_BEFORE = time(20, 0)
MIN_NEWS_GAP = timedelta(hours=72)
SEND_SLACK = timedelta(hours=3)  # a send runs a little after its time (due's grace)
NEWS_EVERY = timedelta(hours=84)
HORIZON = timedelta(days=14)  # a match further than this does not shape the news yet
WEEKLY_UNTIL = timedelta(days=28)
DEFAULT_WINDOW = timedelta(days=3)  # news window when nothing was ever sent

LABELS = {"pre": "Pré-jogo", "post": "Pós-jogo", "news": "Notícias"}

Kind = Literal["pre", "post", "news"]
Stage = Literal["build", "send"]


class Fixture(BaseModel):
    match_id: str
    league: str
    kickoff: datetime
    time_valid: bool
    state: Literal["pre", "in", "post", "postponed"]
    home: str
    away: str


class Slot(BaseModel):
    kind: Kind
    build_at: datetime
    send_at: datetime
    window_start: datetime
    match_id: str | None = None
    league: str | None = None
    label: str


def _at(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=TZ)


def _pre_game(match: Fixture) -> tuple[datetime, datetime]:
    """(build, send) of the pre-game."""
    kickoff = match.kickoff.astimezone(TZ)
    if match.time_valid and kickoff.time() < EARLY_KICKOFF:
        eve = kickoff.date() - timedelta(days=1)
        return _at(eve, EARLY_BUILD), _at(eve, NIGHT_BEFORE)
    morning = _at(kickoff.date(), BUILD_TIME)
    build = max(kickoff - PRE_GAME_LEAD, morning) if match.time_valid else morning
    return build, build + REVIEW_TIME


def _post_game(match: Fixture) -> datetime:
    return _at(match.kickoff.astimezone(TZ).date() + timedelta(days=1), SEND_TIME)


def _morning_build(send_at: datetime) -> datetime:
    """News and post-game: built at 08:00 of the day they go out."""
    return _at(send_at.astimezone(TZ).date(), BUILD_TIME)


def _nearest_send_time(moment: datetime) -> datetime:
    """SEND_TIME of the closest day; a tie goes to the later day."""
    moment = moment.astimezone(TZ)
    same_day = _at(moment.date(), SEND_TIME)
    before, after = (
        (same_day, same_day + timedelta(days=1))
        if moment >= same_day
        else (same_day - timedelta(days=1), same_day)
    )
    return before if moment - before < after - moment else after


def _news_between(start: datetime, end: datetime) -> list[datetime]:
    gap = end - start
    if gap <= MIN_NEWS_GAP:
        return []
    n = max(1, gap // NEWS_EVERY)
    return [_nearest_send_time(start + gap * i / (n + 1)) for i in range(1, n + 1)]


def _weekly(start: datetime, until: datetime, weekdays: tuple[int, ...]) -> list[datetime]:
    """SEND_TIME on each of `weekdays` (0 = Monday) from MIN_NEWS_GAP after `start` to `until`.

    A real send goes out a few minutes after SEND_TIME: Monday 13:02 to Thursday 13:00 still
    counts as the 72 h gap (SEND_SLACK).
    """
    first = start + MIN_NEWS_GAP - SEND_SLACK
    day = first.astimezone(TZ).date()
    found = []
    while (moment := _at(day, SEND_TIME)) <= until:
        if day.weekday() in weekdays and moment >= first:
            found.append(moment)
        day += timedelta(days=1)
    return found


_LABEL_PATTERN = re.compile(rf"(?:{'|'.join(LABELS.values())}) — \d{{2}}/\d{{2}}/\d{{4}}")


def label_of(subject: str) -> str | None:
    """The slot label inside an edition subject ("… — Pré-jogo — 18/10/2026: …")."""
    match = _LABEL_PATTERN.search(subject)
    return match.group(0) if match else None


def _label(kind: Kind, send_at: datetime) -> str:
    return f"{LABELS[kind]} — {send_at.astimezone(TZ):%d/%m/%Y}"


def plan(
    fixtures: list[Fixture],
    now: datetime,
    last_sent: datetime | None,
    sent_label: str | None = None,
    weekdays: tuple[int, ...] = (0,),
) -> list[Slot]:
    """Every slot after the last real send, in order; `window_start` is the previous build.

    `sent_label` is the last edition's label: a reschedule that moves that slot later
    does not make it due again. `weekdays`: the weekly news days when no match is near
    (0 = Monday; teams with special sections also get Thursday).
    """
    anchor = last_sent or now - DEFAULT_WINDOW
    match_slots: list[tuple[Kind, datetime, Fixture]] = []
    pre_builds: dict[str, datetime] = {}
    previous_post: datetime | None = None
    for match in sorted(fixtures, key=lambda f: f.kickoff):
        if match.state == "postponed":
            continue
        (pre_build, pre), post = _pre_game(match), _post_game(match)
        pre_builds[match.match_id] = pre_build
        # Games on consecutive days: the post-game (with the next match card) wins.
        if previous_post is None or pre > previous_post:
            match_slots.append(("pre", pre, match))
        match_slots.append(("post", post, match))
        previous_post = post
    match_slots.sort(key=lambda slot: slot[1])

    timeline: list[tuple[Kind, datetime, Fixture | None]] = []
    previous = anchor
    for kind, send_at, match in match_slots:
        if send_at <= anchor or _label(kind, send_at) == sent_label:
            previous = max(previous, min(send_at, anchor))
            continue
        if kind == "pre":
            if send_at - previous <= HORIZON:
                news = _news_between(previous, send_at)
            else:
                news = _weekly(previous, min(send_at - MIN_NEWS_GAP, now + WEEKLY_UNTIL), weekdays)
            timeline += [("news", day, None) for day in news]
        timeline.append((kind, send_at, match))
        previous = send_at
    # After the last known match: weekly news.
    timeline += [("news", day, None) for day in _weekly(previous, now + WEEKLY_UNTIL, weekdays)]

    slots: list[Slot] = []
    # Each draft collects news up to its build: the next window starts there, not at the send.
    start = built_before(last_sent, sent_label) if last_sent else anchor
    for kind, send_at, match in timeline:
        build_at = pre_builds[match.match_id] if kind == "pre" and match else None
        slots.append(
            Slot(
                kind=kind,
                build_at=build_at or _morning_build(send_at),
                send_at=send_at,
                window_start=start,
                match_id=match.match_id if match else None,
                league=match.league if match else None,
                label=_label(kind, send_at),
            )
        )
        start = slots[-1].build_at
    return slots


def built_before(sent: datetime, label: str | None) -> datetime:
    """When the edition sent at `sent` was built: 2 h before for a pre-game, 5 h otherwise."""
    if label and label.startswith(LABELS["pre"]):
        return sent - REVIEW_TIME
    return sent - MORNING_REVIEW


def due(slots: list[Slot], now: datetime, grace: timedelta = timedelta(hours=3)) -> Slot | None:
    """The latest slot whose send time passed less than `grace` ago."""
    ready = [s for s in slots if s.send_at <= now < s.send_at + grace]
    return max(ready, key=lambda s: s.send_at, default=None)


def due_stages(
    slots: list[Slot], now: datetime, grace: timedelta = timedelta(hours=3)
) -> list[tuple[Slot, Stage]]:
    """Every build and send whose time passed less than `grace` ago, in time order.

    All of them, not the latest only: a build must not hide a send that has not gone out yet.
    A build is left out once the same slot's send is due.
    """
    events = [(s.build_at, 0, s, "build") for s in slots] + [
        (s.send_at, 1, s, "send") for s in slots
    ]
    ready = sorted((e for e in events if e[0] <= now < e[0] + grace), key=lambda e: e[:2])
    # Once a slot's send is due its build is moot (a send without a draft builds it).
    sending = {slot.label for _, _, slot, stage in ready if stage == "send"}
    return [
        (slot, stage) for _, _, slot, stage in ready if stage == "send" or slot.label not in sending
    ]


def due_stage(
    slots: list[Slot], now: datetime, grace: timedelta = timedelta(hours=3)
) -> tuple[Slot, Stage] | None:
    """One stage to run now (the hourly backup): the oldest pending send, else the latest build."""
    ready = due_stages(slots, now, grace)
    sends = [r for r in ready if r[1] == "send"]
    if sends:
        return sends[0]
    return ready[-1] if ready else None
