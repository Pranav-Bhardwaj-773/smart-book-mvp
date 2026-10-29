import { NextRequest, NextResponse } from "next/server";

function backendOrigin(): string | null {
  const raw = (
    process.env.BACKEND_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    ""
  ).trim();
  if (!raw) return null;
  const origin = raw.replace(/\/$/, "");
  if (/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?(\/|$)/i.test(origin)) {
    return null;
  }
  return origin;
}

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
]);

async function proxyRequest(
  req: NextRequest,
  pathSegments: string[],
): Promise<NextResponse> {
  const origin = backendOrigin();
  if (!origin) {
    return NextResponse.json(
      {
        detail:
          "Set BACKEND_URL on Vercel to your public API URL (e.g. https://smart-book-mvp.onrender.com).",
      },
      { status: 503 },
    );
  }

  const path = pathSegments.join("/");
  const target = `${origin}/${path}${req.nextUrl.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    headers.set(key, value);
  });

  let body: ArrayBuffer | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Could not reach the book API. Check BACKEND_URL on Vercel." },
      { status: 502 },
    );
  }

  const outHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    outHeaders.set(key, value);
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(req, path);
}

export async function POST(req: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(req, path);
}

export async function PATCH(req: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(req, path);
}

export async function PUT(req: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(req, path);
}

export async function DELETE(req: NextRequest, ctx: RouteContext) {
  const { path } = await ctx.params;
  return proxyRequest(req, path);
}
