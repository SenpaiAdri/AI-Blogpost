import { NextRequest, NextResponse } from "next/server";
import { getPaginatedTags } from "@/lib/posts";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const offset = Number.parseInt(searchParams.get("offset") || "0", 10);
  const limit = Number.parseInt(searchParams.get("limit") || "50", 10);

  const safeOffset = Number.isFinite(offset) ? Math.max(0, offset) : 0;
  const safeLimit = Number.isFinite(limit) ? Math.min(Math.max(1, limit), 50) : 50;

  const result = await getPaginatedTags(safeOffset, safeLimit);
  return NextResponse.json(result);
}