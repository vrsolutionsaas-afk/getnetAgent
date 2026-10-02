"use client";

import { useEffect, useState, type KeyboardEvent } from "react";
import Image from "next/image";
import { Download, ExternalLink, Maximize2, Minus, Plug, Plus, RefreshCw, RotateCcw, ShieldCheck, Workflow } from "lucide-react";
import { ErrorNotice, Modal, Spinner } from "./ui";
import styles from "./architecture.module.css";

const diagramUrl = "/api/admin/arquitetura";
const diagramAlt = "Fluxo Getnet: navegador, portal Next.js na Vercel, FastAPI e agentes no Railway, PostgreSQL com pgvector, dados simulados de suporte, OpenAI e Tavily.";
const tabs = [
  { key: "fluxo", label: "Visão da arquitetura", icon: Workflow },
  { key: "integracoes", label: "Integrações", icon: Plug },
  { key: "seguranca", label: "Segurança e limites", icon: ShieldCheck },
] as const;

const steps = [
  ["Entrada autenticada", "O portal encaminha a pergunta. A sessão identifica o cliente; um nome digitado no chat não troca a conta consultada."],
  ["Triagem e segurança", "Regras verificam a mensagem. O roteador escolhe a função adequada; saudações conhecidas recebem respostas locais."],
  ["Consulta aos fatos", "Produtos usam a base de conhecimento. Informações atuais usam a web. Consultas de conta usam ferramentas com dados simulados."],
  ["Resposta e registro", "A saída passa pelo mascaramento de padrões sensíveis. O portal registra o histórico e as chamadas aos modelos são contabilizadas."],
];

const integrations = [
  { name: "Vercel / Next.js", kind: "Hospedagem prevista", role: "Portal e servidor intermediário", data: "Login, chat, histórico e painel. Encaminha chamadas autenticadas à API; mantém a sessão em cookie HttpOnly." },
  { name: "Railway / FastAPI", kind: "Hospedagem prevista", role: "Serviço de atendimento", data: "Valida a sessão, aplica regras do portal e inicia o fluxo dos agentes. Backend Python empacotado com Docker." },
  { name: "LangGraph", kind: "Orquestração interna", role: "Coordenação dos agentes", data: "Organiza guardrails, roteamento, consultas e resposta. Nem toda etapa usa um modelo ou um serviço externo." },
  { name: "PostgreSQL + pgvector", kind: "Persistência", role: "Dados do portal e conhecimento", data: "Usuários, sessões, conversas, cotas e consumo. O índice vetorial encontra trechos de produtos por semelhança de significado." },
  { name: "OpenAI", kind: "Provedor externo", role: "Classificação, geração e embeddings", data: "Padrões do projeto: gpt-4o-mini para rotear, gpt-4o para responder e text-embedding-3-small para a busca na base. Modelos configuráveis no backend." },
  { name: "Tavily", kind: "Provedor externo", role: "Busca na web", data: "Clima, câmbio e outras informações atuais. Quando falta contexto de produtos, a busca é restrita a getnet.com.br e subdomínios." },
  { name: "Ferramentas de suporte", kind: "Dados simulados", role: "Consultas da conta autenticada", data: "Liquidação de vendas, status da maquininha e antecipação disponível. Não consultam sistemas bancários reais nem executam operações financeiras." },
];

