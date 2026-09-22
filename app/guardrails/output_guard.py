"""Guardrail de saida: sanea a resposta final antes de retornar ao usuario.

Mascara numeros de conta bancaria e agencia que possam vazar para o texto,
mesmo que uma tool os tenha retornado como fato interno. Mantem o nome do banco
(util), removendo apenas os digitos sensiveis.
"""

import re

# "agência 1234" / "Ag 1234" / "Ag. 1234"
_REGEX_AGENCIA = re.compile(r"\bag(?:[êe]ncia|\.?)\s*n?[º°]?\s*\d[\d.\- ]*", re.IGNORECASE)

# "conta corrente 56789-0" / "conta 56789-0" / "CC 56789-0" / "C/C 56789-0"
_REGEX_CONTA = re.compile(
    r"\b(?:conta(?:\s+corrente)?|CC|C/C)\s*n?[º°]?\s*\d[\d.\- ]*",
    re.IGNORECASE,
)


def sanear_saida(resposta: str) -> str:
    """Aplica saneamento minimo na resposta final (mascara agencia e conta)."""
    if not resposta:
        return resposta
    resposta = _REGEX_AGENCIA.sub("agência **** ", resposta)
    resposta = _REGEX_CONTA.sub("conta cadastrada ", resposta)
    return resposta
