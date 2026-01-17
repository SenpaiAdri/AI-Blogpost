import { supabaseAdmin } from "@/lib/supabase";

export interface GeneratedPostData {
    title: string;
    slug: string;
    content: string;
    excerpt: string;
    tldr: string[];
    tags: string[];
    source_url: { name: string; url: string }[];
}

/**
 * Saves a generated post to the database using the Admin client.
 * Handles upserting tags, inserting the post, and creating relationships.
 */
export async function saveGeneratedPost(postData: GeneratedPostData) {
    // Process Tags
    const tagIds: number[] = [];
    if (postData.tags && postData.tags.length > 0) {
        for (const tagName of postData.tags) {
            const slug = tagName.toLowerCase().replace(/[^a-z0-9]/g, "-");

            // Upsert tag
            const { data: tag, error: tagError } = await supabaseAdmin
                .from("tags")
                .upsert({ name: tagName, slug: slug }, { onConflict: "slug" })
                .select()
                .single();

            if (tagError) {
                console.error(`Error saving tag ${tagName}:`, tagError);
                continue;
            }

            if (tag) tagIds.push(tag.id);
        }
    }

    // Insert Post
    const { data: newPost, error: postError } = await supabaseAdmin
        .from("posts")
        .insert({
            title: postData.title,
            slug: postData.slug,
            content: postData.content,
            excerpt: postData.excerpt,
            tldr: postData.tldr,
            source_url: postData.source_url,
            ai_model: "gemini-2.0-flash-lite",
            is_published: true,
            published_at: new Date().toISOString(),
            cover_image: "https://images.unsplash.com/photo-1485827404703-89b55fcc595e" // Default robot image
        })
        .select()
        .single();

    if (postError) {
        throw new Error(`Supabase Insert Error: ${postError.message}`);
    }

    // Link Tags
    if (newPost && tagIds.length > 0) {
        const postTags = tagIds.map(tagId => ({
            post_id: newPost.id,
            tag_id: tagId
        }));

        const { error: linkError } = await supabaseAdmin.from("post_tags").insert(postTags);
        if (linkError) {
            console.error("Error linking tags:", linkError);
            // We don't throw here because the post was saved successfully
        }
    }

    return newPost;
}
