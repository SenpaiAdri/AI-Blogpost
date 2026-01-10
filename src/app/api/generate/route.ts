import { NextResponse } from "next/server";
import { generateBlogPost } from "@/lib/generate_blog";
import { supabaseAdmin } from "@/lib/supabase";
import { fetchLatestTechNews, formatNewsForAI } from "@/lib/news";

export const maxDuration = 60;

export async function GET(request: Request) {
    try {
        // Fetch news
        const relevantNews = await fetchLatestTechNews();

        if (!relevantNews || relevantNews.length === 0) {
            return NextResponse.json({ error: "No relevant news found to generate from." }, { status: 404 });
        }

        // Prepare context
        const context = formatNewsForAI(relevantNews);

        // Pick the most recent/relevant story as main topic
        const mainStory = relevantNews[0];
        const topic = `${mainStory.title} (${mainStory.source})`;

        console.log(`Generating post for topic: ${topic}`);

        // Generate Content (Real AI or Smart Mock)
        const postData = await generateBlogPost(topic, context);

        if (!postData) {
            return NextResponse.json({ error: "Failed to generate content" }, { status: 500 });
        }

        // Save to Supabase (Tags + Post) using ADMIN client
        const tagIds = [];
        if (postData.tags && postData.tags.length > 0) {
            for (const tagName of postData.tags) {
                const slug = tagName.toLowerCase().replace(/[^a-z0-9]/g, "-");

                // Upsert tag
                const { data: tag } = await supabaseAdmin
                    .from("tags")
                    .upsert({ name: tagName, slug: slug }, { onConflict: "slug" })
                    .select()
                    .single();

                if (tag) tagIds.push(tag.id);
            }
        }

        // Insert Post using ADMIN client
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
            console.error("Supabase Insert Error:", postError);
            return NextResponse.json({ error: postError.message }, { status: 500 });
        }

        // Link Tags using ADMIN client
        if (newPost && tagIds.length > 0) {
            const postTags = tagIds.map(tagId => ({
                post_id: newPost.id,
                tag_id: tagId
            }));

            await supabaseAdmin.from("post_tags").insert(postTags);
        }

        return NextResponse.json({
            success: true,
            topic_used: topic,
            post: newPost
        });

    } catch (error: any) {
        console.error("Route Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
