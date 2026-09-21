"""Guardrail de entrada: deteccao deterministica de conteudo inseguro/fora de escopo.

Roda ANTES do roteamento. Se bloquear, o fluxo vai direto para o Escalation Agent.
Deteccao por regex/heuristica (deterministica) - nao depende do LLM, como
recomendado para acoes criticas de seguranca.
"""

import re
from dataclasses import dataclass

# Padroes de conteudo que deve ser transbordado/bloqueado
_PADROES_INSEGUROS = [
    r"\b(senha|password|token|cvv|c[oó]digo de seguran[cç]a)\b",
    r"\b(cart[aã]o de cr[eé]dito de outra pessoa|dados de outro cliente)\b",
    r"\b(fraude|clonar|hackear|invadir|golpe)\b",
    r"\b(matar|suic[ií]dio|amea[cç]a|bomba)\b",
]

_REGEX_INSEGURO = re.compile("|".join(_PADROES_INSEGUROS), re.IGNORECASE)


@dataclass
class ResultadoGuardrail:
    """Resultado da checagem de guardrail."""

    bloqueado: bool = False
    motivo: str = ""


def checar_entrada(mensagem: str) -> ResultadoGuardrail:
    """Verifica se a mensagem de entrada deve ser bloqueada/transbordada."""
    if not mensagem or not mensagem.strip():
        return ResultadoGuardrail(bloqueado=True, motivo="mensagem_vazia")

    if _REGEX_INSEGURO.search(mensagem):
        return ResultadoGuardrail(bloqueado=True, motivo="conteudo_sensivel")

    return ResultadoGuardrail(bloqueado=False)
