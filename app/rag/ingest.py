"""Pipeline de ingestao do RAG: scrape do site Getnet -> chunk -> embed -> pgvector.

Fluxo:
  1. Baixa o HTML de uma lista curada de paginas do site da Getnet.
  2. Extrai o texto limpo (remove scripts, nav, footer).
  3. Divide em chunks com sobreposicao.
  4. Gera embeddings e armazena no pgvector.
"""

import logging

import httpx
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.vectorstore import garantir_extensao_vector, obter_vectorstore

logger = logging.getLogger(__name__)

# Paginas curadas do site da Getnet que cobrem os temas dos cenarios do desafio:
# maquininhas (Get Clássica/Smart), Pix, antecipacao, crediario, link de pagamento.
URLS_GETNET = [
    "https://www.getnet.com.br/",
    "https://www.getnet.com.br/maquininhas/",
    "https://www.getnet.com.br/receba-por-pix/",
    "https://www.getnet.com.br/antecipacao-de-recebiveis/",
    "https://www.getnet.com.br/link-de-pagamento/",
    "https://www.getnet.com.br/perguntas-frequentes/",
    "https://www.getnet.net/en",
]

# Parametros de chunking
TAMANHO_CHUNK = 1000
SOBREPOSICAO_CHUNK = 150

# Cabecalho para evitar bloqueio simples por ausencia de User-Agent
CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GetnetRAGBot/1.0; +https://www.getnet.com.br)"
    )
}


def _extrair_texto(html: str) -> str:
    """Extrai texto limpo do HTML, removendo ruido de navegacao."""
    sopa = BeautifulSoup(html, "lxml")
    for tag in sopa(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    texto = sopa.get_text(separator=" ", strip=True)
    # Normaliza espacos em excesso
    return " ".join(texto.split())


def _baixar_paginas(urls: list[str]) -> list[Document]:
    """Baixa cada URL e retorna Documents com o texto e a fonte nos metadados."""
    documentos: list[Document] = []
    with httpx.Client(timeout=30, follow_redirects=True, headers=CABECALHOS) as cliente:
        for url in urls:
            try:
                resposta = cliente.get(url)
                resposta.raise_for_status()
                texto = _extrair_texto(resposta.text)
                if len(texto) < 200:
                    logger.warning("Pagina com pouco texto, ignorada: %s", url)
                    continue
                documentos.append(Document(page_content=texto, metadata={"source": url}))
                logger.info("Baixado: %s (%d chars)", url, len(texto))
            except Exception as exc:  # noqa: BLE001 - ingestao best-effort por URL
                logger.warning("Falha ao baixar %s: %s", url, exc)
    return documentos


def executar_ingestao(urls: list[str] | None = None) -> int:
    """Executa o pipeline completo de ingestao. Retorna o numero de chunks inseridos."""
    urls = urls or URLS_GETNET
    logger.info("Iniciando ingestao de %d URLs", len(urls))

    garantir_extensao_vector()

    documentos = _baixar_paginas(urls)
    if not documentos:
        logger.error("Nenhum documento baixado. Ingestao abortada.")
        return 0

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=TAMANHO_CHUNK,
        chunk_overlap=SOBREPOSICAO_CHUNK,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = divisor.split_documents(documentos)
    logger.info("Gerados %d chunks a partir de %d documentos", len(chunks), len(documentos))

    vectorstore = obter_vectorstore()
    vectorstore.add_documents(chunks)
    logger.info("Ingestao concluida: %d chunks inseridos no pgvector", len(chunks))
    return len(chunks)
