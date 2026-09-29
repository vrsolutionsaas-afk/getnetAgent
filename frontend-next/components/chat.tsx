"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUp, Check, Copy, CreditCard, ExternalLink, History, MessageSquare, Plus, ReceiptText, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, failure, number, type ChatReply, type Conversation, type Message, type Session } from "@/lib/api";
import { ErrorNotice, Spinner } from "./ui";

export default function Chat({ session, refreshSession }: { session: Session; refreshSession: () => Promise<void> }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const requestId = useRef(0);

  useEffect(() => { api<Conversation[]>("conversas").then(setConversations).catch(error => setError(failure(error))); }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [messages, pending]);

  async function open(conversation: Conversation) {
    const sequence = ++requestId.current;
    setSelected(conversation); setHistory(false); setLoading(true); setError(""); setDraft("");
    try { const data = await api<Message[]>(`conversas/${conversation.id}`); if (sequence === requestId.current) setMessages(data); }
    catch (error) { if (sequence === requestId.current) { setMessages([]); setError(failure(error)); } }
    finally { if (sequence === requestId.current) setLoading(false); }
  }
  function newConversation() { ++requestId.current; setSelected(null); setMessages([]); setDraft(""); setHistory(false); setError(""); setLoading(false); composer.current?.focus(); }
  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy || loading) return;
    setBusy(true); setError(""); setPending(text); setDraft("");
    try {
      const conversation = selected || await api<Conversation>("conversas", "POST");
      setSelected(conversation);
      const reply = await api<ChatReply>("mensagens", "POST", { message: text, conversa_id: conversation.id });
      setMessages(previous => [...previous,
        { id: Date.now(), papel: "user", texto: text, fontes: [], agente: "" },
        { id: Date.now() + 1, papel: "assistant", texto: reply.response, fontes: reply.sources, agente: reply.agent },
      ]);
      await api<Conversation[]>("conversas").then(setConversations).catch(error => setError(failure(error)));
    } catch (error) { setError(failure(error)); setDraft(text); }
    finally { setBusy(false); setPending(""); await refreshSession().catch(error => setError(failure(error))); composer.current?.focus(); }
  }
  const exhausted = session.consumo.input + session.consumo.reservado_input >= session.consumo.limite_input || session.consumo.output + session.consumo.reservado_output >= session.consumo.limite_output;
  return <main className="chat-page">
    <header className="chat-heading"><div><p className="eyebrow">CENTRAL GETNET</p><h1>{selected?.titulo === "Nova conversa" ? "Atendimento" : selected?.titulo || "Atendimento"}</h1></div><div className="row"><button className="button secondary" title="Histórico" aria-label="Histórico" disabled={busy} onClick={() => setHistory(!history)} aria-expanded={history}><History size={17} /><span>Histórico</span></button><button className="icon-button bordered" title="Nova conversa" aria-label="Nova conversa" onClick={newConversation} disabled={busy}><Plus size={21} /></button></div></header>
    {history && <section className="history-panel" aria-label="Conversas anteriores"><div className="row between"><h2>Suas conversas</h2><button className="icon-button" title="Fechar histórico" aria-label="Fechar histórico" onClick={() => setHistory(false)}><X size={18} /></button></div>{conversations.length ? conversations.map(conversation => <button key={conversation.id} className={`history-item ${selected?.id === conversation.id ? "selected" : ""}`} onClick={() => open(conversation)}><MessageSquare size={17} /><span>{conversation.titulo}</span></button>) : <p className="muted small empty-history">Nenhuma conversa por aqui ainda.</p>}</section>}
    <div className="chat-scroll" aria-busy={busy || loading}>
      {loading ? <div className="loading-state"><Spinner /></div> : !messages.length && !pending ? <div className="chat-welcome"><div className="welcome-symbol"><MessageSquare size={30} strokeWidth={1.6} /></div><p className="eyebrow">OLÁ, {session.usuario.nome.split(" ")[0].toUpperCase()}</p><h2>Como podemos<br />ajudar hoje?</h2><div className="suggestions">{[{ icon: CreditCard, title: "Minha maquininha", text: "Qual é a situação da minha maquininha?" }, { icon: ReceiptText, title: "Meus recebimentos", text: "Quais são minhas últimas liquidações?" }].map(item => <button key={item.title} onClick={() => { setDraft(item.text); composer.current?.focus(); }}><item.icon size={22} /><span>{item.title}</span><ArrowUp size={16} /></button>)}</div><span className="demo-note">Dados de conta simulados para demonstração.</span></div> : <div className="messages" aria-live="polite">{messages.map(message => <MessageItem key={message.id} message={message} />)}{pending && <><MessageItem message={{ id: -1, papel: "user", texto: pending, fontes: [], agente: "" }} /><div className="thinking"><Spinner /><span>Consultando informações...</span></div></>}<div ref={bottom} /></div>}
    </div>
    <div className="composer-area"><ErrorNotice message={error || (exhausted ? "Sua cota mensal está esgotada. Fale com o administrador." : "")} /><form onSubmit={send} className="composer"><textarea ref={composer} value={draft} onChange={event => setDraft(event.target.value)} placeholder="Escreva sua mensagem..." aria-label="Mensagem" maxLength={2500} rows={2} disabled={busy || exhausted || loading} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><div className="composer-bottom"><span>{number(draft.length)} / 2.500</span><button className="send-button" title="Enviar mensagem" aria-label="Enviar mensagem" disabled={!draft.trim() || busy || exhausted || loading}>{busy ? <Spinner /> : <ArrowUp size={21} />}</button></div></form><div className="composer-footer"><span>Respostas automáticas podem conter imprecisões.</span><span className="token-balance">{number(Math.max(0, session.consumo.limite_output - session.consumo.output - session.consumo.reservado_output))} tokens de saída disponíveis</span></div></div>
  </main>;
}

function MessageItem({ message }: { message: Message }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const customer = message.papel === "user";
  async function copy() {
    try { await navigator.clipboard.writeText(message.texto); setCopied(true); setCopyError(false); }
    catch { setCopyError(true); }
  }
  return <article className={`message ${customer ? "customer" : "assistant"}`}><div className="message-label">{customer ? "Você" : "Atendimento Getnet"}</div><div className="message-text"><ReactMarkdown components={{ a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> }}>{message.texto}</ReactMarkdown></div>{!customer && <div className="message-meta">{message.fontes.filter(url => /^https?:\/\//i.test(url)).map((url, index) => <a key={`${url}-${index}`} href={url} target="_blank" rel="noopener noreferrer" className="source-link"><ExternalLink size={13} />Fonte {index + 1}</a>)}<button className="icon-button" title={copied ? "Copiado" : "Copiar resposta"} aria-label={copied ? "Resposta copiada" : "Copiar resposta"} onClick={copy}>{copied ? <Check size={15} /> : <Copy size={15} />}</button>{copyError && <span className="small" role="status">Não foi possível copiar.</span>}</div>}</article>;
}