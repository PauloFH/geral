import json
import random

from velha_fakes import synthetic

from geral.games import calendario
from geral.games.velha.board import make_board
from geral.games.velha.diario import LAUNCH, daily_board, puzzle_number
from geral.games.velha.importacao import keep_countries

BASE = synthetic()


def test_daily_board_without_freeze_is_the_seeded_one() -> None:
    assert daily_board(BASE, 3, []) == make_board(BASE, random.Random("velha:3"))
    assert daily_board(BASE, 3, []) != daily_board(BASE, 4, [])


def test_daily_board_follows_the_frozen_calendar() -> None:
    frozen = [daily_board(BASE, n, []).code for n in (1, 2, 3)]
    other = synthetic(seed=8)  # the base changed (a new import)

    assert daily_board(other, 3, frozen).code == frozen[2]
    assert daily_board(other, 4, frozen) == make_board(other, random.Random("velha:4"))


def test_frozen_board_with_a_vanished_category_falls_back_to_the_seeded_one() -> None:
    frozen = ["clube:Q999|selecao:BRA|copa:FIFA|clube:Q100|clube:Q101|clube:Q102"]
    assert daily_board(BASE, 1, frozen) == make_board(BASE, random.Random("velha:1"))


def test_puzzle_number_starts_at_one_on_launch() -> None:
    assert puzzle_number(LAUNCH) == 1


def test_freeze_velha_keeps_numbers_already_frozen(tmp_path) -> None:
    path = tmp_path / "calendario.json"
    path.write_text(json.dumps({"velha": {"geral": ["frozen-one"]}}))

    calendario.freeze_velha(path, BASE, 3)

    codes = calendario.answers(calendario.load(path), "velha", "geral")
    assert codes[0] == "frozen-one"
    assert codes[1:] == [daily_board(BASE, n, []).code for n in (2, 3)]


def test_import_keeps_the_countries_of_the_previous_base() -> None:
    old = {"paises": {"Q77": "Uruguai", "Q414": "Argentina"}, "jogadores": []}
    new = {"paises": {"Q77": "Uruguay", "Q739": "Colômbia"}, "jogadores": [{"id": "Q1"}]}

    kept = keep_countries(old, new)

    assert kept["paises"] == {"Q77": "Uruguay", "Q414": "Argentina", "Q739": "Colômbia"}
    assert kept["jogadores"] == [{"id": "Q1"}]
