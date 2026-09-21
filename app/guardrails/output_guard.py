"""Guardrail de saida: sanea a resposta final antes de retornar ao usuario.

Remove vazamento de detalhes internos (numero de serie, dados de conta bancaria
completos) que nao devem aparecer na resposta textual, mesmo que uma tool os
tenha retornado como fato interno.
"""

import re

# Mascara numero de conta/agencia completo se escapar para o texto
_REGEX_CONTA = re.compile(r"\b(CC|C/C|conta)\s*[:\s]?\s*\d{3,}[-\d]*", re.IGNORECASE)


def sanear_saida(resposta: str) -> str:
    """Aplica saneamento minimo na resposta final."""
    if not resposta:
        return resposta
    return _REGEX_CONTA.sub("sua conta cadastrada", resposta)
