"""Attributes, positions and how much each attribute weighs in a position's overall rating."""

ATRIBUTOS = (
    "velocidade",
    "finalizacao",
    "passe",
    "drible",
    "marcacao",
    "fisico",
    "cabeceio",
    "lideranca",
)
POSICOES = ("zagueiro", "lateral", "volante", "meia", "atacante")

# Order of ATRIBUTOS; each row sums to 100 (read as percent).
_TABELA = {
    "zagueiro": (8, 2, 8, 2, 30, 20, 20, 10),
    "lateral": (22, 4, 16, 14, 20, 14, 4, 6),
    "volante": (8, 4, 22, 8, 26, 18, 6, 8),
    "meia": (10, 14, 30, 24, 4, 6, 2, 10),
    "atacante": (18, 34, 8, 18, 1, 8, 10, 3),
}
PESOS: dict[str, dict[str, float]] = {
    posicao: {a: p / 100 for a, p in zip(ATRIBUTOS, linha, strict=True)}
    for posicao, linha in _TABELA.items()
}


def geral(notas: dict[str, int], posicao: str) -> int:
    """The overall rating (1-99) of these attribute ratings playing in `posicao`."""
    total = sum(notas[a] * peso for a, peso in PESOS[posicao].items())
    return max(1, min(99, round(total)))
