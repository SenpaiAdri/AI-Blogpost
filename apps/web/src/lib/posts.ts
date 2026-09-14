import { cache } from "react";
import { unstable_cache } from "next/cache";
import { supabase } from "@/lib/supabase";
import { Comment, Post, PostRow, Tag } from "@/lib/types";

const POSTS_WITH_TAGS_SELECT = `
      *,
      post_tags (
        tags (
          *
        )
      )
    `;

// Lightweight feed select: only columns BlogCard actually renders
// (id, slug, title, tldr, published_at, source_url + tag id/name/slug).
// Skips heavy `content` / `excerpt` / `cover_image` / `ai_model` columns.
const POST_FEED_SELECT = `
      id,
      slug,
      title,
      tldr,
      published_at,
      source_url,
      post_tags (
        tags (
          id,
          name,
          slug
        )
      )
    `;

function mapRowsToPosts(rawPosts: PostRow[] | null): Post[] {
    return (rawPosts || []).map((post) => {
        const tags = post.post_tags?.map((pt) => pt.tags) || [];
        return {
            ...post,
            tags,
        };
    });
}

export async function getPosts(): Promise<Post[]> {
    const { data: rawPosts, error } = await supabase
        .from("posts")
        .select(POST_FEED_SELECT)
        .eq("is_published", true)
        .order("published_at", { ascending: false });

    if (error) {
        console.error("Error fetching posts:", error);
        return [];
    }

    return mapRowsToPosts(rawPosts as unknown as PostRow[]);
}

// Per-request dedupe: generateMetadata + TopicFilterBarSection +
// PostFeedSection (+ getPaginatedPosts internals) all look up the same
// slug within one homepage render — this collapses them to 1 DB hit.
export const getTagBySlug = cache(async (slug: string): Promise<Tag | null> => {
    if (!slug?.trim()) return null;
    const { data, error } = await supabase
        .from("tags")
        .select("id, name, slug")
        .eq("slug", slug.trim().toLowerCase())
        .maybeSingle();

    if (error || !data) {
        return null;
    }
    return data as Tag;
});

export async function getPostsByTagSlug(tagSlug: string): Promise<Post[]> {
    const tag = await getTagBySlug(tagSlug);
    if (!tag) {
        return [];
    }

    const { data: links, error: linkErr } = await supabase
        .from("post_tags")
        .select("post_id")
        .eq("tag_id", tag.id);

    if (linkErr || !links?.length) {
        return [];
    }

    const postIds = [...new Set(links.map((l) => l.post_id as string))];

    const { data: rawPosts, error } = await supabase
        .from("posts")
        .select(POST_FEED_SELECT)
        .in("id", postIds)
        .eq("is_published", true)
        .order("published_at", { ascending: false });

    if (error) {
        console.error("Error fetching posts by tag:", error);
        return [];
    }

    return mapRowsToPosts(rawPosts as unknown as PostRow[]);
}

export type TagWithCount = { tag: Tag; count: number };

/** Build tag frequency from already-loaded posts (no extra query). */
export function aggregateTagsWithCounts(posts: Post[]): TagWithCount[] {
    const map = new Map<string, TagWithCount>();

    for (const post of posts) {
        for (const t of post.tags || []) {
            const key = String(t.id);
            const cur = map.get(key);
            if (cur) {
                cur.count += 1;
            } else {
                map.set(key, { tag: t, count: 1 });
            }
        }
    }

    return Array.from(map.values()).sort(
        (a, b) =>
            b.count - a.count || a.tag.name.localeCompare(b.tag.name)
    );
}

/** Tags that appear on at least one published post, sorted by popularity then name. */
async function fetchTagsWithPostCounts(): Promise<TagWithCount[]> {
    // Lightweight path: fetch tag rows + published-only link counts.
    // Never loads post bodies (the old implementation scanned the whole
    // posts table with SELECT * just to count tags).
    const { data: tagData, error } = await supabase
        .from("tags")
        .select("id, name, slug")
        .order("name");

    if (error || !tagData) {
        console.error("Error fetching tags:", error);
        return [];
    }

    const tags = tagData as unknown as Tag[];
    const tagIds = tags.map((t) => t.id);
    if (tagIds.length === 0) {
        return [];
    }

    const { data: linkData, error: linkErr } = await supabase
        .from("post_tags")
        .select("tag_id, posts!inner(id)")
        .in("tag_id", tagIds)
        .eq("posts.is_published", true);

    if (linkErr) {
        console.error("Error fetching tag counts:", linkErr);
        return [];
    }

    const countMap = new Map<string, number>();
    for (const link of linkData || []) {
        const tagId = String(link.tag_id);
        countMap.set(tagId, (countMap.get(tagId) || 0) + 1);
    }

    return tags
        .map((tag) => ({
            tag,
            count: countMap.get(String(tag.id)) || 0,
        }))
        .filter((t) => t.count > 0)
        .sort((a, b) => b.count - a.count || a.tag.name.localeCompare(b.tag.name));
}

