from velha_fakes import base, player

from geral.games.velha.busca import search

B = base(
    player("Q12897", "Pelé", fama=200, anos="1956–1977", completo="Edson Arantes do Nascimento"),
    player("Q1", "João Leite", fama=10),
    player("Q2", "Joãozinho", fama=30),
    player("Q3", "Leandro", fama=50),
    *(player(f"Q{100 + n}", f"Silva {n}", fama=n) for n in range(15)),
)


def names(q: str) -> list[str]:
    return [p.nome for p in search(B, q)]


def test_search_ignores_accents_and_case() -> None:
    assert names("joao") == ["Joãozinho", "João Leite"]
    assert names("PELE") == ["Pelé"]


def test_search_matches_word_starts_in_nome_or_completo() -> None:
    assert names("edson ara") == ["Pelé"]
    assert names("leite joao") == ["João Leite"]
    assert names("ele") == []  # inside a word, not at its start
    assert names("lea") == ["Leandro"]


def test_search_puts_the_famous_first_and_stops_at_ten() -> None:
    found = search(B, "silva")
    assert len(found) == 10
    assert [p.fama for p in found] == list(range(14, 4, -1))


def test_search_needs_two_letters() -> None:
    assert search(B, "j") == []
    assert search(B, "  ") == []