const safeguards = [
  ["Identidade e acesso", "A API valida a sessão e o perfil. Consultas e históricos são vinculados ao usuário autenticado; identificadores sugeridos pelo modelo não autorizam acesso a outra conta."],
  ["Instruções e dados separados", "Os prompts definem as responsabilidades de cada agente. Mensagens, histórico e documentos não devem substituir as regras de sistema. Prompts não são uma barreira de autorização por si só."],
  ["Proteções de entrada e saída", "Regras bloqueiam padrões conhecidos de prompt injection e pedidos de dados de terceiros. Dados bancários são retirados dos resultados de suporte antes da geração, e a saída mascara padrões sensíveis. Isso reduz riscos, sem garantir proteção absoluta."],
  ["Recusa e atendimento humano", "Pedidos indevidos recebem recusa. Casos que exigem uma pessoa recebem orientação aos canais oficiais. Não há transferência automática, abertura de protocolo ou integração com uma equipe humana."],
  ["Consumo e cotas", "Limites mensais independentes de entrada e saída, por usuário e globais. Há reserva antes da chamada e apuração com o uso informado pelo provedor. Embeddings e Tavily ficam fora dessas cotas; não há limite financeiro em dólares."],
  ["Rastreabilidade e evolução", "Cada atendimento tem um identificador e o percurso dos agentes. Falhas sem dados de consumo mantêm uma estimativa; reservas órfãs ainda não têm reconciliação automática. Fontes, respostas reais e concorrência em produção exigem validação contínua."],
];

