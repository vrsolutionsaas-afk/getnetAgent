"""Fabricas de clientes LLM (ChatOpenAI) para roteamento e geracao."""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import obter_config


@lru_cache
def llm_roteamento() -> ChatOpenAI:
    """LLM rapido/barato usado para classificacao e tarefas internas."""
    config = obter_config()
    return ChatOpenAI(
        model=config.modelo_roteamento,
        temperature=0,
        api_key=config.openai_api_key,
    )


@lru_cache
def llm_geracao() -> ChatOpenAI:
    """LLM principal usado para gerar respostas ao usuario."""
    config = obter_config()
    return ChatOpenAI(
        model=config.modelo_geracao,
        temperature=0.4,
        api_key=config.openai_api_key,
    )
