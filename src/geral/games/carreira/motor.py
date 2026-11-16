"""The career engine: one seed, the draft and the answers so far give the same career, always.

The seed's random stream is consumed in chronological order only, so a new answer never
changes a season that came before it: the career grows in front of the fan, it never shifts.
"""

import random
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from geral.games.carreira import final
from geral.games.carreira.dados import COM_CLUBE, Clube, Condicao, Dados, Decisao, Evento
from geral.games.carreira.draft import JogadaInvalida, Roubo, montar, oferta
from geral.games.carreira.regras import POSICOES, geral

PRIMEIRO_ANO = 2027
IDADE_INICIAL, IDADE_MAXIMA = 16, 42
MAX_ESCOLHAS = 4  # questions per career
CHANCE_ESCOLHA = 0.4  # per season, when one fits
EUROPA = 80  # league strength from which a league counts as the top of Europe
EXOTICAS = ("ara", "jap", "eua", "tur", "mex")
GOL = {"atacante": 0.5, "meia": 0.24, "volante": 0.07, "lateral": 0.06, "zagueiro": 0.05}
ASSIST = {"atacante": 0.16, "meia": 0.26, "volante": 0.09, "lateral": 0.13, "zagueiro": 0.03}


class Craque(BaseModel):
    nome: str = Field(min_length=1, max_length=24)
    camisa: int = Field(ge=1, le=99)
    posicao: Literal[POSICOES]
    pe: Literal["direito", "esquerdo", "ambos"]
    clube: str | None = Field(default=None, max_length=40)  # the 'geral' edition's start


class Entrada(BaseModel):
    semente_draft: str = Field(min_length=1, max_length=40)
    semente: str = Field(min_length=1, max_length=40)
    craque: Craque
    roubos: list[Roubo] = Field(max_length=9)
    escolhas: list[int] = Field(default=[], max_length=MAX_ESCOLHAS + 2)


class Temporada(BaseModel):
    ano: int
    idade: int
    clube: str
    clube_id: str
    pais: str
    liga_forca: int
    jogos: int
    gols: int
    assistencias: int
    nota: int
    titulos: list[str]
    selecao: int  # games for the national team
    copa: bool  # played a World Cup
    manchete: str
    eventos: list[str]


class Escolha(BaseModel):
    id: str
    pergunta: str
    opcoes: list[str]


class Final(BaseModel):
    nota: int  # 0-100
    rotulo: str
    descricao: str
    titulos: dict[str, int]
    clubes: list[str]  # in the order he played for them
    jogos: int
    gols: int
    selecao: int
    copa: bool
    parecido: str  # "your career recalls ___"
    perguntas: list[str]  # ids of the questions asked


class Carreira(BaseModel):
    temporadas: list[Temporada]
    pendente: Escolha | None = None
    final: Final | None = None


def clube_inicial(dados: Dados, edicao: str, escolhido: str | None) -> Clube:
    """A team edition starts in the team's youth; 'geral' in the Brazilian club the fan chose."""
    if edicao != "geral":
        for clube in dados.clubes.values():
            if clube.time == edicao:
                return clube
        raise JogadaInvalida("essa edição não tem clube de partida")
    clube = dados.clubes.get(escolhido or "")
    if clube is None or dados.ligas[clube.liga].pais != "Brasil":
        raise JogadaInvalida("escolha um clube brasileiro para começar")
    return clube


def simular(dados: Dados, edicao: str, entrada: Entrada) -> Carreira:
    notas = montar(oferta(dados, edicao, entrada.semente_draft), entrada.roubos)
    inicio = clube_inicial(dados, edicao, entrada.craque.clube)
    return _Simulacao(dados, entrada, notas, inicio).rodar()


def _fase(idade: int) -> str:
    return "inicio" if idade < 21 else "auge" if idade <= 30 else "fim"


@dataclass
class _Contexto:
    """What conditions look at: the player now and, after the numbers, this season."""

    idade: int
    nota: int
    forca: int
    posicao: str
    historico: set[str]
    no_clube_inicial: bool
    pais: str = ""
    gols: int = 0
    jogos: int = 0
    titulo: bool = False
    selecao: bool = False
    copa: bool = False
    mundial: bool = False

    def casa(self, c: Condicao) -> bool:
        return (
            c.idade_min <= self.idade <= c.idade_max
            and c.nota_min <= self.nota <= c.nota_max
            and c.forca_min <= self.forca <= c.forca_max
            and (not c.posicoes or self.posicao in c.posicoes)
            and (not c.fases or _fase(self.idade) in c.fases)
            and all(r in self.historico for r in c.requer)
            and not any(x in self.historico for x in c.exclui)
            and c.gols_min <= self.gols <= c.gols_max
            and c.jogos_min <= self.jogos <= c.jogos_max
            and (c.titulo is None or c.titulo == self.titulo)
            and (c.no_clube_inicial is None or c.no_clube_inicial == self.no_clube_inicial)
            and (c.selecao is None or c.selecao == self.selecao)
            and (c.copa is None or c.copa == self.copa)
            and (c.mundial is None or c.mundial == self.mundial)
            and (not c.paises or self.pais in c.paises)
        )