// Cross-request cache (free, no Redis): topics change only on ingest
// (2x daily), so a 10-min TTL is safe and collapses every homepage
// regeneration + topics page hit into one shared entry.
export const getTagsWithPostCounts = unstable_cache(
    fetchTagsWithPostCounts,
    ["tags-with-post-counts"],
    { revalidate: 600, tags: ["tags"] }
);

export async function getPostBySlug(slug: string): Promise<Post | null> {
    const { data: postData, error } = await supabase
        .from("posts")
        .select(POSTS_WITH_TAGS_SELECT)
        .eq("slug", slug)
        .single();

    if (error || !postData) {
        return null;
    }

    // Transform raw data
    const rawPost = postData as unknown as PostRow;
    const tags = rawPost.post_tags?.map((pt) => pt.tags) || [];

    return {
        ...rawPost,
        tags
    };
}

export async function getAllPostSlugs(): Promise<{ slug: string }[]> {
    const { data: posts } = await supabase.from("posts").select("slug");
    return posts?.map(({ slug }) => ({ slug })) || [];
}

// Top-level approved comments only (parent_id IS NULL): v1 rows are AI notes,
// later this same feed mixes in top-level human comments with no query change.
const COMMENT_SELECT = "id, post_id, author_type, author_name, body, ai_model, created_at";

async function fetchApprovedComments(postId: string): Promise<Comment[]> {
    if (!postId?.trim()) return [];

    const { data, error } = await supabase
        .from("comments")
        .select(COMMENT_SELECT)
        .eq("post_id", postId)
        .eq("status", "approved")
        .is("parent_id", null)
        .order("created_at", { ascending: true });

    if (error) {
        console.error("Error fetching comments:", error);
        return [];
    }

    return (data || []) as Comment[];
}

// Cross-request cache (10-min TTL matches ISR revalidate): comments change
// only when the scheduled worker runs (2-3x weekly), so this is safe.
export const getApprovedComments = unstable_cache(
    fetchApprovedComments,
    ["approved-comments"],
    { revalidate: 600, tags: ["comments"] }
);

async function fetchPaginatedPosts(
    offset: number,
    limit: number,
    tagSlug?: string
): Promise<{ posts: Post[]; hasMore: boolean }> {
    const safeOffset = Math.max(0, offset || 0);
    const safeLimit = Math.min(Math.max(1, limit || 10), 50);

    let query = supabase
        .from("posts")
        .select(POST_FEED_SELECT)
        .eq("is_published", true)
        .order("published_at", { ascending: false })
        // Fetch one extra row so we can answer hasMore without a count query.
        .range(safeOffset, safeOffset + safeLimit);

    if (tagSlug) {
        const tag = await getTagBySlug(tagSlug);
        if (!tag) {
            return { posts: [], hasMore: false };
        }

        const { data: links, error: linkErr } = await supabase
            .from("post_tags")
            .select("post_id")
            .eq("tag_id", tag.id);

        if (linkErr || !links?.length) {
            if (linkErr) {
                console.error("Error fetching post links by tag:", linkErr);
            }
            return { posts: [], hasMore: false };
        }

        query = query.in("id", [...new Set(links.map((l) => l.post_id as string))]);
    }

    const { data: rawPosts, error } = await query;

    if (error) {
        console.error("Error fetching paginated posts:", error);
        return { posts: [], hasMore: false };
    }

    const rows = (rawPosts || []) as unknown as PostRow[];
    return {
        posts: mapRowsToPosts(rows.slice(0, safeLimit)),
        hasMore: rows.length > safeLimit,
    };
}

// Cross-request cache keyed by (offset, limit, tagSlug). First page
// (homepage SSR) is the hot entry; deeper scroll pages get cached too
// as users reach them. 10-min TTL matches ingest cadence (2x daily).
export const getPaginatedPosts = unstable_cache(
    fetchPaginatedPosts,
    ["paginated-posts"],
    { revalidate: 600, tags: ["posts"] }
);

export async function getPaginatedTags(
    offset: number,
    limit: number
): Promise<{ tags: TagWithCount[]; hasMore: boolean }> {
    const safeOffset = Math.max(0, offset || 0);
    const safeLimit = Math.min(Math.max(1, limit || 10), 50);

    // Reuses the cached full tag list — no extra DB hit on cache hit.
    const tagsWithCounts = await getTagsWithPostCounts();

    const paginated = tagsWithCounts.slice(safeOffset, safeOffset + safeLimit + 1);
    const hasMore = paginated.length > safeLimit;

    return {
        tags: paginated.slice(0, safeLimit),
        hasMore,
    };
}
