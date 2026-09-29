"""Guardrail de entrada: deteccao deterministica de conteudo inseguro/fora de escopo.

Roda ANTES do roteamento. Se bloquear, o fluxo vai direto para o Escalation Agent.
Deteccao por regex/heuristica (deterministica) - nao depende do LLM, como
recomendado para acoes criticas de seguranca.
"""

import re
import unicodedata
from dataclasses import dataclass

# Padroes de conteudo que deve ser transbordado/bloqueado
_PADROES_INSEGUROS = [
    r"\b(senha|password|token|cvv|c[oó]digo de seguran[cç]a)\b",
    r"\b(cart[aã]o de cr[eé]dito de outra pessoa|dados de outro cliente)\b",
    r"\b(fraude|clonar|hackear|invadir|golpe)\b",
    r"\b(matar|suic[ií]dio|amea[cç]a|bomba)\b",
]

_REGEX_INSEGURO = re.compile("|".join(_PADROES_INSEGUROS), re.IGNORECASE)

_REGEX_INJECAO = re.compile(
    r"\b(?:ignore|desconsidere|esqueca|ignore all|disregard|forget)\b.{0,100}"
    r"\b(?:instrucoes|regras|instructions|rules|prompt)\b"
    r"|\b(?:revele|mostre|exiba|repita|imprima|reveal|show|print)\b.{0,80}"
    r"\b(?:prompt|instrucoes internas|system message|system instructions)\b"
    r"|\b(?:finja|atue|aja)\b.{0,60}\b(?:sem restricoes|sem regras|sem filtros)\b"
    r"|\b(?:system|developer)\s*:\s*",
    re.IGNORECASE,
)
_REGEX_DADOS_PESSOAIS = re.compile(
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"
    r"|(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
    r"|\b(?:dados|saldo|extrato|vendas)\b.{0,40}\b(?:outro cliente|outra pessoa|outro usuario)\b"
)
_REGEX_HUMANO = re.compile(
    r"\b(?:quero|preciso|falar|fale|chame|chamar|transfira)\b.{0,60}"
    r"\b(?:atendente|humano|pessoa real)\b"
)


def normalizar_mensagem(mensagem: str) -> str:
    texto = "".join(
        caractere for caractere in unicodedata.normalize("NFKD", mensagem.casefold())
        if not unicodedata.combining(caractere) and unicodedata.category(caractere) != "Cf"
    )
    return re.sub(r"\s+", " ", texto).strip()


@dataclass
class ResultadoGuardrail:
    """Resultado da checagem de guardrail."""

    bloqueado: bool = False
    motivo: str = ""


def checar_entrada(mensagem: str) -> ResultadoGuardrail:
    """Verifica se a mensagem de entrada deve ser bloqueada/transbordada."""
    if not mensagem or not mensagem.strip():
        return ResultadoGuardrail(bloqueado=True, motivo="mensagem_vazia")

    if len(mensagem) > 2500:
        return ResultadoGuardrail(bloqueado=True, motivo="mensagem_longa")

    texto = normalizar_mensagem(mensagem)
    if _REGEX_INJECAO.search(texto):
        return ResultadoGuardrail(bloqueado=True, motivo="instrucao_maliciosa")
    if _REGEX_DADOS_PESSOAIS.search(texto):
        return ResultadoGuardrail(bloqueado=True, motivo="dados_pessoais")
    if _REGEX_INSEGURO.search(texto):
        return ResultadoGuardrail(bloqueado=True, motivo="conteudo_sensivel")
    if _REGEX_HUMANO.search(texto):
        return ResultadoGuardrail(bloqueado=True, motivo="atendimento_humano")

    return ResultadoGuardrail(bloqueado=False)
