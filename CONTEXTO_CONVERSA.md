# Contexto da Conversa: Getnet Multi-Agent

## 1. Objetivo do projeto

Foi implementado um sistema técnico para o desafio **AI Hardcore Engineer - Multi-Agent Support System**, com atendimento multi-agente para clientes Getnet.

O objetivo inicial era criar uma API capaz de:

- Receber mensagens em `POST /chat`.
- Roteá-las para agentes especializados.
- Usar RAG com conhecimento de produtos Getnet.
- Usar busca web geral via Tavily.
- Consultar dados simulados de clientes com ferramentas.
- Escalonar casos sensíveis para atendimento humano.
- Executar em Docker e ser publicável no Railway.
- Possuir testes, documentação e demonstração.

Depois, o escopo evoluiu para um portal completo com:

- Login de clientes e administradores.
- Chat com histórico persistido.
- Controle de cotas mensais de tokens.
- Cotas independentes para tokens de entrada e saída.
- BI administrativo de consumo, chamadas e latência.
- Gestão de clientes, bloqueio e limites individuais.
- Frontend Next.js preparado para Vercel.

## 2. Decisões técnicas

- Linguagem principal: Python.
- Backend: FastAPI.
- Orquestração: LangGraph.
- Banco: PostgreSQL com pgvector.
- Busca web: Tavily.
- Modelos: OpenAI.
- RAG: `langchain-postgres` com pgvector.
- Frontend: Next.js com App Router e TypeScript.
- Hospedagem prevista:
  - Backend e PostgreSQL no Railway.
  - Frontend na Vercel.
- Idioma da aplicação e documentação: português.
- O frontend não deve parecer um chat genérico de IA; foi adotado um visual corporativo, focado em atendimento e operação.

## 3. Arquitetura multi-agente

O grafo LangGraph possui os seguintes agentes:

### Router

Classifica a intenção em:

- `produto`
- `conta_cliente`
- `geral`
- `escalar`

O roteamento usa resposta estruturada e possui fallback determinístico.

### Knowledge

Atende perguntas sobre produtos e serviços:

- Consulta a base RAG para assuntos Getnet.
- Usa Tavily para perguntas gerais.
- Faz fallback para busca web quando o RAG não encontra contexto suficiente.
- Recebe histórico recente da conversa para melhorar o contexto.

### Support

Usa dados simulados de clientes e ferramentas para consultar:

- Liquidações de vendas.
- Status da maquininha.
- Antecipação de recebíveis.

O `user_id` usado pelas ferramentas vem do estado autenticado, não do modelo.

### Escalation

É acionado por guardrails ou por decisão do roteador. Atualmente sinaliza a necessidade de atendimento humano, mas ainda não cria ticket nem integra com uma equipe real.

## 4. Guardrails e observabilidade

Foram mantidos guardrails para:

- Bloquear mensagens sensíveis ou inseguras.
- Encaminhar casos inadequados para escalação.
- Mascarar padrões de dados sensíveis na saída.

A observabilidade inclui:

- `trace_id` por chamada.
- Logs estruturados em JSON.
- Lista de etapas percorridas no campo `trace` da resposta.

## 5. Autenticação e segurança

Foi criada a estrutura de autenticação do portal em `app/portal`.

Características:

- Usuários com perfil `cliente` ou `admin`.
- Senhas armazenadas com `hashlib.scrypt`.
- Sessões opacas aleatórias.
- Apenas o hash do token é persistido no banco.
- Sessões expiram em 12 horas.
- Login protegido contra repetição de tentativas por conta e endereço remoto.
- Clientes bloqueados perdem as sessões ativas.
- Administrador não pode bloquear o próprio acesso.
- Conversas são filtradas pelo usuário autenticado.
- Um cliente não consegue acessar a conversa de outro cliente.
- O endpoint original `/chat` agora exige Bearer token.
- O `user_id` informado em `/chat` precisa coincidir com o cliente da sessão.

No frontend:

- O token não fica no `localStorage`.
- O Next.js armazena a sessão em cookie HttpOnly.
- O cookie usa SameSite Lax e Secure em produção.
- O proxy do Next.js aceita apenas rotas e métodos permitidos.
- Operações de escrita validam a origem.
- O proxy nunca expõe o token no JSON retornado ao navegador.

## 6. Controle de cotas e medição

As cotas são mensais e usam o mês-calendário UTC.

Existem dois níveis:

- Cota individual por cliente.
- Cota global da operação.

Cada nível possui limites independentes de:

- Tokens de entrada.
- Tokens de saída.

Antes de chamar o modelo, o sistema reserva saldo. Depois da chamada, substitui a reserva pelo uso real informado pelo provedor.

A medição intercepta as chamadas síncronas dos modelos por meio de `ModeloMedido`, incluindo:

- Roteamento.
- Geração.
- Chamadas com tools.
- Tokens de entrada.
- Tokens de saída.
- Tokens em cache.
- Latência.

A reserva de entrada é conservadora:

