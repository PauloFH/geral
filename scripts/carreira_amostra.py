"""Print sample careers as text, to read the game's variety by eye.

    uv run python scripts/carreira_amostra.py 20 [--edicao geral] [--posicao atacante]

Each career gets a random draft order, starting club (in 'geral') and answers.
"""

import argparse
import random

from geral.games.carreira import regras
from geral.games.carreira.dados import carregar
from geral.games.carreira.draft import Roubo, oferta
from geral.games.carreira.motor import Craque, Entrada, simular


def carreira(dados, edicao: str, posicao: str | None, n: int, clube: str | None = None) -> str:
    rng = random.Random(f"amostra:{n}")
    posicao = posicao or rng.choice(regras.POSICOES)
    inicio = clube or rng.choice(
        sorted(c.id for c in dados.clubes.values() if dados.ligas[c.liga].pais == "Brasil")
    )
    lendas = oferta(dados, edicao, f"a{n}", inicio)[:8]
    atributos = list(regras.ATRIBUTOS)
    rng.shuffle(atributos)
    entrada = Entrada(
        semente_draft=f"a{n}",
        semente=f"s{n}",
        craque=Craque(
            nome=f"Craque {n}",
            camisa=rng.randint(2, 99),
            posicao=posicao,
            pe="direito",
            clube=inicio,
        ),
        roubos=[Roubo(lenda=x.nome, atributo=a) for x, a in zip(lendas, atributos, strict=True)],
    )
    linhas = [f"== {entrada.craque.nome} ({posicao})"]
    linhas += [f"   roubou {r.atributo} de {r.lenda}" for r in entrada.roubos]
    while (resultado := simular(dados, edicao, entrada)).final is None:
        pergunta = resultado.pendente
        resposta = rng.randrange(len(pergunta.opcoes))
        linhas.append(f"   ? {pergunta.pergunta} -> {pergunta.opcoes[resposta]}")
        entrada = entrada.model_copy(update={"escolhas": [*entrada.escolhas, resposta]})
    for t in resultado.temporadas:
        taças = f" 🏆 {', '.join(t.titulos)}" if t.titulos else ""
        numeros = f"{t.idade} {t.clube:<22} {t.jogos:>2}j {t.gols:>2}g nota {t.nota}"
        linhas.append(f"   {numeros}{taças} | {t.manchete}")
    f = resultado.final
    linhas.append(f"   >> {f.rotulo} ({f.nota}) — {f.descricao} Lembra: {f.parecido}.")
    return "\n".join(linhas)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("n", type=int)
    parser.add_argument("--edicao", default="geral")
    parser.add_argument("--posicao", choices=regras.POSICOES)
    parser.add_argument("--clube")
    args = parser.parse_args()
    dados = carregar()
    for n in range(args.n):
        print(carreira(dados, args.edicao, args.posicao, n, args.clube), end="\n\n")


if __name__ == "__main__":
    main()
