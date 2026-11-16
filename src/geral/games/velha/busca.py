"""Find a player of the base by name, as the fan types it (no accents, any case, word starts)."""

from geral.games.onde_jogou import normalize
from geral.games.velha.base import Base, Player

MIN_LETTERS = 2


def _words(player: Player) -> list[str]:
    return normalize(f"{player.nome} {player.completo}").replace("-", " ").split()


def search(base: Base, q: str, limit: int = 10) -> list[Player]:
    """Players with a word starting with each word of `q`, the most famous first."""
    wanted = normalize(q).replace("-", " ").split()
    if len("".join(wanted)) < MIN_LETTERS:
        return []
    found = [
        p
        for p in base.players.values()
        if all(any(word.startswith(w) for word in _words(p)) for w in wanted)
    ]
    return sorted(found, key=lambda p: (-p.fama, p.nome, p.id))[:limit]
