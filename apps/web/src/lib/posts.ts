import { supabase } from "@/lib/supabase";
import { Post, PostRow, Tag } from "@/lib/types";

const POSTS_WITH_TAGS_SELECT = `
      *,
      post_tags (
        tags (
          *
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
        .select(POSTS_WITH_TAGS_SELECT)
        .eq("is_published", true)
        .order("published_at", { ascending: false });

    if (error) {
        console.error("Error fetching posts:", error);
        return [];
    }

    return mapRowsToPosts(rawPosts as unknown as PostRow[]);
}

export async function getTagBySlug(slug: string): Promise<Tag | null> {
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
}

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
        .select(POSTS_WITH_TAGS_SELECT)
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
export async function getTagsWithPostCounts(): Promise<TagWithCount[]> {
    return aggregateTagsWithCounts(await getPosts());
}

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

export async function getPaginatedPosts(
    offset: number,
    limit: number,
    tagSlug?: string
): Promise<{ posts: Post[]; hasMore: boolean }> {
    const safeOffset = Math.max(0, offset || 0);
    const safeLimit = Math.min(Math.max(1, limit || 10), 50);

    let query = supabase
        .from("posts")
        .select(POSTS_WITH_TAGS_SELECT)
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