- Bytes UTF-8 do payload serializado.
- Margem adicional de 4.096.

O limite máximo de saída é:

- 256 tokens para roteamento.
- 1.024 tokens para geração.

Os retries automáticos dos modelos foram desabilitados para evitar chamadas pagas fora da contabilização.

Em caso de falha sem informação de uso, a reserva permanece como cobrança estimada. Reservas órfãs após queda do processo ainda não possuem reconciliação automática.

Embeddings, ingestão RAG e chamadas Tavily ainda não entram nas cotas nem no BI. Também não há cálculo de custo em dólares.

## 7. Banco de dados do portal

As tabelas principais são:

- `portal_usuarios`
- `portal_sessoes`
- `portal_tentativas_login`
- `portal_limite_global`
- `portal_consumo_mensal`
- `portal_chamadas`
- `portal_conversas`
- `portal_mensagens`

O backend usa `create_all` para criar as tabelas atuais. Futuras mudanças estruturais deverão usar migrações próprias.

No PostgreSQL, as reservas e atualizações de cotas usam bloqueios de linha para reduzir o risco de concorrência entre workers.

SQLite é suportado apenas para testes e prévia local isolada.

## 8. Endpoints do portal

Prefixo: `/portal`

### Autenticação

- `POST /portal/login`
- `POST /portal/logout`
- `GET /portal/sessao`

### Conversas

- `GET /portal/conversas`
- `POST /portal/conversas`
- `GET /portal/conversas/{conversa_id}`
- `POST /portal/mensagens`

### Administração

- `GET /portal/admin/usuarios`
- `POST /portal/admin/usuarios`
- `PATCH /portal/admin/usuarios/{usuario_id}`
- `PUT /portal/admin/cotas`
- `GET /portal/admin/painel?dias=7|30|90`

O painel apresenta:

- Tokens de entrada.
- Tokens de saída.
- Tokens em cache.
- Quantidade de chamadas.
- Latência média.
- Clientes ativos.
- Consumo diário.
- Consumo por modelo e etapa.
- Últimas 30 chamadas.
- Status confirmado, reservado ou estimado após falha.

Também foi adicionado exportador CSV das chamadas recentes.

## 9. Frontend

O frontend está em `frontend-next`.

Tecnologias:

- Next.js 16.
- TypeScript.
- Recharts.
- Lucide React.
- React Markdown.
- Manrope e IBM Plex Mono.

Telas implementadas:

### Login

- Visual corporativo com vermelho Getnet.
- Imagem de pagamento armazenada localmente em `public/checkout.jpg`.
- Mostrar e ocultar senha.
- Mensagens de erro.
- Aviso de que é um ambiente demonstrativo.

### Cliente

- Atendimento.
- Histórico de conversas.
- Nova conversa.
- Sugestões de perguntas.
- Mensagens Markdown.
- Links de fontes.
- Cópia de respostas.
- Contador de caracteres.
- Estado de carregamento.
- Mensagem de cota esgotada.
- Tela de consumo pessoal.

### Administrador

- Visão geral.
- Gráfico de tokens de entrada e saída.
- Filtros de 7, 30 e 90 dias.
- Consumo por modelo e etapa.
- Chamadas recentes.
- Exportação CSV.
- Lista de clientes.
- Busca por nome ou email.
- Criação de clientes.
- Edição de limites.
- Bloqueio e desbloqueio.
- Cotas globais.

O layout foi testado em desktop e celular. O menu móvel é lateral e as tabelas possuem rolagem horizontal controlada.

## 10. Prévia local

Foi criado `tests/portal_preview.py` para testar a interface sem usar OpenAI, Tavily ou banco de produção.

A prévia:

- Usa SQLite temporário.
- Cria contas locais.
- Gera consumo simulado.
- Substitui a execução do chat por resposta local.
- É excluída da imagem Docker.

Contas locais da prévia:

- Administrador: `admin@getnet.local`
- Cliente: `cliente@getnet.local`
- Senha: `Preview-local-2026`

Comandos:

```powershell
python -m uvicorn tests.portal_preview:app --host 127.0.0.1 --port 8001
```

Em outro terminal:

```powershell
$env:GETNET_API_URL = "http://127.0.0.1:8001"
npm --prefix frontend-next run dev -- --hostname 127.0.0.1 --port 3000
```

URL do frontend:

```text
http://127.0.0.1:3000
```

A prévia foi verificada com navegador em 1440px e 390px, incluindo:

- Login.
- Cookie HttpOnly.
- Dashboard.
- Criação e edição de cliente.
- Chat.
- Histórico.
- Logout.
- Bloqueio de acesso administrativo para cliente.
- Ausência de overflow horizontal.

## 11. Testes executados

Resultado final registrado:

```text
38 passed, 1 skipped
```

Também passaram:

