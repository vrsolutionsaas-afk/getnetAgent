export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<Result>(path: string, method = "GET", body?: unknown): Promise<Result> {
  const response = await fetch(`/api/portal/${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(method !== "GET" ? { body: JSON.stringify(body ?? {}) } : {}),
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Confira os dados informados.";
    if (response.status === 401 && path !== "login") window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(detail, response.status);
  }
  return data as Result;
}

export type Quota = {
  mes: string; input: number; output: number; reservado_input: number; reservado_output: number;
  limite_input: number; limite_output: number;
};
export type User = {
  id: string; nome: string; email: string; perfil: "admin" | "cliente"; ativo: boolean;
  cliente_id: string; limite_input: number; limite_output: number; consumo?: Quota;
};
export type Session = { usuario: User; consumo: Quota };
export type Conversation = { id: string; titulo: string; criado_em?: string };
export type Message = { id: number; papel: "user" | "assistant"; texto: string; fontes: string[]; agente: string };
export type ChatReply = { response: string; sources: string[]; agent: string; escalated: boolean; trace_id: string };
export type Dashboard = {
  input: number; output: number; cache: number; chamadas: number; latencia_ms: number; clientes_ativos: number;
  cotas: Quota;
  diario: { dia: string; input: number; output: number }[];
  modelos: { modelo: string; etapa: string; input: number; output: number; chamadas: number }[];
  recentes: { id: string; cliente: string; modelo: string; etapa: string; input: number; output: number;
    status: string; trace_id: string; criado_em: string }[];
};

export const number = (value: number) => new Intl.NumberFormat("pt-BR").format(value);
export const failure = (error: unknown) => error instanceof Error ? error.message : "Algo deu errado. Tente novamente.";