import { NextRequest, NextResponse } from "next/server";
import { getPaginatedPosts, getTagBySlug } from "@/lib/posts";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const offset = Number.parseInt(searchParams.get("offset") || "0", 10);
  const limit = Number.parseInt(searchParams.get("limit") || "10", 10);
  const rawTag = (searchParams.get("tag") || "").trim().toLowerCase();

  const safeOffset = Number.isFinite(offset) ? Math.max(0, offset) : 0;
  const safeLimit = Number.isFinite(limit) ? Math.min(Math.max(1, limit), 50) : 10;

  let tagSlug: string | undefined;
  if (rawTag) {
    const tag = await getTagBySlug(rawTag);
    tagSlug = tag?.slug;
  }

  const result = await getPaginatedPosts(safeOffset, safeLimit, tagSlug);
  return NextResponse.json(result);
}
