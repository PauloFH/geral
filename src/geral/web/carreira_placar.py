"""Fábrica de craques: every finished Carreira counts for the club it started in.

One row per career in its own table of the site's SQLite (like the jogo da velha duels). The key
is a hash of the share code, so the same career sent again (a retry, a reopened page) counts once.
"""

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LENDA = 85  # a final score from here makes a legend
SCHEMA = """
CREATE TABLE IF NOT EXISTS carreira_placar (
    codigo_hash TEXT PRIMARY KEY,
    clube TEXT NOT NULL,
    nota INTEGER NOT NULL,
    lenda INTEGER NOT NULL,
    criada_em TEXT NOT NULL
);
"""
# Most careers first, then the better average, then the name: a stable order for ties.
RANKING = """
SELECT clube, COUNT(*) AS carreiras, ROUND(AVG(nota)) AS media, SUM(lenda) AS lendas
FROM carreira_placar GROUP BY clube ORDER BY carreiras DESC, media DESC, clube
"""


@dataclass(frozen=True)
class Linha:
    clube: str
    carreiras: int
    media: int
    lendas: int
    posicao: int


class PlacarStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executescript(SCHEMA)

    def registrar(self, codigo: str, clube: str, nota: int, agora: datetime) -> bool:
        """Count a finished career for its starting club; False when it was already counted."""
        chave = hashlib.sha256(codigo.encode()).hexdigest()
        with closing(sqlite3.connect(self.path)) as db, db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO carreira_placar VALUES (?, ?, ?, ?, ?)",
                (chave, clube, nota, int(nota >= LENDA), agora.isoformat()),
            )
            return cursor.rowcount == 1

    def _todas(self) -> list[Linha]:
        with closing(sqlite3.connect(self.path)) as db:
            linhas = db.execute(RANKING).fetchall()
        return [
            Linha(clube, carreiras, int(media), lendas, posicao)
            for posicao, (clube, carreiras, media, lendas) in enumerate(linhas, start=1)
        ]

    def ranking(self, limite: int) -> list[Linha]:
        return self._todas()[:limite]

    def posicao(self, clube: str) -> tuple[int, int | None]:
        """(careers, place) of a club; (0, None) before its first career."""
        for linha in self._todas():
            if linha.clube == clube:
                return linha.carreiras, linha.posicao
        return 0, None
