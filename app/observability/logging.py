"""Logging estruturado em JSON e geracao de trace_id por request."""

import json
import logging
import sys
import uuid

from app.config import obter_config


class FormatadorJSON(logging.Formatter):
    """Formata cada log como uma linha JSON (facil de ingerir em ferramentas)."""

    def format(self, record: logging.LogRecord) -> str:
        dados = {
            "nivel": record.levelname,
            "logger": record.name,
            "mensagem": record.getMessage(),
        }
        # Campos extras anexados via logger.info(..., extra={...})
        if hasattr(record, "trace_id"):
            dados["trace_id"] = record.trace_id
        if hasattr(record, "etapa"):
            dados["etapa"] = record.etapa
        if hasattr(record, "detalhe"):
            dados["detalhe"] = record.detalhe
        return json.dumps(dados, ensure_ascii=False)


def configurar_logging() -> None:
    """Configura o handler global de logs em JSON."""
    config = obter_config()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(FormatadorJSON())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(config.log_level.upper())


def novo_trace_id() -> str:
    """Gera um identificador curto de trace para correlacionar logs de um request."""
    return uuid.uuid4().hex[:8]


obter_logger = logging.getLogger
