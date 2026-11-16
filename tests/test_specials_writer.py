from fakes import FakeLLMClient

from geral.specials.sources import Passage
from geral.specials.writer import StoryDraft, write_story
from geral.teams import get_team

PASSAGE = Passage(
    kind="clube",
    key="https://pt.wikipedia.org/wiki/Clube_N%C3%A1utico_Capibaribe#Mascote",
    title="Clube Náutico Capibaribe — Mascote",
    url="https://pt.wikipedia.org/wiki/Clube_N%C3%A1utico_Capibaribe",
    text="A escolha do Timbu como mascote ocorreu em 19 de agosto de 1934.",
)


def answer(prompt, schema):
    return {
        "title": "Como o Náutico virou Timbu",
        "body": "Em 19 de agosto de 1934…",
        "summary": "A provocação que virou mascote.",
        "fact_date": "1934-08-19",
    }


def test_prompt_carries_only_the_passage_and_the_rules() -> None:
    llm = FakeLLMClient(answer)

    write_story(PASSAGE, get_team("nautico"), llm)

    [prompt] = llm.prompts
    assert PASSAGE.text in prompt
    assert "Use apenas" in prompt and "120 a 180 palavras" in prompt
    assert "Timbu News" in prompt


def test_story_draft_keeps_the_passage_kind_and_source() -> None:
    story = write_story(PASSAGE, get_team("nautico"), FakeLLMClient(answer))

    assert isinstance(story, StoryDraft)
    assert (story.kind, story.source_key, story.source_url) == (
        "clube",
        PASSAGE.key,
        PASSAGE.url,
    )
    assert story.source_title == "Clube Náutico Capibaribe — Mascote"
    assert story.fact_date == "1934-08-19"


def test_prompt_forbids_talking_to_the_reader() -> None:
    llm = FakeLLMClient(answer)

    write_story(PASSAGE, get_team("nautico"), llm)

    assert "Não cite a newsletter" in llm.prompts[0]
