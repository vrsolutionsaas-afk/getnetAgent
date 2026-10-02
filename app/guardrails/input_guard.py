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
    r"\b(clonar|hackear|invadir)\b",
]

_REGEX_INSEGURO = re.compile("|".join(_PADROES_INSEGUROS), re.IGNORECASE)
# Situacoes reais que exigem pessoa (vitima de golpe, risco a vida), nao recusa.
_REGEX_RISCO = re.compile(r"\b(fraude|golpe|matar|suicidio|ameaca|bomba)\b")

_ALVOS_REGRAS = (
    r"instrucoes|regras|instructions|rules|prompts?|politicas|seguranca"
    r"|restricoes|filtros|diretrizes|policies|guidelines|safeguards?"
)
_REGEX_INJECAO = re.compile(
    rf"\b(?:ignore|desconsidere|esqueca|ignore all|disregard|forget)\b.{{0,100}}\b(?:{_ALVOS_REGRAS})\b"
    r"|\b(?:revele|mostre|exiba|repita|imprima|reveal|show|print)\b.{0,80}"
    r"\b(?:prompts?|instrucoes internas|system message|system instructions)\b"
    rf"|\b(?:finja|atue|aja|act|pretend)\b.{{0,60}}\b(?:sem|nao tivesse|nao tem|without)\b.{{0,20}}\b(?:{_ALVOS_REGRAS})\b"
    rf"|\b(?:burlar|contornar|driblar|bypass|circumvent)\b.{{0,60}}\b(?:{_ALVOS_REGRAS}|autenticacao|protecoes)\b"
    r"|\b(?:siga|seguir|obedeca|follow|obey)\b.{0,40}\b(?:minhas|my) (?:instrucoes|ordens|instructions|commands)\b"
    r"|\b(?:system|developer)\s*:\s*",
    re.IGNORECASE,
)
_REGEX_DADOS_PESSOAIS = re.compile(
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"
    r"|(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
    r"|\b(?:dados|saldo|extrato|vendas|cpf)\b (?:\w+ )?(?:de|do|da|dos|das) "
    r"(?:outr[oa]s? (?:clientes?|pessoas?|usuarios?|lojistas?)|cliente \d+)\b"
    r"|\b(?:access|see|view|show|data)\b.{0,30}\b(?:other|another) (?:users?|customers?|accounts?|people)\b"
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
    if _REGEX_RISCO.search(texto):
        return ResultadoGuardrail(bloqueado=True, motivo="risco")
    if _REGEX_INSEGURO.search(texto):
        return ResultadoGuardrail(bloqueado=True, motivo="conteudo_sensivel")
    if _REGEX_HUMANO.search(texto):
        return ResultadoGuardrail(bloqueado=True, motivo="atendimento_humano")

    return ResultadoGuardrail(bloqueado=False)
