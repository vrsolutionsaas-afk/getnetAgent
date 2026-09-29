import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 180;

const cookieName = "getnet_session";
const permitted: Record<string, RegExp> = {
  GET: /^(sessao|conversas|conversas\/[a-zA-Z0-9_-]+|admin\/usuarios|admin\/painel)$/,
  POST: /^(login|logout|conversas|mensagens|admin\/usuarios)$/,
  PATCH: /^admin\/usuarios\/[a-zA-Z0-9_-]+$/,
  PUT: /^admin\/cotas$/,
};

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const path = (await context.params).path.join("/");
  if (!permitted[request.method]?.test(path)) {
    return NextResponse.json({ detail: "Operação não encontrada." }, { status: 404 });
  }
  if (request.method !== "GET") {
    const origin = process.env.PORTAL_ORIGIN || `${request.nextUrl.protocol}//${request.headers.get("host")}`;
    if (request.headers.get("origin") !== origin) {
      return NextResponse.json({ detail: "Origem não permitida." }, { status: 403 });
    }
    if (!request.headers.get("content-type")?.startsWith("application/json")) {
      return NextResponse.json({ detail: "Formato inválido." }, { status: 415 });
    }
  }

  const token = request.cookies.get(cookieName)?.value;
  if (path !== "login" && !token) {
    return NextResponse.json({ detail: "Entre para continuar." }, { status: 401 });
  }
  const apiUrl = process.env.GETNET_API_URL;
  if (!apiUrl) {
    return NextResponse.json({ detail: "O endereço da API ainda não foi configurado." }, { status: 503 });
  }

  try {
    const body = request.method === "GET" ? undefined : await request.text();
    if (body && Buffer.byteLength(body, "utf8") > 20000) {
      return NextResponse.json({ detail: "Requisição muito grande." }, { status: 413 });
    }
    const target = new URL(`${apiUrl.replace(/\/$/, "")}/portal/${path}`);
    if (path === "admin/painel") {
      target.searchParams.set("dias", request.nextUrl.searchParams.get("dias") || "30");
    }
    const upstream = await fetch(target, {
      method: request.method,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(165000),
    });
    const data = await upstream.json();
    if (path === "login" && upstream.ok) {
      const response = NextResponse.json({ usuario: data.usuario }, { headers: { "Cache-Control": "no-store" } });
      response.cookies.set(cookieName, data.token, {
        httpOnly: true, secure: process.env.NODE_ENV === "production",
        sameSite: "lax", path: "/", maxAge: 12 * 60 * 60,
      });
      return response;
    }
    const response = NextResponse.json(data, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
    if (path === "logout" || (upstream.status === 401 && path !== "login")) response.cookies.delete(cookieName);
    return response;
  } catch {
    return NextResponse.json({ detail: "Não foi possível conectar ao atendimento. Tente novamente." }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT };