"""The career engine: one seed, the draft and the answers so far give the same career, always.

The seed's random stream is consumed in chronological order only, so a new answer never
changes a season that came before it: the career grows in front of the fan, it never shifts.
"""

import random
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from geral.games.carreira import final
from geral.games.carreira.dados import (
    COM_CLUBE,
    Clube,
    Condicao,
    Dados,
    Decisao,
    Efeito,
    Evento,
    OpcaoRotina,
)
from geral.games.carreira.draft import JogadaInvalida, Roubo, montar, oferta
from geral.games.carreira.regras import NOMES, POSICOES, geral

PRIMEIRO_ANO = 2027
IDADE_INICIAL, IDADE_MAXIMA = 16, 42
MAX_ESCOLHAS = 4  # decision questions per career (both modes)
MAX_RESPOSTAS = 60  # every answer of a Completa career: a day-to-day one per season, the market
CHANCE_ESCOLHA = 0.4  # per season, when one fits
COPA_DO_NORDESTE = "Copa do Nordeste"
SALTO = 18  # the biggest jump in level of a move up
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
    escolhas: list[int] = Field(default=[], max_length=MAX_RESPOSTAS)
    modo: Literal["rapida", "completa"] = "rapida"


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
    chegada: str | None = None  # "Chegou do Vasco": every change of club says so
    rotina: "ResultadoRotina | None" = None  # the day-to-day choice before this season


class ResultadoRotina(BaseModel):
    situacao: str
    escolha: str
    deu_certo: bool
    efeito: str  # "+3 finalização", "" when nothing changed


class InfoOpcao(BaseModel):
    chance: int | None = None  # % of it going well; None when there is no risk
    efeitos: str = ""  # "certo: +3 finalização · errado: lesão leve"


class Escolha(BaseModel):
    id: str
    tipo: Literal["dia", "mercado", "decisao"] = "decisao"
    pergunta: str
    opcoes: list[str]
    info: list[InfoOpcao] = []  # chance and effects of each option (day-to-day ones)
    destinos: list[str]  # the kind of each option (ficar, europa, aposentar…)
    clubes: list[str | None]  # the club each option moves to, None when it stays put


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


def chance_de(opcao: OpcaoRotina, notas: dict[str, int]) -> int:
    """The % shown to the fan and rolled by the engine: one source for both."""
    if opcao.chance >= 100:
        return 100
    bonus = (notas[opcao.bonus] - 70) // 2 if opcao.bonus else 0
    return max(5, min(95, opcao.chance + bonus))


def descrever(efeito: Efeito) -> str:
    partes = [
        f"{'+' if d > 0 else '−'}{abs(d)} {NOMES[a].lower()}" for a, d in efeito.atributos.items()
    ]
    if efeito.nota:
        partes.append(f"{'+' if efeito.nota > 0 else '−'}{abs(efeito.nota)} de forma")
    if efeito.jogos < 1:
        partes.append("lesão: perde parte da temporada" if efeito.jogos <= 0.7 else "lesão leve")
    if efeito.saida > 0:
        partes.append("mais chance de proposta")
    elif efeito.saida < 0:
        partes.append("mais chance de ficar")
    if efeito.selecao:
        partes.append("olho da Seleção")
    return ", ".join(partes)


def _info(opcao: OpcaoRotina, notas: dict[str, int]) -> InfoOpcao:
    chance = chance_de(opcao, notas)
    certo, errado = descrever(opcao.sucesso), descrever(opcao.fracasso)
    if chance >= 100:
        return InfoOpcao(chance=None, efeitos=certo or "nada muda")
    return InfoOpcao(
        chance=chance, efeitos=f"certo: {certo or 'nada muda'} · errado: {errado or 'nada muda'}"
    )


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
    ofertadas = oferta(dados, edicao, entrada.semente_draft, entrada.craque.clube)
    notas = montar(ofertadas, entrada.roubos)
    inicio = clube_inicial(dados, edicao, entrada.craque.clube)
    return _Simulacao(dados, entrada, notas, inicio).rodar()


