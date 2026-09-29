"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Image from "next/image";
import { ArrowDown, ArrowUp, ArrowUpRight, BookOpen, Check, ChevronRight, Coins, Copy, CreditCard, ExternalLink, Globe, Headset, History, MessageSquare, Plus, ReceiptText, RotateCcw, Search, ShieldCheck, Wallet } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, failure, number, type ChatReply, type Conversation, type Message, type Session } from "@/lib/api";
import { ErrorNotice, Modal, Spinner } from "./ui";
import styles from "./chat.module.css";

const suggestions = [
  { icon: CreditCard, title: "Minha maquininha", detail: "Conexão e funcionamento", text: "Minha maquininha não conecta. Pode verificar?" },
  { icon: ReceiptText, title: "Meus recebimentos", detail: "Vendas e prazos", text: "Quando vou receber o dinheiro das minhas vendas?" },
  { icon: Coins, title: "Antecipação", detail: "Valores disponíveis", text: "Posso antecipar meus recebíveis?" },
  { icon: Wallet, title: "Produtos Getnet", detail: "Maquininhas, Pix e pagamentos", text: "Qual a diferença entre a Get Clássica e a Get Smart?" },
];

function conversationDate(value?: string) {
  if (!value || Number.isNaN(Date.parse(value))) return "Nova conversa";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

function searchable(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
}

export default function Chat({ session, refreshSession }: { session: Session; refreshSession: () => Promise<void> }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [query, setQuery] = useState("");
  const [failedLoad, setFailedLoad] = useState(false);
  const [showLatest, setShowLatest] = useState(false);
  const [error, setError] = useState("");
  const scrollArea = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const sending = useRef(false);
  const composer = useRef<HTMLTextAreaElement>(null);
  const requestId = useRef(0);
  const listRequestId = useRef(0);
  const active = useRef(true);

  useEffect(() => {
    active.current = true;
    const sequence = ++listRequestId.current;
    api<Conversation[]>("conversas").then(data => { if (active.current && sequence === listRequestId.current) setConversations(data); })
      .catch(error => { if (active.current && sequence === listRequestId.current) setHistoryError(failure(error)); })
      .finally(() => { if (active.current && sequence === listRequestId.current) setHistoryLoading(false); });
    return () => { active.current = false; };
  }, []);
  useEffect(() => {
    if (followLatest.current && !loading) scrollArea.current?.scrollTo({ top: scrollArea.current.scrollHeight });
  }, [messages, pending, loading]);
  useEffect(() => {
    const field = composer.current;
    if (!field) return;
    field.style.height = "0px";
    field.style.height = `${Math.min(150, Math.max(48, field.scrollHeight))}px`;
  }, [draft]);

  async function loadHistory() {
    const sequence = ++listRequestId.current;
    setHistoryLoading(true); setHistoryError("");
    try {
      const data = await api<Conversation[]>("conversas");
      if (active.current && sequence === listRequestId.current) setConversations(data);
    } catch (error) { if (active.current && sequence === listRequestId.current) setHistoryError(failure(error)); }
    finally { if (active.current && sequence === listRequestId.current) setHistoryLoading(false); }
  }

  async function open(conversation: Conversation) {
    if (sending.current) return;
    const sequence = ++requestId.current;
    followLatest.current = true;
    setSelected(conversation); setHistory(false); setLoading(true); setFailedLoad(false); setError(""); setDraft(""); setMessages([]); setShowLatest(false);
    try { const data = await api<Message[]>(`conversas/${conversation.id}`); if (active.current && sequence === requestId.current) setMessages(data); }
    catch (error) { if (active.current && sequence === requestId.current) { setFailedLoad(true); setError(failure(error)); } }
    finally { if (active.current && sequence === requestId.current) setLoading(false); }
  }
  function newConversation() {
    if (sending.current) return;
    ++requestId.current; followLatest.current = true;
    setSelected(null); setMessages([]); setDraft(""); setHistory(false); setError(""); setLoading(false); setFailedLoad(false); setShowLatest(false);
    composer.current?.focus();
  }
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || text.length > 2500 || sending.current || loading || exhausted || failedLoad) return;
    sending.current = true; followLatest.current = true;
    const sequence = ++requestId.current;
    setBusy(true); setError(""); setPending(text); setDraft("");
    try {
      const conversation = selected || await api<Conversation>("conversas", "POST");
      if (!active.current || sequence !== requestId.current) return;
      setSelected(conversation);
      const reply = await api<ChatReply>("mensagens", "POST", { message: text, conversa_id: conversation.id });
      if (!active.current || sequence !== requestId.current) return;
      setMessages(previous => [...previous,
        { id: Date.now(), papel: "user", texto: text, fontes: [], agente: "" },
        { id: Date.now() + 1, papel: "assistant", texto: reply.response, fontes: reply.sources, agente: reply.agent },
      ]);
      setPending("");
      setSelected({ ...conversation, titulo: conversation.titulo === "Nova conversa" ? text.slice(0, 80) : conversation.titulo });
      await loadHistory();
    } catch (error) { if (active.current && sequence === requestId.current) { setError(failure(error)); setDraft(text); } }
    finally {
      sending.current = false;
      if (active.current && sequence === requestId.current) {
        setBusy(false); setPending("");
        await refreshSession().catch(error => setError(failure(error)));
        composer.current?.focus({ preventScroll: true });
      }
    }
  }
  const exhausted = session.consumo.input + session.consumo.reservado_input >= session.consumo.limite_input || session.consumo.output + session.consumo.reservado_output >= session.consumo.limite_output;
  const remaining = Math.max(0, session.consumo.limite_output - session.consumo.output - session.consumo.reservado_output);
  const filtered = conversations.filter(conversation => searchable(conversation.titulo).includes(searchable(query.trim())));
  const unavailable = busy || exhausted || loading || failedLoad;
  return <main className={styles.page}>
    <header className={styles.heading}>
      <div className={styles.headingIdentity}><span className={styles.brandMark}><Headset size={23} strokeWidth={1.7} /></span><div><p className={styles.eyebrow}>ATENDIMENTO GETNET</p><h1 title={selected?.titulo}>{selected?.titulo === "Nova conversa" ? "Nova conversa" : selected?.titulo || "Sua central de atendimento"}</h1><span className={styles.subtitle}>Assistente virtual</span></div></div>
      <div className={styles.headerActions}><button className="icon-button bordered" title="Histórico de conversas" aria-label="Histórico de conversas" disabled={busy} onClick={() => setHistory(!history)} aria-expanded={history}><History size={19} /></button><button className="icon-button bordered" title="Nova conversa" aria-label="Nova conversa" onClick={newConversation} disabled={busy}><Plus size={21} /></button></div>
    </header>
    {history && <Modal title="Suas conversas" onClose={() => setHistory(false)}>
      <label className={styles.historySearch}><span className="sr-only">Buscar conversa</span><Search size={17} /><input type="search" placeholder="Buscar conversa" value={query} onChange={event => setQuery(event.target.value)} /></label>
      <ErrorNotice message={historyError} />
      {historyError && <button className="button secondary" onClick={loadHistory} disabled={historyLoading}><RotateCcw size={15} />Tentar novamente</button>}
      <div className={styles.historyList} aria-busy={historyLoading}>
        {historyLoading ? <div className={styles.empty}><Spinner /><p>Carregando conversas</p></div> : filtered.length ? filtered.map(conversation => <button key={conversation.id} className={`${styles.historyItem} ${selected?.id === conversation.id ? styles.selected : ""}`} aria-current={selected?.id === conversation.id ? "true" : undefined} onClick={() => open(conversation)}><MessageSquare size={18} /><span><strong>{conversation.titulo}</strong><small>{conversationDate(conversation.criado_em)}</small></span><ChevronRight size={16} /></button>) : !historyError && <div className={styles.empty}><MessageSquare size={26} strokeWidth={1.5} /><p>{query ? "Nenhuma conversa encontrada." : "Você ainda não tem conversas."}</p></div>}
      </div>
      <div className={styles.historyFooter}><span>{number(filtered.length)} {filtered.length === 1 ? "conversa" : "conversas"}</span><button className="button secondary" onClick={newConversation}><Plus size={16} />Nova conversa</button></div>
    </Modal>}
    <div className={styles.conversationSurface}>
      <div ref={scrollArea} className={styles.scroll} aria-busy={loading} onScroll={event => {
        const area = event.currentTarget;
        const nearBottom = area.scrollHeight - area.scrollTop - area.clientHeight < 100;
        followLatest.current = nearBottom; setShowLatest(!nearBottom);
      }}>
        {loading ? <div className={styles.empty} role="status"><Spinner /><p>Carregando conversa</p></div> : failedLoad ? <div className={styles.empty}><MessageSquare size={28} /><p>Não foi possível carregar esta conversa.</p><button className="button secondary" onClick={() => selected && open(selected)}><RotateCcw size={16} />Tentar novamente</button></div> : !messages.length && !pending ? <section className={styles.welcome} aria-label="Novo atendimento">
          <div className={styles.welcomeIntro}><div><p className={styles.welcomeGreeting}>Olá, {session.usuario.nome.trim().split(/\s+/)[0]}.</p><h2>O que você precisa<br />resolver hoje?</h2></div><Image className={styles.welcomeImage} src="/checkout.jpg" width={180} height={120} alt="Pagamento no balcão de uma loja" /></div>
          <div className={styles.suggestions}>{suggestions.map(item => <button key={item.title} disabled={exhausted} onClick={() => { setDraft(item.text); composer.current?.focus(); }}><span className={styles.suggestionIcon}><item.icon size={22} strokeWidth={1.6} /></span><span><strong>{item.title}</strong><small>{item.detail}</small></span><ArrowUpRight size={17} /></button>)}</div>
          <p className={styles.demoNote}><ShieldCheck size={14} />Ambiente demonstrativo · Dados de conta simulados</p>
        </section> : <div className={styles.messages} role="log" aria-label="Mensagens da conversa" aria-live="polite" aria-relevant="additions">
          <div className={styles.conversationDate}><span>{conversationDate(selected?.criado_em)}</span></div>
          {messages.map(message => <MessageItem key={message.id} message={message} />)}
          {pending && <><MessageItem message={{ id: -1, papel: "user", texto: pending, fontes: [], agente: "" }} /><div className={styles.thinking} role="status"><span className={styles.messageAvatar}><Headset size={17} /></span><div><strong>Getnet</strong><span><Spinner />Preparando resposta</span></div></div></>}
        </div>}
      </div>
      {showLatest && messages.length > 0 && <button className={`icon-button bordered ${styles.jumpButton}`} title="Ir para a última mensagem" aria-label="Ir para a última mensagem" onClick={() => { followLatest.current = true; scrollArea.current?.scrollTo({ top: scrollArea.current.scrollHeight }); }}><ArrowDown size={19} /></button>}
    </div>
    <div className={styles.composerArea}>
      <ErrorNotice message={error || (exhausted ? "Sua cota mensal está esgotada. Fale com o administrador." : "")} />
      <form onSubmit={send} className={`${styles.composer} ${unavailable ? styles.composerDisabled : ""}`}>
        <textarea ref={composer} value={draft} onChange={event => setDraft(event.target.value)} placeholder={exhausted ? "Cota mensal esgotada" : "Escreva sua mensagem para a Getnet..."} aria-label="Mensagem" maxLength={2500} rows={2} disabled={unavailable} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} />
        <div className={styles.composerBottom}><span className={styles.privacy}><ShieldCheck size={13} />Não compartilhe senhas ou dados de cartão.</span><div><span className={styles.counter} aria-label={`${draft.length} de 2500 caracteres`}>{number(draft.length)} / 2.500</span><button type="submit" className={styles.sendButton} title="Enviar mensagem" aria-label="Enviar mensagem" disabled={!draft.trim() || unavailable}>{busy ? <Spinner /> : <ArrowUp size={21} />}</button></div></div>
      </form>
      <div className={styles.composerFooter}><span>Respostas automáticas podem conter imprecisões.</span><span>Saída disponível: <strong>{number(remaining)}</strong> tokens</span></div>
    </div>
  </main>;
}

