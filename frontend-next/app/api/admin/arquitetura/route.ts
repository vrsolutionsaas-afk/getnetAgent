import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const privateHeaders = { "Cache-Control": "private, no-store", "Vary": "Cookie", "X-Content-Type-Options": "nosniff" };

export async function GET(request: NextRequest) {
  const token = request.cookies.get("getnet_session")?.value;
  if (!token) return NextResponse.json({ detail: "Entre para continuar." }, { status: 401, headers: privateHeaders });
  const apiUrl = process.env.GETNET_API_URL;
  if (!apiUrl) return NextResponse.json({ detail: "O endereço da API ainda não foi configurado." }, { status: 503, headers: privateHeaders });

  try {
    const sessionResponse = await fetch(`${apiUrl.replace(/\/$/, "")}/portal/sessao`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(15000),
    });
    if (sessionResponse.status === 401 || sessionResponse.status === 403) {
      return NextResponse.json({ detail: "Sessão inválida ou acesso não autorizado." }, { status: sessionResponse.status, headers: privateHeaders });
    }
    if (!sessionResponse.ok) throw new Error("Sessão indisponível");
    const session = await sessionResponse.json();
    if (session?.usuario?.perfil !== "admin" || session.usuario.ativo !== true) {
      return NextResponse.json({ detail: "Acesso exclusivo para administradores." }, { status: 403, headers: privateHeaders });
    }
    const image = await readFile(path.join(process.cwd(), "assets", "arquitetura-getnet.png"));
    return new NextResponse(new Uint8Array(image), { headers: {
      ...privateHeaders,
      "Content-Type": "image/png",
      "Content-Disposition": `${request.nextUrl.searchParams.get("download") === "1" ? "attachment" : "inline"}; filename="arquitetura-getnet.png"`,
    } });
  } catch {
    return NextResponse.json({ detail: "Não foi possível carregar o diagrama agora." }, { status: 502, headers: privateHeaders });
  }
}