"""The share link of a finished career: everything needed to replay it, nothing stored.

The code also carries the card's summary, so a link made before the data changed still shows
the card that was shared (the career itself would come out different with the new data).
"""

import base64
import binascii
import json
import zlib

from pydantic import BaseModel, ValidationError

from geral.games.carreira.motor import Carreira, Entrada

LIMITE = 2000  # characters
MAX_JSON = 8192  # bytes once decompressed: a real career is ~1.5 KB


class CodigoInvalido(ValueError):
    pass


class Resumo(BaseModel):
    nome: str
    posicao: str
    rotulo: str
    nota: int
    titulos: int
    clubes: list[str]


class Compartilhado(BaseModel):
    versao: str
    edicao: str
    entrada: Entrada
    resumo: Resumo


def resumir(entrada: Entrada, carreira: Carreira) -> Resumo:
    final = carreira.final
    if final is None:
        raise ValueError("only a finished career has a card")
    return Resumo(
        nome=entrada.craque.nome,
        posicao=entrada.craque.posicao,
        rotulo=final.rotulo,
        nota=final.nota,
        titulos=sum(final.titulos.values()),
        clubes=final.clubes,
    )


def codificar(versao: str, edicao: str, entrada: Entrada, resumo: Resumo) -> str:
    dados = Compartilhado(versao=versao, edicao=edicao, entrada=entrada, resumo=resumo)
    bruto = zlib.compress(dados.model_dump_json().encode(), level=9)
    return base64.urlsafe_b64encode(bruto).decode().rstrip("=")


def decodificar(codigo: str) -> Compartilhado:
    if not codigo or len(codigo) > LIMITE:
        raise CodigoInvalido("código vazio ou grande demais")
    try:
        bruto = base64.urlsafe_b64decode(codigo + "=" * (-len(codigo) % 4))
        descompressor = zlib.decompressobj()
        texto = descompressor.decompress(bruto, MAX_JSON)
        if descompressor.unconsumed_tail:
            raise CodigoInvalido("código grande demais")
        return Compartilhado.model_validate(json.loads(texto))
    except (binascii.Error, ValueError, zlib.error, ValidationError, RecursionError) as erro:
        raise CodigoInvalido("código de carreira inválido") from erro
