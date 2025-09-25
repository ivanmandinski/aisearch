"""
WordPress content fetcher and processor.
"""
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import logging
from config import settings

logger = logging.getLogger(__name__)


class WordPressContentFetcher:
    """Fetches and processes content from WordPress REST API."""
    
    def __init__(self):
        self.base_url = settings.wordpress_api_url
        self.auth = (settings.wordpress_username, settings.wordpress_password)
        self.client = httpx.AsyncClient(
            auth=self.auth,
            timeout=30.0,
            headers={"User-Agent": "HybridSearchBot/1.0"}
        )
    
    async def fetch_all_posts(self) -> List[Dict[str, Any]]:
        """Fetch all published posts from WordPress."""
        posts = []
        page = 1
        per_page = 100
        
        while True:
            try:
                response = await self.client.get(
                    f"{self.base_url}/posts",
                    params={
                        "per_page": per_page,
                        "page": page,
                        "status": "publish",
                        "_embed": True
                    }
                )
                response.raise_for_status()
                
                batch_posts = response.json()
                if not batch_posts:
                    break
                    
                posts.extend(batch_posts)
                page += 1
                
                logger.info(f"Fetched {len(batch_posts)} posts from page {page-1}")
                
            except httpx.HTTPError as e:
                logger.error(f"Error fetching posts: {e}")
                break
        
        logger.info(f"Total posts fetched: {len(posts)}")
        return posts
    
    async def fetch_all_pages(self) -> List[Dict[str, Any]]:
        """Fetch all published pages from WordPress."""
        pages = []
        page = 1
        per_page = 100
        
        while True:
            try:
                response = await self.client.get(
                    f"{self.base_url}/pages",
                    params={
                        "per_page": per_page,
                        "page": page,
                        "status": "publish",
                        "_embed": True
                    }
                )
                response.raise_for_status()
                
                batch_pages = response.json()
                if not batch_pages:
                    break
                    
                pages.extend(batch_pages)
                page += 1
                
                logger.info(f"Fetched {len(batch_pages)} pages from page {page-1}")
                
            except httpx.HTTPError as e:
                logger.error(f"Error fetching pages: {e}")
                break
        
        logger.info(f"Total pages fetched: {len(pages)}")
        return pages
    
    def clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract text."""
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def process_content_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single WordPress content item."""
        # Extract basic information
        processed = {
            "id": item["id"],
            "title": item["title"]["rendered"],
            "slug": item["slug"],
            "type": item["type"],
            "url": item["link"],
            "date": item["date"],
            "modified": item["modified"],
            "author": item.get("_embedded", {}).get("author", [{}])[0].get("name", "Unknown"),
            "categories": [],
            "tags": [],
            "excerpt": "",
            "content": "",
            "word_count": 0
        }
        
        # Clean and extract content
        raw_content = item["content"]["rendered"]
        processed["content"] = self.clean_html_content(raw_content)
        processed["word_count"] = len(processed["content"].split())
        
        # Extract excerpt
        if item.get("excerpt", {}).get("rendered"):
            processed["excerpt"] = self.clean_html_content(item["excerpt"]["rendered"])
        
        # Extract categories
        if "_embedded" in item and "wp:term" in item["_embedded"]:
            for term_group in item["_embedded"]["wp:term"]:
                for term in term_group:
                    if term["taxonomy"] == "category":
                        processed["categories"].append({
                            "id": term["id"],
                            "name": term["name"],
                            "slug": term["slug"]
                        })
                    elif term["taxonomy"] == "post_tag":
                        processed["tags"].append({
                            "id": term["id"],
                            "name": term["name"],
                            "slug": term["slug"]
                        })
        
        return processed
    
    async def get_all_content(self) -> List[Dict[str, Any]]:
        """Fetch and process all WordPress content."""
        logger.info("Starting content fetch from WordPress...")
        
        # Fetch posts and pages concurrently
        posts_task = self.fetch_all_posts()
        pages_task = self.fetch_all_pages()
        
        posts, pages = await asyncio.gather(posts_task, pages_task)
        
        # Process all content
        all_content = []
        
        for post in posts:
            processed_post = self.process_content_item(post)
            all_content.append(processed_post)
        
        for page in pages:
            processed_page = self.process_content_item(page)
            all_content.append(processed_page)
        
        logger.info(f"Processed {len(all_content)} content items")
        return all_content
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