def artigos(campo: str, clube: Clube | None) -> dict[str, str]:
    """`{campo}` plus its articled forms for the texts: {o_clube}, {do_clube}, {no_clube}…"""
    nome = clube.nome if clube else ""
    f = clube is not None and clube.genero == "f"
    formas = {
        "o": "a" if f else "o",
        "O": "A" if f else "O",
        "do": "da" if f else "do",
        "no": "na" if f else "no",
        "pelo": "pela" if f else "pelo",
        "ao": "à" if f else "ao",
        "para_o": "para a" if f else "para o",
    }
    return {campo: nome} | {f"{k}_{campo}": f"{v} {nome}" for k, v in formas.items()}


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
    regiao: str = ""
    classico: bool = False
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
            and (not c.regioes or self.regiao in c.regioes)
            and (c.classico is None or c.classico == self.classico)
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
    chegada: str | None = None  # how he got to the current club, for the next season
    efeito: Efeito = Efeito()  # the day-to-day result, for the next season
    resultado: ResultadoRotina | None = None
    rotinas_vistas: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rng = random.Random(f"carreira:{self.entrada.semente}")
        self.posicao = self.entrada.craque.posicao
        base = geral(self.notas, self.posicao)
        self.teto = max(35, min(99, base + round(self.rng.gauss(0, 9))))
        self.nota = max(30, self.teto - 25)
        self.aposenta_aos = self.rng.randint(33, 38) + (2 if self.notas["fisico"] >= 85 else 0)
        self.idade, self.ano, self.clube = IDADE_INICIAL, PRIMEIRO_ANO, self.inicio
        self.completa = self.entrada.modo == "completa"
        self._pesos_estado: dict[str, int] = {}
        self._peso_nordeste = 1
        for clube in self.dados.clubes.values():
            if clube.estado:
                self._pesos_estado[clube.estado] = (
                    self._pesos_estado.get(clube.estado, 0) + clube.prestigio**2
                )
                if self.dados.regiao(clube) == "nordeste":
                    self._peso_nordeste += clube.prestigio**2

    # -- the loop --------------------------------------------------------------------------

    def rodar(self) -> Carreira:
        while True:
            if self.completa and self.idade > IDADE_INICIAL:
                pendente = self._dia_a_dia()
                if pendente:
                    return Carreira(temporadas=self.temporadas, pendente=pendente)
            temporada, saida = self._temporada()
            self.temporadas.append(temporada)
            if not self._encerra():
                pendente, decidiu = self._pergunta(temporada)
                if pendente:
                    return Carreira(temporadas=self.temporadas, pendente=pendente)
                if not (self.aposentou or decidiu):  # the fan's answer holds this winter
                    pendente = self._mercado(saida)
                    if pendente:
                        return Carreira(temporadas=self.temporadas, pendente=pendente)
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

    def _campos_classico(self) -> dict[str, str]:
        """{classico} and {rival} for the texts: the derby turns by year, without the dice."""
        todos = self.dados.classicos_de(self.clube)
        nome, rival = todos[self.ano % len(todos)] if todos else ("clássico", None)
        return {"classico": nome} | artigos("rival", rival)

    def _regionais(self, participacao: float) -> list[str]:
        """The state cup and, for a club of the Northeast, the Copa do Nordeste: a club's chance is
        its weight (prestige squared) among the clubs that play it."""
        estado = self.dados.estados.get(self.clube.estado or "")
        if estado is None:
            return []
        ganhos = []
        peso = self.clube.prestigio**2
        rivais = self._pesos_estado.get(estado.uf, peso)
        if self.rng.random() < min(0.75, 1.1 * peso / rivais) * participacao:
            ganhos.append(estado.campeonato)
        if estado.regiao == "nordeste":
            chance = min(0.3, 2.2 * peso / self._peso_nordeste) * participacao
            if self.rng.random() < chance:
                ganhos.append(COPA_DO_NORDESTE)
        return ganhos

    def _contexto(self) -> _Contexto:
        return _Contexto(
            idade=self.idade,
            nota=self.nota,
            forca=self.dados.ligas[self.clube.liga].forca,
            pais=self.dados.ligas[self.clube.liga].pais,
            posicao=self.posicao,
            historico=self.historico,
            no_clube_inicial=self.clube.id == self.inicio.id,
            regiao=self.dados.regiao(self.clube) or "",
            classico=bool(self.dados.classicos_de(self.clube)),
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
        efeito_jogos = min([e.efeito.jogos for e in antes] + [self.efeito.jogos])
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
            titulos += self._regionais(peso * min(1.0, jogos / 10))
            convocado = any(e.efeito.selecao for e in antes) or self.efeito.selecao
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
        campos = (
            artigos("clube", self.clube)
            | self._campos_classico()
            | {
                "nome": self.entrada.craque.nome,
                "camisa": self.entrada.craque.camisa,
                "liga": liga.pais,
                "campeonato": liga.campeonato,
                "gols": gols,
                "jogos": jogos,
                "idade": self.idade,
            }
        )
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
            chegada=self.chegada,
            rotina=self.resultado,
        )
        saida = sum(e.efeito.saida for e in eventos) + self.efeito.saida
        self.chegada, self.efeito, self.resultado = None, Efeito(), None
        return temporada, saida

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
            # a step up, not a leap: the ABC boy goes through Sport or Bahia before Europe
            "maior": lambda c: atual + 3 < self._nivel(c) <= min(nota + 4, atual + SALTO),
            "menor": lambda c: nota - 18 <= self._nivel(c) <= min(atual - 2, nota - 2),
            "emprestimo": lambda c: nota - 16 <= self._nivel(c) <= nota - 3,
            "lado": lambda c: abs(self._nivel(c) - atual) <= 6,
            "arabia": lambda c: c.liga == "ara" and self._nivel(c) <= nota + 8,
            "exotico": lambda c: (
                c.liga in EXOTICAS and c.liga != self.clube.liga and self._nivel(c) <= nota + 8
            ),
        }
        cabem = sorted((c for c in clubes if filtros[tipo](c)), key=lambda c: c.id)
        if tipo in ("menor", "lado", "emprestimo", "maior"):
            pais = self.dados.ligas[self.clube.liga].pais
            perto = [c for c in cabem if self.dados.ligas[c.liga].pais == pais]
            if perto and self.rng.random() < 0.65:  # most moves stay in the country
                cabem = perto
                regiao = self.dados.regiao(self.clube)
                vizinhos = [c for c in cabem if regiao and self.dados.regiao(c) == regiao]
                if vizinhos and self.rng.random() < 0.5:  # and in Brazil, half in the region
                    cabem = vizinhos
        return self.rng.choice(cabem) if cabem else None

    def _mudar(
        self, clube: Clube | None, emprestimo: bool = False, motivo: str | None = None
    ) -> None:
        if clube is None:
            return
        if motivo is None:
            de = artigos("c", self.clube)
            motivo = f"Emprestado {de['pelo_c']}" if emprestimo else f"Chegou {de['do_c']}"
        self.emprestado_de = (self.emprestado_de or self.clube) if emprestimo else None
        self.clube, self.chegada = clube, motivo

    def _mercado(self, saida: float) -> Escolha | None:
        """The winter's market. Rápida moves him by itself; Completa asks, save for the end of a
        loan and a release (both told in the next season's line)."""
        if self.emprestado_de:
            de = artigos("c", self.clube)["ao_c"]
            self._mudar(self.emprestado_de, motivo=f"Voltou do empréstimo {de}")
            return None
        diff = self.nota - self._nivel(self.clube)
        sorte = self.rng.random()
        if self.clube.id == self.inicio.id and self.idade <= 19:
            sorte = 1 - (1 - sorte) * 0.4  # the boy rarely leaves the club that raised him
        destino = None
        if self.idade >= 31 and sorte < 0.08 + saida / 2:
            destino = self._destino(self.rng.choice(("exotico", "casa", "menor")))
        elif diff >= 8 and sorte < 0.35 + saida:
            destino = self._destino("maior")
        elif diff <= -10 and sorte < (0.85 if diff <= -18 else 0.5) + saida:
            destino = self._destino("menor")
            if self.completa and diff <= -18 and destino:  # no room: released, no question
                saiu = artigos("c", self.clube)["pelo_c"]
                self._mudar(destino, motivo=f"Dispensado {saiu}")
                return None
        elif sorte < 0.08 + saida:
            destino = self._destino("lado")
        if destino is None:
            return None
        if not self.completa:
            self._mudar(destino)
            return None
        return self._proposta(destino)

    def _proposta(self, destino: Clube) -> Escolha | None:
        campos = artigos("clube", self.clube) | artigos("destino", destino)
        campos |= {"nome": self.entrada.craque.nome, "idade": self.idade}
        pais = self.dados.ligas[destino.liga].pais
        onde = "" if pais == self.dados.ligas[self.clube.liga].pais else f" ({pais})"
        escolha = Escolha(
            id="proposta",
            tipo="mercado",
            pergunta="{O_destino}{onde} faz uma proposta por {nome}.".format_map(
                campos | {"onde": onde}
            ),
            opcoes=[
                "Aceitar e ir {para_o_destino}".format_map(campos),
                "Ficar {no_clube}".format_map(campos),
            ],
            destinos=["maior", "ficar"],
            clubes=[destino.id, None],
        )
        resposta = self._resposta(len(escolha.opcoes))
        if resposta is None:
            return escolha
        if resposta == 0:
            self._mudar(destino)
        return None

    def _resposta(self, opcoes: int) -> int | None:
        """The fan's next answer, or None when the career waits for it."""
        if self.respondidas >= len(self.entrada.escolhas):
            return None
        resposta = self.entrada.escolhas[self.respondidas]
        self.respondidas += 1
        if not 0 <= resposta < opcoes:
            raise JogadaInvalida("essa opção não existe")
        return resposta

    def _dia_a_dia(self) -> Escolha | None:
        """Completa: the season's day-to-day situation; its result counts for this season."""
        ctx = self._contexto()
        if self.temporadas:
            ctx.gols, ctx.jogos = self.temporadas[-1].gols, self.temporadas[-1].jogos
        cabem = [r for r in self.dados.rotinas if ctx.casa(r.condicao)]
        novas = [r for r in cabem if r.id not in self.rotinas_vistas] or cabem
        if not novas:
            return None
        rotina = self.rng.choices(novas, weights=[r.peso for r in novas])[0]
        self.rotinas_vistas.append(rotina.id)
        campos = (
            artigos("clube", self.clube)
            | self._campos_classico()
            | {
                "nome": self.entrada.craque.nome,
                "idade": self.idade,
            }
        )
        texto = rotina.texto.format_map(campos)
        resposta = self._resposta(len(rotina.opcoes))
        if resposta is None:
            return Escolha(
                id=rotina.id,
                tipo="dia",
                pergunta=texto,
                opcoes=[o.texto.format_map(campos) for o in rotina.opcoes],
                info=[_info(o, self.notas) for o in rotina.opcoes],
                destinos=["ficar"] * len(rotina.opcoes),
                clubes=[None] * len(rotina.opcoes),
            )
        opcao = rotina.opcoes[resposta]
        deu_certo = self.rng.random() * 100 < chance_de(opcao, self.notas)
        efeito = opcao.sucesso if deu_certo else opcao.fracasso
        antes = geral(self.notas, self.posicao)
        for atributo, delta in efeito.atributos.items():
            self.notas[atributo] = max(1, min(99, self.notas[atributo] + delta))
        ganho = geral(self.notas, self.posicao) - antes + efeito.nota
        self.nota = max(20, min(99, self.nota + ganho))
        self.teto = max(35, min(99, self.teto + geral(self.notas, self.posicao) - antes))
        self.efeito = efeito
        self.resultado = ResultadoRotina(
            situacao=texto,
            escolha=opcao.texto.format_map(campos),
            deu_certo=deu_certo,
            efeito=descrever(efeito),
        )
        return None

    def _pergunta(self, temporada: Temporada) -> tuple[Escolha | None, bool]:
        """Maybe a question this season: (pending question, the fan settled this winter)."""
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
        resposta = self._resposta(len(decisao.opcoes))
        if resposta is None:
            return self._escolha(decisao, destinos), False
        destino = decisao.opcoes[resposta].destino
        if destino == "aposentar":
            self.aposentou = True
        elif destino == "mais_um":
            self.aposenta_aos = min(IDADE_MAXIMA, max(self.aposenta_aos, self.idade + 2))
        elif destino in destinos:
            self._mudar(destinos[destino], emprestimo=destino == "emprestimo")
        return None, True

    def _escolha(self, decisao: Decisao, destinos: dict[str, Clube | None]) -> Escolha:
        alvos = [c for c in destinos.values() if c]
        clubes = [destinos.get(o.destino) for o in decisao.opcoes]
        pais = lambda c: self.dados.ligas[c.liga].pais if c else ""  # noqa: E731
        campos = artigos("clube", self.clube) | {
            "nome": self.entrada.craque.nome,
            "idade": self.idade,
        }
        # {destino} in the question is the first club on offer, {outro} the second; in an option,
        # {destino} is that option's own club.
        primeiro = alvos[0] if alvos else None
        segundo = alvos[1] if len(alvos) > 1 else None
        geral_ = campos | artigos("destino", primeiro) | artigos("outro", segundo)
        geral_ |= {"pais_destino": pais(primeiro), "pais_outro": pais(segundo)}

        def opcao(texto: str, clube: Clube | None) -> str:
            proprio = clube or primeiro
            return texto.format_map(
                campos | artigos("destino", proprio) | {"pais_destino": pais(proprio)}
            )

        return Escolha(
            id=decisao.id,
            pergunta=decisao.pergunta.format_map(geral_),
            opcoes=[opcao(o.texto, c) for o, c in zip(decisao.opcoes, clubes, strict=True)],
            destinos=[o.destino for o in decisao.opcoes],
            clubes=[c.id if c else None for c in clubes],
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


Temporada.model_rebuild()