function MessageItem({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const customer = message.papel === "user";
  const sources = [...new Set(message.fontes)].flatMap(value => {
    try {
      const url = new URL(value);
      return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password
        ? [{ url: url.href, domain: url.hostname.replace(/^www\./, "") }] : [];
    } catch { return []; }
  });
  useEffect(() => {
    if (!copied) return;
    const timeout = setTimeout(() => setCopied(false), 2500);
    return () => clearTimeout(timeout);
  }, [copied]);
  async function copy() {
    try { await navigator.clipboard.writeText(message.texto); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  return <article className={`${styles.message} ${customer ? styles.customer : styles.assistant}`} aria-label={customer ? "Sua mensagem" : "Resposta Getnet"}>
    <div className={styles.messageIdentity}>{!customer && <span className={styles.messageAvatar}><Headset size={17} /></span>}<strong>{customer ? "Você" : "Getnet"}</strong>{!customer && <span>Assistente virtual</span>}</div>
    <div className={styles.messageBody}>{customer ? <p className={styles.customerText}>{message.texto}</p> : <ReactMarkdown components={{ a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}<ExternalLink size={12} aria-hidden="true" /></a> }}>{message.texto}</ReactMarkdown>}</div>
    {!customer && <>
      {message.agente === "support" && <p className={styles.messageContext}><ShieldCheck size={13} /> Consulta com dados demonstrativos</p>}
      <div className={styles.messageFooter}>
        {sources.length > 0 && <details className={styles.sources}><summary><BookOpen size={15} /><span>{sources.length} {sources.length === 1 ? "fonte consultada" : "fontes consultadas"}</span></summary><ul>{sources.map(source => <li key={source.url}><a href={source.url} target="_blank" rel="noopener noreferrer" title={source.url}><Globe size={14} /><span>{source.domain}</span><ExternalLink size={13} /></a></li>)}</ul></details>}
        <button className={`icon-button ${styles.copyButton}`} title={copied ? "Copiado" : "Copiar resposta"} aria-label={copied ? "Resposta copiada" : "Copiar resposta"} onClick={copy}>{copied ? <Check size={16} /> : <Copy size={16} />}</button>
        <span className={copyError ? styles.copyError : "sr-only"} role="status">{copyError ? "Não foi possível copiar." : copied ? "Resposta copiada." : ""}</span>
      </div>
    </>}
  </article>;
}