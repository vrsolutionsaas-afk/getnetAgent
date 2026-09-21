"""Ferramenta de busca na web (Tavily) para perguntas gerais fora do escopo Getnet."""

import logging
from dataclasses import dataclass, field

from tavily import TavilyClient

from app.config import obter_config

logger = logging.getLogger(__name__)


@dataclass
class ResultadoWeb:
    """Resultado consolidado de uma busca na web."""

    resumo: str = ""
    fontes: list[str] = field(default_factory=list)
    sucesso: bool = False


def buscar_na_web(consulta: str, max_resultados: int = 4) -> ResultadoWeb:
    """Executa uma busca na web via Tavily e retorna um resumo com fontes.

    Usado para perguntas gerais (clima, cotacao de moeda, etc.) que nao sao
    respondidas pela base de conhecimento da Getnet.
    """
    config = obter_config()
    if not config.tavily_api_key:
        logger.warning("TAVILY_API_KEY nao configurada; web search indisponivel.")
        return ResultadoWeb()

    try:
        cliente = TavilyClient(api_key=config.tavily_api_key)
        resposta = cliente.search(
            query=consulta,
            max_results=max_resultados,
            include_answer=True,
            search_depth="basic",
        )
    except Exception as exc:  # noqa: BLE001 - falha de rede nao pode derrubar o agente
        logger.warning("Falha na busca Tavily: %s", exc)
        return ResultadoWeb()

    resumo = resposta.get("answer") or ""
    fontes: list[str] = []
    trechos: list[str] = []
    for item in resposta.get("results", []):
        if item.get("url"):
            fontes.append(item["url"])
        if item.get("content"):
            trechos.append(item["content"])

    if not resumo and trechos:
        resumo = "\n\n".join(trechos[:3])

    if not resumo:
        return ResultadoWeb()

    return ResultadoWeb(resumo=resumo, fontes=fontes, sucesso=True)
