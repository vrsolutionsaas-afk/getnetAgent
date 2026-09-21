-- Inicializacao do banco de dados para o RAG (pgvector).
-- Executado automaticamente pelo container do Postgres no primeiro start.

CREATE EXTENSION IF NOT EXISTS vector;

-- As tabelas de embeddings sao criadas/gerenciadas pelo langchain-postgres
-- (PGVector) na primeira ingestao. Aqui garantimos apenas a extensao.
