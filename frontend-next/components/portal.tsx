"use client";

import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, BarChart3, Eye, EyeOff, Gauge, LogOut, Menu, MessageSquare, ShieldCheck, Users, Workflow, X } from "lucide-react";
import { api, ApiError, failure, type Session } from "@/lib/api";
import { Brand, ErrorNotice, QuotaBars, Spinner } from "./ui";
import Chat from "./chat";
import Admin from "./admin";
import Architecture from "./architecture";

export default function Portal() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [view, setView] = useState("inicio");
  const [menu, setMenu] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    let active = true;
    api<Session>("sessao").then(data => { if (active) setSession(data); }).catch(error => {
      if (active && !(error instanceof ApiError && error.status === 401)) setError(failure(error));
    }).finally(() => { if (active) setLoading(false); });
    const expire = () => { setSession(null); setView("inicio"); setMenu(false); };
    window.addEventListener("session-expired", expire);
    return () => { active = false; window.removeEventListener("session-expired", expire); };
  }, []);

  async function refreshSession() { setSession(await api<Session>("sessao")); }
  async function logout() {
    setLoggingOut(true);
    try { await api("logout", "POST"); setSession(null); setView("inicio"); setMenu(false); setError(""); }
    catch (error) { setError(failure(error)); }
    finally { setLoggingOut(false); }
  }

  if (loading) return <main className="boot"><Brand /><Spinner /></main>;
  if (!session) return <Login initialError={error} onLogin={data => { setSession(data); setError(""); }} />;

  const admin = session.usuario.perfil === "admin";
  const current = view === "inicio" ? (admin ? "painel" : "chat") : view;
  const nav = [
    ...(admin ? [{ key: "painel", label: "Visão geral", icon: BarChart3 }, { key: "usuarios", label: "Clientes", icon: Users }, { key: "cotas", label: "Cotas globais", icon: Gauge }, { key: "arquitetura", label: "Arquitetura", icon: Workflow }] : []),
    { key: "chat", label: "Atendimento", icon: MessageSquare },
    { key: "minhas-cotas", label: "Meu consumo", icon: Gauge },
  ];
  return <div className={`shell ${menu ? "menu-open" : ""}`}>
    {menu && <button className="nav-scrim" aria-label="Fechar navegação" onClick={() => setMenu(false)} />}
    <aside className="sidebar">
      <div className="sidebar-brand"><Brand /><button className="icon-button mobile-only" aria-label="Fechar menu" onClick={() => setMenu(false)}><X size={20} /></button></div>
      <div className="workspace-label">CENTRAL DE ATENDIMENTO</div>
      <div className="workspace-name"><span className="workspace-symbol">G</span><div>Getnet <small>{admin ? "Administração" : "Área do cliente"}</small></div></div>
      <nav aria-label="Menu principal">{nav.map(item => <button key={item.key} className={`nav-item ${current === item.key ? "active" : ""}`} aria-current={current === item.key ? "page" : undefined} onClick={() => { setView(item.key); setMenu(false); setError(""); }}><item.icon size={19} />{item.label}</button>)}</nav>
      <div className="sidebar-bottom"><span className="demo-label"><ShieldCheck size={14} /> Ambiente demonstrativo</span><div className="identity"><span className="avatar">{session.usuario.nome.slice(0, 2).toUpperCase()}</span><div><strong>{session.usuario.nome}</strong><small>{session.usuario.email}</small></div><button className="icon-button" disabled={loggingOut} onClick={logout} title="Sair" aria-label="Sair">{loggingOut ? <Spinner /> : <LogOut size={18} />}</button></div></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div className="row"><button className="icon-button mobile-only" title="Menu" aria-label="Abrir menu" onClick={() => setMenu(true)}><Menu size={21} /></button><span>Portal Getnet</span><span className="breadcrumb">/</span><strong>{nav.find(item => item.key === current)?.label}</strong></div><span className="role-label">{admin ? "Administrador" : "Cliente"}</span></header>
      {error && <div className="workspace-error"><ErrorNotice message={error} /></div>}
      {current === "chat" ? <Chat session={session} refreshSession={refreshSession} /> : current === "minhas-cotas" ? <main className="content"><div className="page-heading"><div><p className="eyebrow">MINHA CONTA</p><h1>Meu consumo</h1><p className="muted">Período mensal · {session.consumo.mes} · UTC</p></div></div><section className="personal-quota"><h2>Tokens disponíveis</h2><QuotaBars quota={session.consumo} /><p className="small muted">Limites de entrada e saída independentes. Renovação no primeiro dia de cada mês.</p><button className="button secondary" onClick={() => refreshSession().catch(error => setError(failure(error)))}>Atualizar consumo</button></section></main> : admin ? (current === "arquitetura" ? <Architecture /> : <Admin key={current} view={current} />) : null}
    </div>
  </div>;
}

function Login({ initialError, onLogin }: { initialError: string; onLogin: (session: Session) => void }) {
  const [error, setError] = useState(initialError);
  const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      await api("login", "POST", { email: data.get("email"), senha: data.get("senha") });
      onLogin(await api<Session>("sessao"));
    } catch (error) { setError(failure(error)); }
    finally { setBusy(false); }
  }
  return <main className="login-page">
    <section className="login-visual" aria-label="Getnet"><div className="login-brand"><Brand /><span>Central de atendimento</span></div><div className="login-visual-caption"><span className="login-line" /><p>Seu negócio.<br />Sempre em movimento.</p></div><span className="login-visual-footer">Uma nova conversa começa aqui.</span></section>
    <section className="login-panel"><div className="login-form-wrap"><div className="login-mobile-brand"><Brand /></div><p className="eyebrow">PORTAL GETNET</p><h1>Bom ter você<br />por aqui.</h1><p className="login-subtitle">Entre na sua conta para continuar.</p><form onSubmit={submit} className="form-stack"><label>E-mail<input type="email" name="email" autoComplete="username" placeholder="voce@empresa.com.br" required maxLength={254} /></label><label>Senha<div className="password-field"><input name="senha" type={visible ? "text" : "password"} autoComplete="current-password" required maxLength={128} placeholder="Sua senha" /><button type="button" className="icon-button" aria-label={visible ? "Ocultar senha" : "Mostrar senha"} title={visible ? "Ocultar senha" : "Mostrar senha"} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button></div></label><ErrorNotice message={error} /><button className="button primary login-submit" disabled={busy}>{busy ? <Spinner /> : <>Entrar <ArrowRight size={19} /></>}</button></form><p className="login-help">Precisa de acesso? Fale com o administrador do portal.</p></div><footer className="login-footer"><ShieldCheck size={16} /><span>Projeto demonstrativo · Não é um canal oficial Getnet</span></footer></section>
  </main>;
}