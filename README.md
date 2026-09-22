# Getnet Multi-Agent Support System

Sistema **multi-agente** de suporte ao cliente da Getnet (adquirente de pagamentos:
maquininhas, Pix, antecipação de recebíveis, link de pagamento, crediário).

Os agentes cooperam para interpretar a mensagem do usuário e produzir uma resposta
útil, combinando **RAG** (base de conhecimento do site Getnet), **web search** (Tavily)
e **ferramentas de dados do cliente**. A orquestração é feita com **LangGraph** e
exposta por uma API **FastAPI**.

---

## Índice
- [Arquitetura](#arquitetura)
- [Os agentes](#os-agentes)
- [Fluxo da mensagem](#fluxo-da-mensagem)
- [Pipeline RAG](#pipeline-rag)
- [Guardrails e observabilidade](#guardrails-e-observabilidade)
- [Como rodar](#como-rodar)
- [Contrato da API](#contrato-da-api)
- [Estratégia de testes](#estratégia-de-testes)
- [Estrutura de pastas](#estrutura-de-pastas)

---

## Arquitetura

```
POST /chat {message, user_id}
        │
        ▼
[Guardrail de entrada]  ──(bloqueado)──►  Escalation Agent
        │ (ok)
        ▼
   Router Agent  ──► classifica a intenção
        │
        ├─ produto / geral ──►  Knowledge Agent ──► RAG (pgvector) ou Web (Tavily)
        ├─ conta_cliente   ──►  Support Agent   ──► tools (dados do cliente)
        └─ escalar         ──►  Escalation Agent
        │
        ▼
[Guardrail de saída] ──► Resposta JSON (+ trace)
```

- **Orquestração:** LangGraph (grafo de estados com arestas condicionais)
- **API:** FastAPI (+ Swagger UI em `/docs`)
- **RAG:** pgvector + `text-embedding-3-small`
- **Web search:** Tavily
- **LLMs:** `gpt-4o-mini` (roteamento) e `gpt-4o` (geração)

O estado (`AgentState`) trafega entre os nós carregando: mensagem, `user_id`, rota
decidida, contexto recuperado, resultados de tools, resposta, fontes e o `trace`.

## Os agentes

| Agente | Papel | Mecanismo |
|--------|-------|-----------|
| **Router** | Ponto de entrada; classifica a mensagem em `produto`, `conta_cliente`, `geral` ou `escalar` | LLM com saída estruturada + validação determinística |
| **Knowledge** | Responde sobre produtos/serviços Getnet (RAG) e perguntas gerais (web) | RAG no pgvector; fallback para Tavily quando o RAG não é relevante |
| **Support** | Atendimento com dados do cliente | 3 tools: `liquidacao_vendas`, `status_maquininha`, `antecipacao_recebiveis` |
| **Escalation** (bônus) | Handoff para humano | Acionado por guardrail ou rota `escalar` |

**Princípios de design** (aprendidos em produção):
- As **tools retornam fatos estruturados**, nunca texto final — o LLM compõe a resposta.
- O `user_id` usado nas tools vem **sempre do estado**, nunca do LLM (evita que o
  modelo invente identificadores e acesse dados de outro cliente).
- Ações críticas (bloqueio, escalonamento) são **determinísticas**, não dependem do
  LLM chamar uma tool.

## Fluxo da mensagem

1. **Guardrail de entrada** (determinístico): bloqueia conteúdo vazio, sensível ou
   inseguro → vai direto ao Escalation Agent.
2. **Router**: classifica a intenção.
3. **Agente especializado**:
   - `produto` → Knowledge (RAG); se o RAG não for relevante, cai no web search.
   - `geral` → Knowledge (web search direto).
   - `conta_cliente` → Support (tools).
   - `escalar` → Escalation.
4. **Guardrail de saída**: mascara dados sensíveis (ex.: conta bancária) que
   possam ter vazado para o texto.

Mapeamento dos cenários do desafio:

| Mensagem | Rota | Agente | Mecanismo |
|----------|------|--------|-----------|
| Diferença Get Clássica × Get Smart | produto | Knowledge | RAG |
| Previsão do tempo em POA amanhã | geral | Knowledge | Web (Tavily) |
| Quando cai o dinheiro da venda de ontem | conta_cliente | Support | Tool |
| Preciso de conta pra receber via Pix | produto | Knowledge | RAG |
| Maquininha não conecta na internet | conta_cliente | Support | Tool |
| Como funciona antecipação | produto | Knowledge | RAG |
| Cotação do euro hoje | geral | Knowledge | Web (Tavily) |

## Pipeline RAG

**Ingestão → Armazenamento → Recuperação → Geração**

> **Decisão de arquitetura sobre a fonte de dados:** o site oficial da Getnet é uma
> SPA renderizada em JavaScript com redirecionamentos de tracking, o que impede a
> extração de conteúdo útil por scraping estático (todas as URLs caem numa home
> genérica). Por isso, a **fonte principal do RAG é uma base de conhecimento curada**
> ([app/data/getnet_kb.py](app/data/getnet_kb.py)), escrita a partir das informações
> públicas dos produtos Getnet e cobrindo todos os cenários do desafio. O scraper do
> site permanece no pipeline como **fonte complementar** (best-effort, com
> deduplicação). O desafio autoriza isso explicitamente (*"please, look for other
> sources"*).

1. **Ingestão** ([app/rag/ingest.py](app/rag/ingest.py)): carrega os documentos
   curados e, opcionalmente, faz scraping das páginas do site (BeautifulSoup,
   removendo nav/script/footer e deduplicando páginas repetidas por redirect).
   Divide tudo em chunks de ~1000 caracteres com sobreposição de 150.
2. **Armazenamento** ([app/rag/vectorstore.py](app/rag/vectorstore.py)): gera
   embeddings com `text-embedding-3-small` e armazena no **pgvector**
   (`langchain-postgres`, metadados em JSONB, coleção `getnet_knowledge`). A cada
   ingestão a coleção é recriada (idempotente).
3. **Recuperação** ([app/rag/retriever.py](app/rag/retriever.py)): busca por
   similaridade com score normalizado e aplica um **limiar**
   (`RAG_LIMIAR_SIMILARIDADE`). Se nenhum trecho passar, marca como não relevante →
   o Knowledge Agent usa o **web search** como fallback (evita alucinação).
4. **Geração**: o `gpt-4o` responde ancorado **somente** no contexto recuperado,
   citando as fontes (URLs) na resposta.

Reindexar a base:

```bash
python -m scripts.run_ingestion
```

## Guardrails e observabilidade

- **Guardrail de entrada** (`app/guardrails/input_guard.py`): regex determinístico
  para conteúdo sensível/inseguro (senha, fraude, dados de terceiros) → escalonamento.
- **Guardrail de saída** (`app/guardrails/output_guard.py`): mascara dados de conta
  bancária que escapem para o texto.
- **Observabilidade** (`app/observability/logging.py`): cada request recebe um
  `trace_id`; os logs são **estruturados em JSON** (nível, etapa, trace_id, detalhe).
  A resposta inclui um campo `trace` com os passos percorridos — ótimo para depurar e
  para a demonstração.

## Como rodar

### Pré-requisitos
- Docker e Docker Compose
- Chaves: `OPENAI_API_KEY` e `TAVILY_API_KEY`

### 1. Configurar o ambiente

```bash
cp .env.example .env
# edite .env e preencha OPENAI_API_KEY e TAVILY_API_KEY
```

### 2. Subir com Docker Compose (recomendado)

```bash
docker compose up --build
```

Isso sobe o Postgres (pgvector) e a API. Aguarde o banco ficar saudável.

### 3. Indexar a base de conhecimento (uma vez)

```bash
docker compose exec api python -m scripts.run_ingestion
```

### 4. Testar

- Swagger UI: http://localhost:8000/docs
- Smoke test dos 10 cenários:

```bash
docker compose exec api python -m scripts.smoke_test
```

- Ou via `curl`:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the difference between Get Clássica and Get Smart?", "user_id": "cliente1988"}'
```

### Rodar localmente (sem Docker)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# suba um Postgres com pgvector e ajuste POSTGRES_HOST=localhost no .env
python -m scripts.run_ingestion
uvicorn app.main:app --reload
```

### Deploy no Railway (opcional, URL pública)

O projeto está pronto para deploy no Railway via `railway.toml` (build pelo Dockerfile).

1. **Banco pgvector**: no projeto Railway, adicione um serviço de banco com a imagem
   `pgvector/pgvector:pg16` (ou o template pgvector do marketplace) com um volume em
   `/var/lib/postgresql/data`.
2. **API**: adicione um serviço a partir do repositório GitHub. O Railway detecta o
   `railway.toml` e faz o build pelo Dockerfile. A porta é injetada via `PORT`.
3. **Variáveis** no serviço da API:
   - `OPENAI_API_KEY`, `TAVILY_API_KEY`
   - `DATABASE_URL` — referência ao banco pgvector (ex.: `${{Postgres.DATABASE_URL}}`)
   - `ADMIN_TOKEN` — um token secreto seu (habilita o endpoint de ingestão)
4. **Ingestão** (uma vez, após o deploy): como não há terminal, chame o endpoint
   protegido `POST /admin/ingest` com o header `X-Admin-Token: <ADMIN_TOKEN>` — pode
   ser feito direto pelo Swagger `/docs`. A extensão `vector` é criada automaticamente.

## Contrato da API

**Request** — `POST /chat`

```json
{ "message": "How does receivables advance work?", "user_id": "cliente1988" }
```

**Response**

```json
{
  "response": "A antecipação permite receber o valor das vendas antes do prazo...",
  "agent": "knowledge",
  "route": "produto",
  "sources": ["https://www.getnet.com.br/antecipacao-de-recebiveis/"],
  "escalated": false,
  "trace_id": "a1b2c3d4",
  "trace": ["guardrail_entrada -> ok", "router -> produto", "knowledge -> rag", "finalizar -> guardrail_saida"]
}
```

Usuários de teste na base mock: `cliente1988` (maquininha offline, antecipação
disponível) e `cliente2025` (maquininha online).

## Estratégia de testes

A suíte cobre três níveis, priorizando testes **rápidos e sem dependências externas**:

1. **Unitários determinísticos** (sem rede):
   - `test_guardrails.py` — bloqueio de entrada e saneamento de saída.
   - `test_support_tools.py` — as 3 tools sobre a base mock.
   - `test_router.py` — mapa de roteamento do grafo (arestas condicionais).
2. **Integração** (`test_integration.py`):
   - Fluxo de **escalonamento por guardrail** ponta a ponta via `TestClient` — sem
     nenhum dublê, pois é determinístico.
   - Nós **Knowledge** (RAG e fallback web) com LLM/RAG/Tavily **dublados**
     (monkeypatch), validando a lógica de decisão sem gastar tokens.
3. **Smoke test end-to-end** (`scripts/smoke_test.py`): executa os 10 cenários do
   desafio contra a API real (requer chaves e base indexada).

Rodar os testes:

```bash
pytest
```

**Como eu abordaria testes de integração abrangentes em produção:**
- Dataset de **regressão** com pares (pergunta → rota esperada / agente esperado /
  fontes esperadas), rodado a cada mudança de prompt.
- **Avaliação de qualidade** (LLM-as-judge) para respostas do Knowledge/Support,
  medindo fidelidade ao contexto (groundedness) e ausência de alucinação.
- Testes de **roteamento** com um conjunto rotulado de mensagens (matriz de confusão
  das rotas).
- **Contract tests** do endpoint (schema da resposta) e testes de resiliência
  (Tavily/OpenAI indisponíveis → degradação graciosa, já tratada com try/except).
- **Observabilidade em produção:** traces por request, logs estruturados, métricas de
  latência/tokens por agente, alertas de taxa de escalonamento e de fallback do RAG.

## Estrutura de pastas

```
getnet-multiagent/
├── app/
│   ├── main.py                # FastAPI + POST /chat + /health
│   ├── config.py              # settings (.env)
│   ├── schemas.py             # ChatRequest / ChatResponse
│   ├── graph/                 # Orquestração LangGraph
│   │   ├── state.py           # AgentState
│   │   ├── builder.py         # montagem do grafo
│   │   ├── router_agent.py    # Agente 1 — Router
│   │   ├── knowledge_agent.py # Agente 2 — Knowledge (RAG + web)
│   │   ├── support_agent.py   # Agente 3 — Support (tools)
│   │   ├── escalation_agent.py# Agente 4 — Escalation (bônus)
│   │   └── llm.py             # fábricas de ChatOpenAI
│   ├── rag/                   # ingest / vectorstore / retriever
│   ├── tools/                 # web_search (Tavily) + customer_tools
│   ├── guardrails/            # input_guard / output_guard
│   ├── observability/         # logging estruturado + trace_id
│   └── data/                  # mock_users
├── scripts/                   # run_ingestion / smoke_test
├── tests/                     # unitários + integração
├── db/init.sql                # CREATE EXTENSION vector
├── Dockerfile
├── docker-compose.yml         # api + pgvector
├── requirements.txt
└── .env.example
```

---

Feito com foco em código modular e manutenível, prompts de alta qualidade, pipeline
RAG funcional, guardrails determinísticos e observabilidade — conforme os critérios
de avaliação do desafio.
