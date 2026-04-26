import requests
from typing import Optional
from bs4 import BeautifulSoup

from logger import get_logger
from rate_limit import wait_for_url

logger = get_logger("scraper")


def fetch_with_jina(url: str) -> Optional[str]:
    """Fetch article content using Jina Reader API."""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        wait_for_url(jina_url)
        response = requests.get(jina_url, timeout=30)
        
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        logger.warning(f"Jina fetch error for {url}: {e}")
        return None


def fetch_with_bs4(url: str) -> Optional[str]:
    """Fallback: Fetch article content using BeautifulSoup."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        wait_for_url(url)
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "lxml")
            
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            
            main = soup.find("main") or soup.find("article") or soup.find("div", class_=lambda x: x and "content" in x.lower())
            
            if main:
                text = main.get_text(separator="\n", strip=True)
                return text[:10000]
            
            return soup.get_text(separator="\n", strip=True)[:10000]
        return None
    except Exception as e:
        logger.warning(f"BS4 fetch error for {url}: {e}")
        return None


def scrape_article(url: str) -> Optional[str]:
    """Scrape article content with Jina as primary, BS4 as fallback."""
    content = fetch_with_jina(url)
    
    if content and len(content) > 100:
        return content
    
    logger.debug(f"Jina failed, trying BS4 for {url}")
    return fetch_with_bs4(url)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        test_url = "https://openai.com/blog/gpt-4"
    content = scrape_article(test_url)
    if content:
        logger.info(f"Fetched {len(content)} characters")
        logger.debug(content[:500])