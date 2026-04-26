import { NextRequest, NextResponse } from "next/server";

type Bucket = {
  count: number;
  resetAt: number;
};

function parsePositiveInt(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return Math.floor(parsed);
}

const WINDOW_MS = Math.max(parsePositiveInt(process.env.RATE_LIMIT_WINDOW_MS, 60_000), 1_000);
const MAX_REQUESTS = Math.max(parsePositiveInt(process.env.RATE_LIMIT_MAX_REQUESTS, 60), 1);

const RATE_LIMITED_PREFIXES = ["/api", "/blog"];

const globalState = globalThis as typeof globalThis & {
  __rateLimitBuckets?: Map<string, Bucket>;
};

const buckets = globalState.__rateLimitBuckets ?? new Map<string, Bucket>();
globalState.__rateLimitBuckets = buckets;

function getClientKey(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim();
    if (first) return first;
  }

  const realIp = request.headers.get("x-real-ip");
  if (realIp) return realIp.trim();

  return "unknown";
}

function shouldRateLimit(pathname: string): boolean {
  return RATE_LIMITED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  if (!shouldRateLimit(pathname)) {
    return NextResponse.next();
  }

  const now = Date.now();
  const key = `${getClientKey(request)}:${pathname}`;
  const existing = buckets.get(key);

  if (!existing || now > existing.resetAt) {
    buckets.set(key, { count: 1, resetAt: now + WINDOW_MS });
  } else {
    existing.count += 1;
    buckets.set(key, existing);
  }

  const current = buckets.get(key)!;
  const remaining = Math.max(MAX_REQUESTS - current.count, 0);

  if (current.count > MAX_REQUESTS) {
    return new NextResponse(
      JSON.stringify({ error: "Too many requests. Please try again later." }),
      {
        status: 429,
        headers: {
          "content-type": "application/json",
          "retry-after": String(Math.ceil((current.resetAt - now) / 1000)),
          "x-ratelimit-limit": String(MAX_REQUESTS),
          "x-ratelimit-remaining": "0",
          "x-ratelimit-reset": String(Math.floor(current.resetAt / 1000)),
        },
      }
    );
  }

  const response = NextResponse.next();
  response.headers.set("x-ratelimit-limit", String(MAX_REQUESTS));
  response.headers.set("x-ratelimit-remaining", String(remaining));
  response.headers.set("x-ratelimit-reset", String(Math.floor(current.resetAt / 1000)));
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)"],
};
