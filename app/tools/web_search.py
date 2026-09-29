"""Ferramenta de busca na web (Tavily) para perguntas gerais fora do escopo Getnet."""

import logging
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from tavily import TavilyClient

from app.config import obter_config

logger = logging.getLogger(__name__)


@dataclass
class ResultadoWeb:
    """Resultado consolidado de uma busca na web."""

    resumo: str = ""
    fontes: list[str] = field(default_factory=list)
    sucesso: bool = False


def buscar_na_web(consulta: str, max_resultados: int = 4, dominios: list[str] | None = None) -> ResultadoWeb:
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
        filtros = {"include_domains": dominios} if dominios else {}
        resposta = cliente.search(
            query=consulta,
            max_results=max_resultados,
            include_answer=False,
            search_depth="basic",
            **filtros,
        )
    except Exception as exc:  # noqa: BLE001 - falha de rede nao pode derrubar o agente
        logger.warning("Falha na busca Tavily: %s", type(exc).__name__)
        return ResultadoWeb()

    fontes: list[str] = []
    trechos: list[str] = []
    for item in resposta.get("results", []):
        url = item.get("url", "")
        conteudo = item.get("content", "")
        try:
            endereco = urlsplit(url)
            host = endereco.hostname or ""
            permitido = endereco.scheme in {"http", "https"} and bool(host) and not endereco.username and not endereco.password
            if dominios:
                permitido = permitido and any(host == dominio or host.endswith(f".{dominio}") for dominio in dominios)
        except ValueError:
            continue
        if permitido and conteudo and url not in fontes:
            fontes.append(url)
            trechos.append(f"Fonte: {url}\n{conteudo[:4000]}")

    if not trechos:
        return ResultadoWeb()

    return ResultadoWeb(resumo="\n\n".join(trechos), fontes=fontes, sucesso=True)