@dataclass
class _Simulacao:
    dados: Dados
    entrada: Entrada
    notas: dict[str, int]
    inicio: Clube
    temporadas: list[Temporada] = field(default_factory=list)
    historico: set[str] = field(default_factory=set)
    perguntadas: list[str] = field(default_factory=list)
    respondidas: int = 0
    emprestado_de: Clube | None = None
    aposentou: bool = False

    def __post_init__(self) -> None:
        self.rng = random.Random(f"carreira:{self.entrada.semente}")
        self.posicao = self.entrada.craque.posicao
        base = geral(self.notas, self.posicao)
        self.teto = max(35, min(99, base + round(self.rng.gauss(0, 9))))
        self.nota = max(30, self.teto - 25)
        self.aposenta_aos = self.rng.randint(33, 38) + (2 if self.notas["fisico"] >= 85 else 0)
        self.idade, self.ano, self.clube = IDADE_INICIAL, PRIMEIRO_ANO, self.inicio

    # -- the loop --------------------------------------------------------------------------

    def rodar(self) -> Carreira:
        while True:
            temporada, saida = self._temporada()
            self.temporadas.append(temporada)
            if not self._encerra():
                pendente, ficou = self._pergunta(temporada)
                if pendente:
                    return Carreira(temporadas=self.temporadas, pendente=pendente)
                if not (self.aposentou or ficou):
                    self._mercado(saida)
            if self.aposentou or self._encerra():
                break
            self.idade, self.ano = self.idade + 1, self.ano + 1
            self._evoluir()
        if self.respondidas < len(self.entrada.escolhas):
            raise JogadaInvalida("a carreira já terminou: escolhas demais")
        return Carreira(temporadas=self.temporadas, final=self._final())

    def _encerra(self) -> bool:
        return (
            self.idade >= IDADE_MAXIMA
            or self.idade >= self.aposenta_aos
            or (self.idade >= 30 and self.nota < 40)
        )

    def _evoluir(self) -> None:
        if self.idade <= 26:
            self.nota += min(max(0, self.teto - self.nota), self.rng.randint(2, 6))
        elif self.idade <= 30:
            self.nota += self.rng.choice((-1, 0, 0, 1))
        else:
            self.nota -= self.rng.randint(1, 3) + (2 if self.idade >= 34 else 0)
        self.nota = max(20, min(99, self.nota))

    # -- one season ------------------------------------------------------------------------

    def _nivel(self, clube: Clube) -> float:
        return (self.dados.ligas[clube.liga].forca + clube.prestigio) / 2

    def _contexto(self) -> _Contexto:
        return _Contexto(
            idade=self.idade,
            nota=self.nota,
            forca=self.dados.ligas[self.clube.liga].forca,
            pais=self.dados.ligas[self.clube.liga].pais,
            posicao=self.posicao,
            historico=self.historico,
            no_clube_inicial=self.clube.id == self.inicio.id,
        )

    def _sortear_eventos(self, momento: str, ctx: _Contexto) -> list[Evento]:
        cabem = [
            e
            for e in self.dados.eventos
            if e.momento == momento
            and not (e.unico and e.id in self.historico)
            and ctx.casa(e.condicao)
        ]
        if not cabem:
            return []
        if momento == "antes":
            if self.rng.random() >= 0.35:
                return []
            return [self.rng.choices(cabem, weights=[e.peso for e in cabem])[0]]
        primeiro = self.rng.choices(cabem, weights=[e.peso for e in cabem])[0]
        outros = [e for e in cabem if e is not primeiro and e.id != "temporada-comum"]
        if outros and self.rng.random() < 0.3:
            return [primeiro, self.rng.choices(outros, weights=[e.peso for e in outros])[0]]
        return [primeiro]

    def _temporada(self) -> tuple[Temporada, float]:
        liga = self.dados.ligas[self.clube.liga]
        nivel = self._nivel(self.clube)
        antes = self._sortear_eventos("antes", self._contexto())
        efeito_jogos = min([e.efeito.jogos for e in antes], default=1.0)
        jogos = gols = assist = selecao = 0
        titulos: list[str] = []
        copa = False
        if self.idade > IDADE_INICIAL:
            parte = max(0.03, min(1.0, 0.5 + (self.nota - nivel) / 25)) * efeito_jogos
            jogos = round(self.rng.randint(36, 52) * parte)
            forma = 0.7 + 0.6 * max(0.0, min(1.0, (self.nota - nivel + 20) / 40))
            taxa_gol = GOL[self.posicao] * (self.notas["finalizacao"] / 75) ** 1.6 * forma
            taxa_assist = ASSIST[self.posicao] * (self.notas["passe"] / 75) ** 1.4 * forma
            gols = sum(self.rng.random() < taxa_gol for _ in range(jogos))
            assist = sum(self.rng.random() < taxa_assist for _ in range(jogos))
            peso = 0.6 + 0.4 * min(1.0, parte * 1.5)
            chance = max(
                0.01, min(0.55, (self.clube.prestigio - 55) / 90 + (self.nota - nivel) / 250)
            )
            chance *= peso * min(1.0, jogos / 15)  # a title needs the player on the pitch
            if self.rng.random() < chance:
                titulos.append(liga.campeonato)
            if liga.copa and self.rng.random() < chance * 0.6:
                titulos.append(liga.copa)
            if (
                liga.continental
                and self.clube.prestigio >= 68
                and self.rng.random() < chance * 0.35
            ):
                titulos.append(liga.continental)
            convocado = any(e.efeito.selecao for e in antes)
            if 18 <= self.idade <= 35 and self.nota >= 78 and parte > 0.4:
                convocado = convocado or self.rng.random() < min(0.95, (self.nota - 76) / 14)
            if convocado:
                selecao = self.rng.randint(3, 10)
                if self.ano % 4 == 2 and self.nota >= 82 and self.rng.random() < 0.7:
                    copa, selecao = True, selecao + self.rng.randint(2, 7)
                    if self.rng.random() < 0.12:
                        titulos.append("Copa do Mundo")
        ctx = self._contexto()
        ctx.gols, ctx.jogos, ctx.titulo, ctx.selecao = gols, jogos, bool(titulos), selecao > 0
        ctx.copa, ctx.mundial = copa, "Copa do Mundo" in titulos
        depois = self._sortear_eventos("depois", ctx)
        eventos = antes + depois
        for e in eventos:
            self.historico.add(e.id)
            self.nota = max(20, min(99, self.nota + e.efeito.nota))
            if e.efeito.titulo:
                titulos.append(e.efeito.titulo)
        principal = (depois or antes)[0] if eventos else None
        campos = {
            "nome": self.entrada.craque.nome,
            "camisa": self.entrada.craque.camisa,
            "clube": self.clube.nome,
            "liga": liga.pais,
            "campeonato": liga.campeonato,
            "gols": gols,
            "jogos": jogos,
            "idade": self.idade,
        }
        manchete = self.rng.choice(principal.manchetes).format_map(campos) if principal else ""
        temporada = Temporada(
            ano=self.ano,
            idade=self.idade,
            clube=self.clube.nome,
            clube_id=self.clube.id,
            pais=liga.pais,
            liga_forca=liga.forca,
            jogos=jogos,
            gols=gols,
            assistencias=assist,
            nota=self.nota,
            titulos=titulos,
            selecao=selecao,
            copa=copa,
            manchete=manchete,
            eventos=[e.id for e in eventos],
        )
        return temporada, sum(e.efeito.saida for e in eventos)

    # -- between seasons -------------------------------------------------------------------

    def _destino(self, tipo: str) -> Clube | None:
        """A club for a move of this kind, or None when the world has no fit."""
        atual, nota = self._nivel(self.clube), self.nota
        clubes = [c for c in self.dados.clubes.values() if c.id != self.clube.id]
        forca = {c.id: self.dados.ligas[c.liga].forca for c in clubes}
        if tipo == "casa":
            return self.inicio if self.clube.id != self.inicio.id else None
        filtros = {
            "europa": lambda c: forca[c.id] >= EUROPA and nota - 14 <= self._nivel(c) <= nota + 4,
            "maior": lambda c: atual + 3 < self._nivel(c) <= nota + 4,
            "menor": lambda c: nota - 18 <= self._nivel(c) <= min(atual - 2, nota - 2),
            "emprestimo": lambda c: nota - 16 <= self._nivel(c) <= nota - 3,
            "lado": lambda c: abs(self._nivel(c) - atual) <= 6,
            "arabia": lambda c: c.liga == "ara" and self._nivel(c) <= nota + 8,
            "exotico": lambda c: c.liga in EXOTICAS and self._nivel(c) <= nota + 8,
        }
        cabem = sorted((c for c in clubes if filtros[tipo](c)), key=lambda c: c.id)
        if tipo in ("menor", "lado", "emprestimo"):
            pais = self.dados.ligas[self.clube.liga].pais
            perto = [c for c in cabem if self.dados.ligas[c.liga].pais == pais]
            if perto and self.rng.random() < 0.65:  # moves down or sideways mostly stay home
                cabem = perto
        return self.rng.choice(cabem) if cabem else None

    def _mudar(self, clube: Clube | None, emprestimo: bool = False) -> None:
        if clube is None:
            return
        self.emprestado_de = self.clube if emprestimo else None
        self.clube = clube

    def _mercado(self, saida: float) -> None:
        if self.emprestado_de:
            self._mudar(self.emprestado_de)
            return
        diff = self.nota - self._nivel(self.clube)
        sorte = self.rng.random()
        if self.idade >= 31 and sorte < 0.08 + saida / 2:
            self._mudar(self._destino(self.rng.choice(("exotico", "casa", "menor"))))
        elif diff >= 8 and sorte < 0.35 + saida:
            self._mudar(self._destino("maior"))
        elif diff <= -10 and sorte < (0.85 if diff <= -18 else 0.5) + saida:
            self._mudar(self._destino("menor"))
        elif sorte < 0.08 + saida:
            self._mudar(self._destino("lado"))

    def _pergunta(self, temporada: Temporada) -> tuple[Escolha | None, bool]:
        """Maybe a question this season: (pending question, the player chose to stay)."""
        if len(self.perguntadas) >= MAX_ESCOLHAS or self.rng.random() >= CHANCE_ESCOLHA:
            return None, False
        ctx = self._contexto()
        ctx.gols, ctx.jogos = temporada.gols, temporada.jogos
        ctx.titulo, ctx.selecao = bool(temporada.titulos), temporada.selecao > 0
        ctx.copa, ctx.mundial = temporada.copa, "Copa do Mundo" in temporada.titulos
        cabem = [
            d for d in self.dados.decisoes if d.id not in self.perguntadas and ctx.casa(d.condicao)
        ]
        if not cabem:
            return None, False
        decisao = self.rng.choices(cabem, weights=[d.peso for d in cabem])[0]
        destinos = {
            o.destino: self._destino(o.destino) for o in decisao.opcoes if o.destino in COM_CLUBE
        }
        if any(clube is None for clube in destinos.values()):
            return None, False
        self.perguntadas.append(decisao.id)
        if self.respondidas >= len(self.entrada.escolhas):
            return self._escolha(decisao, destinos), False
        resposta = self.entrada.escolhas[self.respondidas]
        self.respondidas += 1
        if not 0 <= resposta < len(decisao.opcoes):
            raise JogadaInvalida("essa opção não existe")
        destino = decisao.opcoes[resposta].destino
        if destino == "aposentar":
            self.aposentou = True
        elif destino == "mais_um":
            self.aposenta_aos = min(IDADE_MAXIMA, max(self.aposenta_aos, self.idade + 2))
        elif destino in destinos:
            self._mudar(destinos[destino], emprestimo=destino == "emprestimo")
        return None, destino in ("ficar", "mais_um")

    def _escolha(self, decisao: Decisao, destinos: dict[str, Clube | None]) -> Escolha:
        alvo = next(iter(destinos.values()), None)
        campos = {
            "nome": self.entrada.craque.nome,
            "clube": self.clube.nome,
            "idade": self.idade,
            "destino": alvo.nome if alvo else "",
        }
        return Escolha(
            id=decisao.id,
            pergunta=decisao.pergunta.format_map(campos),
            opcoes=[o.texto.format_map(campos) for o in decisao.opcoes],
        )

    # -- the end ---------------------------------------------------------------------------

    def _final(self) -> Final:
        titulos: dict[str, int] = {}
        for t in self.temporadas:
            for nome in t.titulos:
                titulos[nome] = titulos.get(nome, 0) + 1
        rotulo, descricao = final.rotular(self.dados, self.temporadas)
        return Final(
            nota=final.nota(self.temporadas),
            rotulo=rotulo,
            descricao=descricao,
            titulos=titulos,
            clubes=list(dict.fromkeys(t.clube for t in self.temporadas)),
            jogos=sum(t.jogos for t in self.temporadas),
            gols=sum(t.gols for t in self.temporadas),
            selecao=sum(t.selecao for t in self.temporadas),
            copa=any(t.copa for t in self.temporadas),
            parecido=final.parecido(self.dados, final.base_real(), self.temporadas, self.posicao),
            perguntas=list(self.perguntadas),
        )