- `npm run lint`
- `npm run build`
- Diagnósticos do backend e frontend sem erros.
- Testes de origem externa bloqueada no proxy.
- Testes de cookie HttpOnly.
- Testes de login e logout.
- Testes de isolamento de conversas.
- Testes de cotas individuais e globais.
- Testes de input e output independentes.
- Testes de BI.
- Teste de bloqueio antes de chamar o provedor.

Os warnings restantes vêm principalmente de dependências Python/Pydantic e de configuração futura do pytest-asyncio.

## 12. Deploy previsto

### Railway

O backend continua sendo implantado pelo `Dockerfile` e `railway.toml`.

Variáveis necessárias:

- `OPENAI_API_KEY`
- `TAVILY_API_KEY`
- `DATABASE_URL`
- `ADMIN_TOKEN`
- `PORTAL_ADMIN_EMAIL`
- `PORTAL_ADMIN_SENHA` na primeira criação do administrador

O `railway.toml` possui:

```toml
preDeployCommand = "python -m scripts.preparar_portal"
```

Depois que o administrador for criado, a senha inicial deve ser removida do ambiente. O script é idempotente e não altera senha ou permissões de administrador existente.

### Vercel

Configuração prevista:

- Root Directory: `frontend-next`.
- Framework: Next.js.
- `GETNET_API_URL=https://getnetagent-production.up.railway.app`
- `PORTAL_ORIGIN=https://seu-dominio.vercel.app`

As variáveis não devem usar prefixo `NEXT_PUBLIC_`, pois são utilizadas pelo proxy server-side.

O backend deve ser atualizado antes de testar o frontend publicado.

## 13. Pontos ainda pendentes

- Publicar as alterações no GitHub.
- Fazer deploy do backend atualizado no Railway.
- Configurar as variáveis reais do Railway.
- Criar o administrador no ambiente de produção.
- Criar o projeto Vercel e configurar o frontend.
- Testar concorrência real em PostgreSQL.
- Testar chamadas reais com OpenAI e Tavily.
- Implementar reconciliação de reservas órfãs.
- Medir embeddings e Tavily, caso essas cotas sejam necessárias.
- Criar migrações formais para futuras alterações de banco.
- Integrar escalonamento com ticket ou atendimento humano real.
- Verificar e validar fontes oficiais da base curada do RAG.

## 14. Cuidados importantes

- Não publicar credenciais de teste como credenciais de produção.
- Não expor tokens de sessão em logs ou no frontend.
- Não afirmar que o atendimento humano é real enquanto não houver integração de ticket.
- Não afirmar que as cotas medem embeddings ou Tavily.
- Não afirmar que a estimativa conservadora de input equivale exatamente aos tokens cobrados pelo provedor.
- Não fazer deploy ou criar recursos pagos sem autorização explícita.
- Não versionar `.env`, tokens ou senhas.

## 15. Atualização dos agentes e guardrails (28/09/2026)

Após a publicação do portal, foram observadas respostas inadequadas para "Olá"
e "Conte até 100": ambas eram encaminhadas para busca web. O fluxo foi ajustado:

- Novas rotas `saudacao`, `encerramento`, `fora_escopo` e `esclarecer`, atendidas
  localmente pelo nó `atendimento`, sem modelo de geração nem fontes artificiais.
- Cumprimentos, despedidas e contagens reconhecidos pelas regras determinísticas
  também dispensam o modelo de roteamento. As demais intenções usam classificação.
- Falha do roteador pede esclarecimento, em vez de assumir `produto`.
- Clima, câmbio e notícias continuam permitidos na rota `geral`, preservando o desafio.
- Guardrails normalizam texto e bloqueiam padrões de instruções maliciosas,
  CPF/cartão e pedidos de dados de terceiros antes do roteamento.
- Histórico bloqueado não é reenviado aos modelos. Fontes recuperadas ficam
  separadas da política de sistema e são tratadas como dados não confiáveis.
- Fallback de produtos para Tavily é limitado a `getnet.com.br` e subdomínios,
  com verificação do hostname. Sem evidências, a resposta informa a limitação.
- Support não publica afirmações de conta sem ferramenta autorizada e dados
  encontrados. Continua usando a identidade autenticada, nunca a indicada pelo modelo.
- A conta bancária é retirada do resultado da ferramenta antes do envio ao modelo.
  O prompt informa que os dados são simulados e que não há operações financeiras.
- Escalation não promete transferência, protocolo ou atendente em instantes.
  `escalated` indica bloqueio ou necessidade de revisão, não transferência efetiva.
- Saída mascara também padrões de CPF, cartão e credenciais.

Validação local desta atualização: **85 passed, 1 skipped**. O teste ignorado
requer chamadas reais; os demais usam dublês e bancos temporários isolados. Não
houve acesso ao PostgreSQL de produção nem consumo de OpenAI/Tavily nesta validação.
Regex e prompts reduzem riscos, mas não garantem proteção absoluta contra prompt
injection ou erros factuais. Ainda é necessária avaliação das respostas com modelos
reais. O usuário autorizou o commit e push destas melhorias para a `main`.
A validação em produção permanece pendente após o deploy do Railway.
