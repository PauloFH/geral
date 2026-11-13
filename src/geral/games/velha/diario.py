"""The daily solo board: the same for everyone, frozen in the calendar once played."""

import random
from datetime import date

from geral.games.daily import number_on
from geral.games.velha.base import Base
from geral.games.velha.board import Board, make_board, parse_board

LAUNCH = date(2026, 11, 14)  # board #1: no later than the deploy, or two days share #1
GAME = "velha"  # its key in `calendario.json` (edition "geral" only)


def puzzle_number(day: date) -> int:
    return number_on(day, LAUNCH)


def daily_board(base: Base, number: int, frozen: list[str]) -> Board:
    """Board #number: the frozen one while its categories still exist, else the seeded draw."""
    if 1 <= number <= len(frozen):
        try:
            return parse_board(base, frozen[number - 1])
        except ValueError:
            pass  # a category left the base: better a new board than a broken page
    return make_board(base, random.Random(f"velha:{number}"))
