import { GoogleGenerativeAI } from "@google/generative-ai";

const apiKey = process.env.GOOGLE_API_KEY || "";
const genAI = new GoogleGenerativeAI(apiKey);

// AI model that we use
const model = genAI.getGenerativeModel({
  model: "gemini-2.0-flash-lite",
});

export async function generateBlogPost(topic: string, sourceContext: string) {
  const prompt = `
    You are an expert tech blogger for a site called "AI Blogpost".
    Your task is to write a high-quality, engaging blog post about the following topic: "${topic}".
    
    Use the following source material context to inform your post:
    ${sourceContext}

    Output Format: JSON
    The output must be a valid JSON object with the following schema:
    {
      "title": "Catchy Title",
      "slug": "kebab-case-slug",
      "tldr": ["Bullet point 1", "Bullet point 2", "Bullet point 3"],
      "content": "Full markdown content...",
      "excerpt": "Short teaser sentence...",
      "tags": ["Tag1", "Tag2"],
      "source_url": [{"name": "Source Name", "url": "https://source.url"}]
    }

    Guidelines:
    - Content should be in Markdown format.
    - Tone: Professional, enthusiastic, yet critical/technical.
    - No introductory text, just the JSON.
  `;

  try {
    const result = await model.generateContent(prompt);
    const response = await result.response;
    const text = response.text();

    // Clean up potential markdown code block formatting
    const jsonStr = text.replace(/```json/g, "").replace(/```/g, "").trim();

    return JSON.parse(jsonStr);
  } catch (error: any) {
    // if there is an error, log it and fall back to smart mock generation
    console.error("AI Generation Error (likely quota):", error.message);
    console.log("Falling back to smart mock generation...");

    // Extract a title from the context if possible
    const titleMatch = sourceContext.match(/Title: (.*)/);
    const sourceMatch = sourceContext.match(/Source: (.*)/);
    const linkMatch = sourceContext.match(/Link: (.*)/);

    const mockTitle = titleMatch ? titleMatch[1] : `AI Update: ${topic}`;
    const mockSource = sourceMatch ? sourceMatch[1] : "Tech News";
    const mockLink = linkMatch ? linkMatch[1] : "https://example.com";
    const cleanSlug = mockTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    const uniqueSlug = `${cleanSlug}-${Date.now()}`;

    return {
      title: mockTitle,
      slug: uniqueSlug,
      tldr: [
        "This is a simulated post because the AI quota was exceeded.",
        "It used the real RSS feed data to generate this title.",
        "Enable billing to get full AI generation."
      ],
      content: `
# ${mockTitle}

*(Note: This content is a placeholder because the AI API quota was hit. The title and source below are real, fetched from your RSS feed.)*

We are seeing significant developments in **${topic}**. Reports from **${mockSource}** indicate that this is a major shift in the industry.

## Why it matters
The implications of this announcement are far-reaching. Developers and enterprises alike are scrambling to understand what this means for their roadmaps.

## Key Takeaways
- Innovation is accelerating.
- Competitors are responding.
- The open-source community is watching closely.

[Read the full story on ${mockSource}](${mockLink})
          `,
      excerpt: `Latest update on ${topic} from ${mockSource}. Read more about the breaking news.`,
      tags: ["AI", "Tech News", "Mock Data"],
      source_url: [
        { name: mockSource, url: mockLink }
      ]
    };
  }
}
