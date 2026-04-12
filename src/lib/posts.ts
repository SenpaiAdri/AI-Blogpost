import { supabase } from "@/lib/supabase";
import { Post, PostRow, Tag } from "@/lib/types";

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
        .select(`
      *,
      post_tags (
        tags (
          *
        )
      )
    `)
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
        .select(
            `
      *,
      post_tags (
        tags (
          *
        )
      )
    `
        )
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
        .select(`
      *,
      post_tags (
        tags (
          *
        )
      )
    `)
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
