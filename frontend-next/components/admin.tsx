"use client";

import { useEffect, useState, type FormEvent } from "react";
import { ArrowDownLeft, ArrowUpRight, Check, Download, Gauge, Pencil, Plus, RefreshCw, Search, Timer, Zap } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, failure, number, type Dashboard, type Quota, type User } from "@/lib/api";
import { ErrorNotice, Modal, QuotaBars, Spinner } from "./ui";

export default function Admin({ view }: { view: string }) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [days, setDays] = useState(30);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<User | "new" | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([api<Dashboard>(`admin/painel?dias=${days}`), api<User[]>("admin/usuarios")])
      .then(([data, clients]) => { if (active) { setDashboard(data); setUsers(clients); setError(""); } })
      .catch(error => { if (active) setError(failure(error)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [days, revision]);

  function refresh() { setLoading(true); setRevision(value => value + 1); }
  const title = view === "usuarios" ? "Clientes" : view === "cotas" ? "Cotas globais" : "Visão geral";
  const filtered = users.filter(user => `${user.nome} ${user.email}`.toLowerCase().includes(search.toLowerCase()));
  return <main className="content">
    <div className="page-heading"><div><p className="eyebrow">GESTÃO DO ATENDIMENTO</p><h1>{title}</h1><p className="muted">{view === "painel" ? "Consumo e atividade da operação." : view === "usuarios" ? `${users.filter(user => user.perfil === "cliente").length} clientes cadastrados` : "Orçamento mensal de tokens da operação."}</p></div><div className="heading-actions"><button className="icon-button bordered" title="Atualizar dados" aria-label="Atualizar dados" disabled={loading} onClick={refresh}>{loading ? <Spinner /> : <RefreshCw size={17} />}</button>{view === "painel" && <button className="button secondary" disabled={!dashboard?.recentes.length || loading} title="Exportar últimas 30 chamadas do período" onClick={() => dashboard && exportCalls(dashboard)}><Download size={16} />Exportar CSV</button>}{view === "usuarios" && <button className="button primary" onClick={() => setEditing("new")}><Plus size={18} />Novo cliente</button>}</div></div>
    <ErrorNotice message={error} />
    {loading ? <div className="loading-state"><Spinner /><span>Carregando dados...</span></div> : dashboard && <>
      {view === "painel" && <>
        <div className="period-bar"><span className="row small muted"><span className="live-dot" />{dashboard.clientes_ativos} clientes ativos</span><div className="segmented" aria-label="Período do relatório">{[7, 30, 90].map(period => <button key={period} aria-pressed={days === period} className={days === period ? "selected" : ""} onClick={() => { setDays(period); setLoading(true); }}>{period} dias</button>)}</div></div>
        <div className="metrics">{[
          { label: "Tokens de entrada", value: number(dashboard.input), detail: `${number(dashboard.cache)} em cache`, icon: ArrowDownLeft, tone: "input" },
          { label: "Tokens de saída", value: number(dashboard.output), detail: "Respostas dos modelos", icon: ArrowUpRight, tone: "output" },
          { label: "Chamadas aos modelos", value: number(dashboard.chamadas), detail: "Roteamento + geração", icon: Zap, tone: "" },
          { label: "Latência média", value: `${(dashboard.latencia_ms / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} s`, detail: "Por chamada ao modelo", icon: Timer, tone: "" },
        ].map(metric => <section key={metric.label} className={`metric ${metric.tone}`}><div className="row between"><span>{metric.label}</span><metric.icon size={18} /></div><strong>{metric.value}</strong><small>{metric.detail}</small></section>)}</div>
        <div className="analytics-grid"><section className="chart-section"><div className="section-heading"><div><h2>Consumo ao longo do tempo</h2><p className="small muted">Tokens por dia · UTC</p></div><div className="chart-legend"><span><i className="input-dot" />Entrada</span><span><i className="output-dot" />Saída</span></div></div><div className="chart-container">{dashboard.diario.length ? <ResponsiveContainer width="100%" height="100%"><AreaChart data={dashboard.diario} margin={{ top: 16, right: 8, left: 0, bottom: 0 }} accessibilityLayer><CartesianGrid vertical={false} stroke="#eceeef" /><XAxis dataKey="dia" tickFormatter={value => `${String(value).slice(8, 10)}/${String(value).slice(5, 7)}`} axisLine={false} tickLine={false} tick={{ fill: "#747978", fontSize: 11 }} minTickGap={26} /><YAxis tickFormatter={value => new Intl.NumberFormat("pt-BR", { notation: "compact" }).format(Number(value))} axisLine={false} tickLine={false} width={50} tick={{ fill: "#747978", fontSize: 11 }} /><Tooltip formatter={(value, name) => [number(Number(value)), name === "input" ? "Entrada" : "Saída"]} labelFormatter={label => String(label)} contentStyle={{ borderRadius: 6, border: "1px solid #e5e7e6", fontSize: 12 }} /><Area type="monotone" dataKey="input" stroke="#d82836" fill="#d82836" fillOpacity={0.07} strokeWidth={2} dot={dashboard.diario.length === 1} isAnimationActive={false} /><Area type="monotone" dataKey="output" stroke="#168477" fill="#168477" fillOpacity={0.08} strokeWidth={2} dot={dashboard.diario.length === 1} isAnimationActive={false} /></AreaChart></ResponsiveContainer> : <div className="empty-state"><BarChartEmpty /><h3>Ainda sem consumo</h3><p>Não há chamadas registradas neste período.</p></div>}</div></section><section className="monthly-section"><div className="section-heading"><div><h2>Cota da operação</h2><p className="small muted">{dashboard.cotas.mes} · renovação mensal</p></div><Gauge size={19} /></div><QuotaBars quota={dashboard.cotas} /><span className="small muted">Reservas também comprometem o saldo disponível.</span></section></div>
        <section className="table-section"><div className="section-heading"><h2>Consumo por modelo</h2><span className="small muted">Últimos {days} dias</span></div><div className="table-scroll"><table><thead><tr><th>Modelo</th><th>Etapa</th><th className="numeric">Entrada</th><th className="numeric">Saída</th><th className="numeric">Chamadas</th></tr></thead><tbody>{dashboard.modelos.map(model => <tr key={`${model.modelo}-${model.etapa}`}><td className="mono model-name">{model.modelo}</td><td>{stageLabel(model.etapa)}</td><td className="numeric">{number(model.input)}</td><td className="numeric">{number(model.output)}</td><td className="numeric">{number(model.chamadas)}</td></tr>)}{!dashboard.modelos.length && <tr><td colSpan={5} className="empty-cell">Nenhum modelo utilizado no período.</td></tr>}</tbody></table></div></section>
        <section className="table-section"><div className="section-heading"><h2>Atividade recente</h2><span className="small muted">Até 30 chamadas</span></div><div className="table-scroll"><table><thead><tr><th>Cliente</th><th>Modelo / etapa</th><th className="numeric">Entrada</th><th className="numeric">Saída</th><th>Apuração</th><th>Data · UTC</th></tr></thead><tbody>{dashboard.recentes.map(call => <tr key={call.id}><td title={`Trace: ${call.trace_id}`}>{call.cliente}</td><td><span className="mono model-name">{call.modelo}</span><small className="cell-subtitle">{stageLabel(call.etapa)}</small></td><td className="numeric">{number(call.input)}</td><td className="numeric">{number(call.output)}</td><td><span className={`status ${call.status === "confirmado" ? "success" : "warning"}`}>{statusLabel(call.status)}</span></td><td className="small muted">{new Date(call.criado_em.endsWith("Z") || /[+-]\d\d:\d\d$/.test(call.criado_em) ? call.criado_em : `${call.criado_em}Z`).toLocaleString("pt-BR", { timeZone: "UTC", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</td></tr>)}{!dashboard.recentes.length && <tr><td colSpan={6} className="empty-cell">Nenhuma atividade registrada.</td></tr>}</tbody></table></div></section>
        <p className="scope-note">Tokens dos modelos de conversa. Embeddings e buscas web não incluídos. Cache faz parte dos tokens de entrada.</p>
      </>}
      {view === "usuarios" && <section className="table-section clients-section"><div className="client-toolbar"><div className="search-field"><Search size={18} /><input type="search" aria-label="Buscar cliente" placeholder="Buscar por nome ou e-mail" value={search} onChange={event => setSearch(event.target.value)} /></div><span className="small muted">{filtered.length} registros</span></div><div className="table-scroll"><table><thead><tr><th>Cliente</th><th>Perfil</th><th>Entrada / limite mensal</th><th>Saída / limite mensal</th><th>Acesso</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{filtered.map(user => <tr key={user.id}><td><strong>{user.nome}</strong><small className="cell-subtitle">{user.email}</small></td><td>{user.perfil === "admin" ? "Admin" : "Cliente"}</td><td className="mono small">{number(user.consumo?.input || 0)} <span className="muted">/ {number(user.limite_input)}</span></td><td className="mono small">{number(user.consumo?.output || 0)} <span className="muted">/ {number(user.limite_output)}</span></td><td><span className={`status ${user.ativo ? "success" : "inactive"}`}>{user.ativo ? "Ativo" : "Bloqueado"}</span></td><td><button className="icon-button" title={`Editar ${user.nome}`} aria-label={`Editar ${user.nome}`} onClick={() => setEditing(user)}><Pencil size={16} /></button></td></tr>)}{!filtered.length && <tr><td colSpan={6} className="empty-cell">Nenhum cliente encontrado.</td></tr>}</tbody></table></div></section>}
      {view === "cotas" && <GlobalQuotas quota={dashboard.cotas} onSaved={refresh} />}
    </>}
    {editing && <UserForm user={editing === "new" ? undefined : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); refresh(); }} />}
  </main>;
}

function BarChartEmpty() { return <div className="empty-chart-symbol"><span /><span /><span /><span /><span /></div>; }
function stageLabel(stage: string) { return stage === "roteamento" ? "Roteamento" : stage === "geracao" ? "Geração" : stage; }
function statusLabel(status: string) { return status === "confirmado" ? "Confirmado" : status === "reservado" ? "Reservado" : "Estimado após falha"; }

function LimitFields({ input, output }: { input: number; output: number }) {
  return <div className="form-columns"><label>Entrada · tokens / mês<input name="limite_input" type="number" min={0} max={2000000000} step={1} defaultValue={input} required /></label><label>Saída · tokens / mês<input name="limite_output" type="number" min={0} max={2000000000} step={1} defaultValue={output} required /></label></div>;
}

function GlobalQuotas({ quota, onSaved }: { quota: Quota; onSaved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true); setError("");
    try { await api("admin/cotas", "PUT", { limite_input: Number(data.get("limite_input")), limite_output: Number(data.get("limite_output")) }); onSaved(); }
    catch (error) { setError(failure(error)); }
    finally { setBusy(false); }
  }
  return <div className="quota-settings"><section><h2>Limites mensais</h2><p className="muted settings-description">Válidos para todos os clientes, além dos limites individuais.</p><form onSubmit={submit} className="form-stack"><LimitFields input={quota.limite_input} output={quota.limite_output} /><div className="notice neutral"><Gauge size={18} /><span>Cota zero bloqueia novas chamadas. Alterações não apagam o consumo já registrado.</span></div><ErrorNotice message={error} /><div><button className="button primary" disabled={busy}>{busy ? <Spinner /> : <Check size={17} />}Salvar limites</button></div></form></section><section className="quota-current"><h2>Utilização neste mês</h2><p className="small muted">{quota.mes} · UTC</p><QuotaBars quota={quota} /></section></div>;
}

function UserForm({ user, onClose, onSaved }: { user?: User; onClose: () => void; onSaved: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const limits = { limite_input: Number(data.get("limite_input")), limite_output: Number(data.get("limite_output")) };
    setBusy(true); setError("");
    try {
      if (user) await api(`admin/usuarios/${user.id}`, "PATCH", { ...limits, ativo: data.get("ativo") === "on" });
      else await api("admin/usuarios", "POST", { ...limits, nome: data.get("nome"), email: data.get("email"), senha: data.get("senha"), cliente_id: data.get("cliente_id") });
      onSaved();
    } catch (error) { setError(failure(error)); }
    finally { setBusy(false); }
  }
  return <Modal title={user ? "Editar acesso e cotas" : "Novo cliente"} onClose={() => { if (!busy) onClose(); }}><form onSubmit={submit} className="form-stack">{user ? <div className="edit-identity"><strong>{user.nome}</strong><p className="muted small">{user.email}</p></div> : <><label>Nome<input name="nome" required minLength={2} maxLength={120} autoComplete="name" autoFocus /></label><label>E-mail<input name="email" type="email" required maxLength={254} autoComplete="email" /></label><label>Senha inicial<input name="senha" type="password" required minLength={12} maxLength={128} autoComplete="new-password" placeholder="Mínimo de 12 caracteres" /></label><label>Conta de demonstração<select name="cliente_id"><option value="cliente1988">Maria · cliente1988</option><option value="cliente2025">João · cliente2025</option></select></label></>}<LimitFields input={user?.limite_input ?? 200000} output={user?.limite_output ?? 50000} />{user && <label className="checkbox-label"><input type="checkbox" name="ativo" defaultChecked={user.ativo} />Acesso ativo</label>}<ErrorNotice message={error} /><div className="modal-actions"><button type="button" className="button secondary" disabled={busy} onClick={onClose}>Cancelar</button><button className="button primary" disabled={busy}>{busy ? <Spinner /> : <Check size={17} />}{user ? "Salvar alterações" : "Criar cliente"}</button></div></form></Modal>;
}

function exportCalls(dashboard: Dashboard) {
  const cell = (value: unknown) => `"${String(value).replace(/^[=+@-]/, "'$&").replace(/"/g, '""')}"`;
  const lines = [["Cliente", "Modelo", "Etapa", "Entrada", "Saída", "Apuração", "Trace", "Data UTC"], ...dashboard.recentes.map(call => [call.cliente, call.modelo, call.etapa, call.input, call.output, statusLabel(call.status), call.trace_id, call.criado_em])];
  const url = URL.createObjectURL(new Blob(["\uFEFF", lines.map(row => row.map(cell).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a"); link.href = url; link.download = "getnet-chamadas-recentes.csv"; link.click(); URL.revokeObjectURL(url);
}