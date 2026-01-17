import { NextResponse } from "next/server";
import { generateBlogPost } from "@/lib/generate_blog";
import { fetchLatestTechNews, formatNewsForAI } from "@/lib/news";
import { saveGeneratedPost } from "@/lib/admin";

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

        // Save to Supabase using Admin Service
        try {
            const newPost = await saveGeneratedPost(postData);

            return NextResponse.json({
                success: true,
                topic_used: topic,
                post: newPost
            });
        } catch (dbError: any) {
            console.error("Database Error:", dbError);
            return NextResponse.json({ error: dbError.message }, { status: 500 });
        }

    } catch (error: any) {
        console.error("Route Error:", error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
