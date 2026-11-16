"""The nightly job: keep each team's stories collection at about TARGET ready stories.

It runs when fewer than LOW are left, or every Sunday. Sources already seen (used or refused) are
skipped; kinds are interleaved so a round does not bring ten idols. Each story is written by the
model from its passage and checked by the verifier: a refusal is kept too, with the reason.
"""

import logging
import random
from datetime import date
from itertools import zip_longest

import httpx
from pydantic import BaseModel, Field

from geral.config import Settings
from geral.send import recipients
from geral.specials import sources
from geral.specials.sources import Passage
from geral.specials.verifier import NUMBER, unsupported
from geral.specials.writer import StoryDraft, write_story
from geral.summarizer.client import LLMClient, LLMError
from geral.teams import Team

logger = logging.getLogger(__name__)

TARGET = 10
LOW = 8
MAX_CALLS = 20  # model calls per team per round
MIN_WORDS, MAX_WORDS = 100, 200  # the prompt asks for 120 to 180
SUNDAY = 6


class TopUpReport(BaseModel):
    team: str
    accepted: int = 0
    rejected: int = 0
    skipped_reason: str | None = None
    problems: list[str] = Field(default_factory=list)
    stories: list[StoryDraft] = Field(default_factory=list)  # accepted ones (dry run preview)


def _interleaved(found: list[Passage], today: date) -> list[Passage]:
    rng = random.Random(today.isoformat())
    by_kind: dict[str, list[Passage]] = {}
    for p in found:
        by_kind.setdefault(p.kind, []).append(p)
    for group in by_kind.values():
        rng.shuffle(group)
    return [p for row in zip_longest(*by_kind.values()) for p in row if p is not None]


def refusal(story: StoryDraft, passage: Passage, team: Team) -> str | None:
    """Why the verifier refuses the story, or None."""
    allowed = [team.name, team.newsletter, team.fans, *team.club_terms]
    text = f"{story.title}\n{story.body}\n{story.summary}"
    missing = unsupported(text, f"{passage.title}\n{passage.text}", allowed)
    if missing:
        return "fora da fonte: " + ", ".join(missing)
    words = len(story.body.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        return f"tamanho: {words} palavras"
    return None


def top_up(
    team: Team, settings: Settings, llm: LLMClient, wiki: httpx.Client, today: date
) -> TopUpReport:
    report = TopUpReport(team=team.slug)
    keep = not settings.DRY_RUN
    try:
        if settings.SUBSCRIBERS_API_TOKEN or keep:
            unused = recipients.stories_count(settings, team.slug)
            seen = recipients.story_sources(settings, team.slug)
        else:  # a local dry run without the page: as if the collection were empty
            unused, seen = 0, set()
    except httpx.HTTPError as e:
        logger.error("Stories of %s: the page did not answer: %s", team.slug, e)
        report.skipped_reason = "portal fora do ar"
        return report
    if unused >= LOW and today.weekday() != SUNDAY:
        report.skipped_reason = f"acervo com {unused} histórias"
        return report
    need = TARGET - unused
    if need <= 0:
        report.skipped_reason = f"acervo com {unused} histórias"
        return report
    fresh = [p for p in sources.passages(wiki, team) if p.key not in seen]
    for calls, passage in enumerate(_interleaved(fresh, today)):
        if report.accepted >= need or calls >= MAX_CALLS:
            break
        try:
            story = write_story(passage, team, llm)
        except LLMError as e:
            report.problems.append(f"Gemini: {e}")
            break
        if story.fact_date and story.fact_date[:4] not in NUMBER.findall(passage.text):
            story = story.model_copy(update={"fact_date": ""})
        reason = refusal(story, passage, team)
        if keep:
            try:
                recipients.add_story(
                    settings, team.slug, story.model_dump() | {"rejected_reason": reason}
                )
            except httpx.HTTPError as e:
                report.problems.append(f"portal: {e}")
                break
        if reason:
            report.rejected += 1
            logger.info("Story refused (%s): %s", passage.title, reason)
        else:
            report.accepted += 1
            report.stories.append(story)
    return report
