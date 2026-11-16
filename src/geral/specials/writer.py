"""A story written by the model from one passage only (the verifier checks it afterwards)."""

from pydantic import BaseModel

from geral.specials.sources import Kind, Passage
from geral.summarizer.client import LLMClient
from geral.summarizer.pipeline import render_prompt
from geral.teams import Team


class StoryResponse(BaseModel):
    title: str
    body: str
    summary: str
    fact_date: str = ""


class StoryDraft(StoryResponse):
    kind: Kind
    source_key: str
    source_url: str
    source_title: str


def write_story(passage: Passage, team: Team, llm: LLMClient) -> StoryDraft:
    prompt = render_prompt(
        "story", team=team, kind=passage.kind, source_title=passage.title, text=passage.text
    )
    answer = llm.generate_json(prompt, StoryResponse)
    return StoryDraft(
        **answer.model_dump(),
        kind=passage.kind,
        source_key=passage.key,
        source_url=passage.url,
        source_title=passage.title,
    )
