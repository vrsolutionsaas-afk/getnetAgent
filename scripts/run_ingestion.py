"""Script de linha de comando para (re)indexar a base de conhecimento Getnet.

Uso:
    python -m scripts.run_ingestion

Requer que o Postgres (pgvector) esteja de pe e as variaveis de ambiente
configuradas (OPENAI_API_KEY, POSTGRES_*).
"""

from app.observability.logging import configurar_logging
from app.rag.ingest import executar_ingestao


def main() -> None:
    configurar_logging()
    total = executar_ingestao()
    print(f"Ingestao finalizada: {total} chunks inseridos.")


if __name__ == "__main__":
    main()
