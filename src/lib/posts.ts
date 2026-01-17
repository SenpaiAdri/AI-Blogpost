import { supabase } from "@/lib/supabase";
import { Post, PostRow, Tag } from "@/lib/types";

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

    // Transform raw data to Post interface
    return (rawPosts as unknown as PostRow[] || []).map((post) => {
        const tags = post.post_tags?.map((pt) => pt.tags) || [];
        return {
            ...post,
            tags
        };
    });
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
