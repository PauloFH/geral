from geral.specials.verifier import unsupported

SOURCE = (
    "A escolha do Timbu como mascote ocorreu durante um jogo entre Náutico e América/PE, no campo "
    'da Jaqueira, em 19 de agosto de 1934. A torcida adversária gritava "Timbu! Timbu!" e o '
    "Náutico venceu por 3–1."
)


def test_verifier_accepts_names_and_dates_in_the_source() -> None:
    story = (
        "Em 19 de agosto de 1934, no campo da Jaqueira, o Náutico enfrentou o América. "
        "A provocação virou símbolo: o Timbu venceu por 3 a 1."
    )

    assert unsupported(story, SOURCE) == []


def test_verifier_rejects_a_year_not_in_the_source() -> None:
    story = "Em 1935, o Náutico venceu o América por 3 a 1."

    assert unsupported(story, SOURCE) == ["1935"]


def test_verifier_rejects_a_name_not_in_the_source() -> None:
    story = "No campo da Jaqueira, o artilheiro Bita decidiu contra o América."

    assert unsupported(story, SOURCE) == ["Bita"]


def test_verifier_ignores_case_and_accents() -> None:
    assert unsupported("O Nautico e o TIMBU, na jaqueira.", SOURCE) == []


def test_verifier_allows_the_team_names() -> None:
    story = "Para os alvirrubros da Timbu News, o Capibaribe lembra 1934."

    assert unsupported(story, SOURCE, allowed=["Timbu News", "Capibaribe"]) == []
    assert unsupported(story, SOURCE) == ["News", "Capibaribe"]
