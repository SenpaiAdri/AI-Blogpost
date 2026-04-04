import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_supabase_client, get_all_existing_urls
from ingest import get_latest_news, NewsItem
from scraper import scrape_article
from generator import generate_blog_post, generate_mock_post


def format_context_for_ai(item: NewsItem, article_content: str = "") -> str:
    """Format news item and article content for AI context."""
    context = f"""Source: {item.source}
Title: {item.title}
Link: {item.link}
Date: {item.pub_date.isoformat()}
"""
    if article_content:
        context += f"\nArticle Content:\n{article_content[:5000]}"
    else:
        context += f"\nSnippet: {item.snippet[:1000]}"
    
    return context


def save_post(client, post_data: dict) -> bool:
    """Save generated post to database."""
    try:
        tag_ids = []
        
        if post_data.get("tags"):
            for tag_name in post_data["tags"]:
                slug = tag_name.lower().replace(" ", "-").replace("[^a-z0-9-]", "")
                
                tag_response = client.from_("tags").upsert(
                    {"name": tag_name, "slug": slug},
                    on_conflict="slug"
                ).select().execute()
                
                if tag_response.data:
                    tag_ids.append(tag_response.data[0]["id"])
        
        post_response = client.from_("posts").insert({
            "title": post_data["title"],
            "slug": post_data["slug"],
            "content": post_data.get("content", ""),
            "excerpt": post_data.get("excerpt", ""),
            "tldr": post_data.get("tldr", []),
            "source_url": post_data.get("source_url", []),
            "ai_model": "gemini-2.0-flash-lite",
            "is_published": True,
            "published_at": datetime.now().isoformat(),
            "cover_image": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e"
        }).execute()
        
        if not post_response.data:
            print("Failed to insert post")
            return False
        
        post_id = post_response.data[0]["id"]
        
        if tag_ids:
            post_tags = [{"post_id": post_id, "tag_id": tid} for tid in tag_ids]
            client.from_("post_tags").insert(post_tags).execute()
        
        return True
        
    except Exception as e:
        print(f"Error saving post: {e}")
        return False


def process_news_item(client, item: NewsItem, existing_urls: set) -> bool:
    """Process a single news item: check duplicate, scrape, generate, save."""
    if item.link in existing_urls:
        print(f"  Skipping duplicate: {item.link}")
        return False
    
    print(f"  Processing: {item.title[:50]}...")
    
    print(f"    Scraping article content...")
    article_content = scrape_article(item.link)
    
    context = format_context_for_ai(item, article_content)
    
    print(f"    Generating blog post...")
    post_data = generate_blog_post(
        topic=item.title,
        article_content=context,
        source_name=item.source,
        source_url=item.link
    )
    
    if not post_data:
        print(f"    AI failed, using mock fallback...")
        post_data = generate_mock_post(item.title, item.source, item.link)
    
    print(f"    Saving to database...")
    success = save_post(client, post_data)
    
    if success:
        print(f"    ✓ Saved: {post_data['title'][:40]}")
    else:
        print(f"    ✗ Failed to save")
    
    return success


def main():
    """Main ingestion pipeline."""
    print("=" * 60)
    print("AI Blog Post Ingestion Pipeline")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    print("\n[1/4] Connecting to Supabase...")
    client = get_supabase_client()
    print("    Connected")
    
    print("\n[2/4] Fetching latest AI news...")
    news_items = get_latest_news(limit=5)
    print(f"    Found {len(news_items)} AI news items")
    
    if not news_items:
        print("    No news found. Exiting.")
        return
    
    for i, item in enumerate(news_items, 1):
        print(f"    {i}. [{item.source}] {item.title[:40]}...")
    
    print("\n[3/4] Checking for duplicates...")
    existing_urls = get_all_existing_urls(client)
    print(f"    Found {len(existing_urls)} existing URLs in database")
    
    print("\n[4/4] Processing news items...")
    success_count = 0
    
    for item in news_items:
        try:
            if process_news_item(client, item, existing_urls):
                success_count += 1
                time.sleep(2)
        except Exception as e:
            print(f"    Error processing {item.title}: {e}")
            continue
    
    print("\n" + "=" * 60)
    print(f"Pipeline Complete!")
    print(f"  Processed: {len(news_items)} items")
    print(f"  New posts: {success_count}")
    print(f"  Skipped: {len(news_items) - success_count} (duplicates)")
    print(f"Finished at: {datetime.now().isoformat()}")
    print("=" * 60)


if __name__ == "__main__":
    main()