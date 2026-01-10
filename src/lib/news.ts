import Parser from 'rss-parser';

// Define our reliable tech news sources
const RSS_FEEDS = [
    { name: 'The Verge', url: 'https://www.theverge.com/rss/index.xml' },
    { name: 'TechCrunch', url: 'https://techcrunch.com/feed/' },
    { name: 'Wired AI', url: 'https://www.wired.com/feed/tag/ai/latest/rss' },
    { name: 'OpenAI Blog', url: 'https://openai.com/blog/rss.xml' }, // Sometimes unreliable, but worth trying
    { name: 'MIT Tech Review', url: 'https://www.technologyreview.com/feed/' },
];

const parser = new Parser();

export interface NewsItem {
    title: string;
    link: string;
    snippet: string;
    source: string;
    pubDate: string;
}

export async function fetchLatestTechNews(): Promise<NewsItem[]> {
    const allNews: NewsItem[] = [];

    // Fetch all feeds in parallel
    const feedPromises = RSS_FEEDS.map(async (feed) => {
        try {
            const feedResult = await parser.parseURL(feed.url);

            // Get the top 5 items from each feed
            const items = feedResult.items.slice(0, 5).map(item => ({
                title: item.title || 'No Title',
                link: item.link || '',
                snippet: item.contentSnippet || item.content || '',
                source: feed.name,
                pubDate: item.pubDate || new Date().toISOString()
            }));

            return items;
        } catch (error) {
            console.warn(`Failed to fetch RSS from ${feed.name}:`, error);
            return [];
        }
    });

    const results = await Promise.all(feedPromises);

    // Flatten the array of arrays
    results.forEach(items => allNews.push(...items));

    // Sort by date
    allNews.sort((a, b) => new Date(b.pubDate).getTime() - new Date(a.pubDate).getTime());

    // Filter for AI-relevant keywords
    const aiKeywords = ['ai', 'artificial intelligence', 'gpt', 'llm', 'neural', 'robot', 'machine learning', 'nvidia', 'gemini', 'claude', 'openai'];

    const relevantNews = allNews.filter(item => {
        const text = (item.title + ' ' + item.snippet).toLowerCase();
        return aiKeywords.some(keyword => text.includes(keyword));
    });

    return relevantNews;
}

export function formatNewsForAI(newsItems: NewsItem[]): string {
    // Take top 5 most relevant news items to send to context
    const topNews = newsItems.slice(0, 5);

    return topNews.map((item, index) => `
    [Article ${index + 1}]
    Source: ${item.source}
    Title: ${item.title}
    Snippet: ${item.snippet.substring(0, 300)}...
    Link: ${item.link}
  `).join('\n\n');
}