export default function Architecture() {
  const [tab, setTab] = useState<(typeof tabs)[number]["key"]>("fluxo");
  const [expanded, setExpanded] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [revision, setRevision] = useState(0);
  const imageUrl = `${diagramUrl}?v=${revision}`;

  useEffect(() => {
    if (!expanded) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); setExpanded(false); }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [expanded]);

  function navigateTabs(event: KeyboardEvent<HTMLDivElement>) {
    const index = tabs.findIndex(item => item.key === tab);
    const next = event.key === "ArrowRight" ? (index + 1) % tabs.length : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault();
    setTab(tabs[next].key);
    document.getElementById(`architecture-tab-${tabs[next].key}`)?.focus();
  }

  function retryImage() { setImageError(false); setImageLoaded(false); setRevision(value => value + 1); }

  return <main className={`content ${styles.page}`}>
    <div className={`page-heading ${styles.heading}`}>
      <div><p className="eyebrow">DOCUMENTAÇÃO DA OPERAÇÃO</p><h1>Arquitetura</h1><p className="muted">Infraestrutura, agentes e integrações do atendimento Getnet.</p></div>
      <a className="button secondary" href={`${diagramUrl}?download=1`} download="arquitetura-getnet.png"><Download size={16} />Baixar diagrama</a>
    </div>
    <div className={styles.context}><ShieldCheck size={18} /><p><strong>Ambiente demonstrativo.</strong> Topologia documentada, sem monitoramento de disponibilidade em tempo real. Dados de conta simulados.</p></div>
    <div className={styles.tabs} role="tablist" aria-label="Seções da arquitetura" onKeyDown={navigateTabs}>
      {tabs.map(item => <button key={item.key} id={`architecture-tab-${item.key}`} role="tab" aria-selected={tab === item.key} aria-controls={`architecture-panel-${item.key}`} tabIndex={tab === item.key ? 0 : -1} onClick={() => setTab(item.key)}><item.icon size={17} />{item.label}</button>)}
    </div>
    <div role="tabpanel" id={`architecture-panel-${tab}`} aria-labelledby={`architecture-tab-${tab}`} tabIndex={0} className={styles.panel}>
      {tab === "fluxo" && <>
        <section aria-labelledby="diagram-heading">
          <div className="section-heading"><div><h2 id="diagram-heading">Da pergunta à resposta</h2><p className="small muted">Vercel · Railway · dados e provedores externos</p></div><button className="icon-button bordered" title="Ampliar diagrama" aria-label="Ampliar diagrama" disabled={!imageLoaded || imageError} onClick={() => { setZoom(100); setExpanded(true); }}><Maximize2 size={18} /></button></div>
          <figure className={styles.diagram}>
            {imageError ? <div className={styles.imageMessage}><ErrorNotice message="Não foi possível carregar o diagrama. Sua sessão ou o serviço pode estar indisponível." /><button className="button secondary" onClick={retryImage}><RefreshCw size={16} />Tentar novamente</button></div> : <>
              {!imageLoaded && <div className={styles.imageMessage} role="status"><Spinner /><span>Carregando diagrama...</span></div>}
              <Image key={revision} src={imageUrl} alt={diagramAlt} width={3200} height={2000} unoptimized onLoad={() => setImageLoaded(true)} onError={() => setImageError(true)} className={styles.image} />
            </>}
          </figure>
          <p className={styles.caption}>Implantação prevista: portal na Vercel; API e banco no Railway. A resposta retorna pelo portal, sem acesso direto do navegador aos provedores de IA.</p>
        </section>
        <section className={styles.section} aria-labelledby="flow-heading"><h2 id="flow-heading">Percurso de uma mensagem</h2><ol className={styles.steps}>{steps.map(([title, description]) => <li key={title}><h3>{title}</h3><p>{description}</p></li>)}</ol></section>
      </>}
      {tab === "integracoes" && <>
        <section aria-labelledby="integrations-heading"><div className="section-heading"><h2 id="integrations-heading">Componentes e responsabilidades</h2></div><div className="table-scroll" tabIndex={0} role="region" aria-label="Tabela de integrações"><table className={styles.integrations}><thead><tr><th scope="col">Componente</th><th scope="col">Papel</th><th scope="col">Dados e limites</th></tr></thead><tbody>{integrations.map(item => <tr key={item.name}><th scope="row">{item.name}<span>{item.kind}</span></th><td>{item.role}</td><td>{item.data}</td></tr>)}</tbody></table></div></section>
        <section className={styles.section} aria-labelledby="sources-heading"><h2 id="sources-heading">De onde vêm as respostas?</h2><dl className={styles.facts}>
          <div><dt>Base de conhecimento (RAG)</dt><dd>Conteúdo curado de produtos é dividido em trechos e indexado no pgvector. A busca recupera os trechos mais próximos da pergunta para orientar a resposta; não treina um modelo novo nem copia todo o site automaticamente.</dd></div>
          <div><dt>Busca externa</dt><dd>Tavily entra para informações atuais ou como alternativa quando a base não traz contexto suficiente. Para produtos, usa domínios oficiais. A atualidade e a qualidade da resposta dependem das fontes; sem evidências, o agente deve informar a limitação.</dd></div>
          <div><dt>Consultas do cliente</dt><dd>As ferramentas devolvem fatos estruturados, e o modelo redige a resposta. A conta vem da sessão. A demonstração não efetua antecipações, pagamentos, estornos ou alterações cadastrais.</dd></div>
        </dl></section>
      </>}
      {tab === "seguranca" && <section aria-labelledby="security-heading"><div className="section-heading"><h2 id="security-heading">Controles e limitações atuais</h2></div><dl className={styles.facts}>{safeguards.map(([title, description]) => <div key={title}><dt>{title}</dt><dd>{description}</dd></div>)}</dl></section>}
    </div>
    {expanded && <Modal title="Diagrama da arquitetura" onClose={() => setExpanded(false)}>
      <div className={styles.viewerToolbar}><div className="row"><button className="icon-button bordered" title="Diminuir zoom" aria-label="Diminuir zoom" disabled={zoom <= 50} onClick={() => setZoom(value => Math.max(50, value - 25))}><Minus size={17} /></button><output className={styles.zoom} aria-live="polite">{zoom}%</output><button className="icon-button bordered" title="Aumentar zoom" aria-label="Aumentar zoom" disabled={zoom >= 150} onClick={() => setZoom(value => Math.min(150, value + 25))}><Plus size={17} /></button><button className="icon-button" title="Restaurar zoom" aria-label="Restaurar zoom" onClick={() => setZoom(100)}><RotateCcw size={17} /></button></div><a className="icon-button" href={diagramUrl} target="_blank" rel="noopener noreferrer" title="Abrir imagem original" aria-label="Abrir imagem original"><ExternalLink size={18} /></a></div>
      <div className={styles.viewer} tabIndex={0} role="region" aria-label="Diagrama ampliado"><Image src={imageUrl} alt={diagramAlt} width={3200} height={2000} unoptimized style={{ width: `${16 * zoom}px`, height: "auto" }} onError={() => { setExpanded(false); setImageError(true); }} /></div>
    </Modal>}
  </main>;
}