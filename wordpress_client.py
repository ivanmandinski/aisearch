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
        # Only use auth if credentials are provided
        auth = None
        if settings.wordpress_username and settings.wordpress_password and \
           settings.wordpress_username != "your_wp_username" and \
           settings.wordpress_password != "your_wp_app_password":
            auth = (settings.wordpress_username, settings.wordpress_password)
        
        self.client = httpx.AsyncClient(
            auth=auth,
            timeout=30.0,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            ),
            headers={"User-Agent": "HybridSearchBot/1.0"},
            http2=False  # Disable HTTP/2 to avoid h2 dependency issues
        )
    
    async def fetch_all_posts(self) -> List[Dict[str, Any]]:
        """Fetch all published posts from WordPress."""
        posts = []
        page = 1
        per_page = 50  # Reduced batch size to avoid large responses
        
        while True:
            try:
                response = await self.client.get(
                    f"{self.base_url}/posts",
                    params={
                        "per_page": per_page,
                        "page": page,
                        "status": "publish",
                        "_embed": True  # Enable embedding to get featured media
                    }
                )
                response.raise_for_status()
                
                batch_posts = response.json()
                if not batch_posts:
                    break
                
                # Process posts one by one to handle errors gracefully
                for post in batch_posts:
                    try:
                        # Clean and validate post data
                        cleaned_post = self._clean_post_data(post)
                        if cleaned_post:
                            posts.append(cleaned_post)
                    except Exception as e:
                        logger.error(f"Error processing post {post.get('id', 'unknown')}: {e}")
                        continue
                
                page += 1
                logger.info(f"Fetched {len(batch_posts)} posts (page {page-1}), total: {len(posts)}")
                
                # Limit to prevent infinite loops
                if page > 50:  # Max 50 pages = 2500 posts
                    break
                
            except Exception as e:
                logger.error(f"Error fetching posts page {page}: {e}")
                break
        
        logger.info(f"Total posts fetched: {len(posts)}")
        return posts
    
    async def fetch_all_pages(self) -> List[Dict[str, Any]]:
        """Fetch all published pages from WordPress."""
        pages = []
        page = 1
        per_page = 50  # Reduced batch size
        
        while True:
            try:
                response = await self.client.get(
                    f"{self.base_url}/pages",
                    params={
                        "per_page": per_page,
                        "page": page,
                        "status": "publish",
                        "_embed": True  # Enable embedding to get featured media
                    }
                )
                response.raise_for_status()
                
                batch_pages = response.json()
                if not batch_pages:
                    break
                
                # Process pages one by one
                for page_item in batch_pages:
                    try:
                        cleaned_page = self._clean_post_data(page_item)
                        if cleaned_page:
                            pages.append(cleaned_page)
                    except Exception as e:
                        logger.error(f"Error processing page {page_item.get('id', 'unknown')}: {e}")
                        continue
                
                page += 1
                logger.info(f"Fetched {len(batch_pages)} pages (page {page-1}), total: {len(pages)}")
                
                # Limit to prevent infinite loops
                if page > 20:  # Max 20 pages = 1000 pages
                    break
                
            except Exception as e:
                logger.error(f"Error fetching pages page {page}: {e}")
                break
        
        logger.info(f"Total pages fetched: {len(pages)}")
        return pages
    
    def clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract text."""
        if not html_content:
            return ""
        
        try:
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
            
            # Limit text length to prevent issues
            if len(text) > 10000:
                text = text[:10000] + "..."
            
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning HTML content: {e}")
            # Return a safe fallback
            return "Content processing error"
    
    def process_content_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single WordPress content item."""
        try:
            logger.info(f"Processing item: {item.get('id', 'unknown')} - {item.get('title', {}).get('rendered', 'No title')}")
            logger.info(f"Available fields in item: {list(item.keys())}")
            logger.info(f"Featured media field: {item.get('featured_media')}")
            logger.info(f"Featured media type: {type(item.get('featured_media'))}")
            
            # Extract basic information with safe defaults
            processed = {
                "id": str(item.get("id", "")),
                "title": self._safe_get_text(item.get("title", {}), "rendered", ""),
                "slug": str(item.get("slug", "")),
                "type": str(item.get("type", "post")),
                "url": str(item.get("link", "")),
                "date": str(item.get("date", "")),
                "modified": str(item.get("modified", "")),
                "author": self._safe_get_author(item),
                "categories": [],
                "tags": [],
                "excerpt": "",
                "content": "",
                "word_count": 0
            }
            
            # Clean and extract content
            raw_content = self._safe_get_text(item.get("content", {}), "rendered", "")
            processed["content"] = self.clean_html_content(raw_content)
            processed["word_count"] = len(processed["content"].split())
            
            # Extract excerpt
            excerpt_raw = self._safe_get_text(item.get("excerpt", {}), "rendered", "")
            if excerpt_raw:
                processed["excerpt"] = self.clean_html_content(excerpt_raw)
            
            # Extract featured image
            featured_image = self._extract_featured_image(item)
            processed["featured_image"] = featured_image
            
            # Pass the featured_media ID for frontend URL construction
            featured_media_id = item.get("featured_media", 0)
            processed["featured_media"] = featured_media_id
            logger.info(f"Processed item {item.get('id', 'unknown')}: featured_media={featured_media_id}, type={type(featured_media_id)}")
            
            # If no featured image, try to extract from content
            if not featured_image:
                processed["featured_image"] = self._extract_image_from_content(raw_content)
            
            # Ensure we have a featured_image field even if empty
            if not processed.get("featured_image"):
                processed["featured_image"] = ""
            
            # Extract categories and tags safely
            try:
                if "_embedded" in item and "wp:term" in item["_embedded"]:
                    for term_group in item["_embedded"]["wp:term"]:
                        for term in term_group:
                            if term.get("taxonomy") == "category":
                                processed["categories"].append({
                                    "id": str(term.get("id", "")),
                                    "name": str(term.get("name", "")),
                                    "slug": str(term.get("slug", ""))
                                })
                            elif term.get("taxonomy") == "post_tag":
                                processed["tags"].append({
                                    "id": str(term.get("id", "")),
                                    "name": str(term.get("name", "")),
                                    "slug": str(term.get("slug", ""))
                                })
            except Exception as e:
                logger.error(f"Error processing categories/tags: {e}")
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing content item: {e}")
            # Return minimal safe structure
            return {
                "id": str(item.get("id", "unknown")),
                "title": "Processing Error",
                "slug": "",
                "type": "post",
                "url": "",
                "date": "",
                "modified": "",
                "author": "Unknown",
                "categories": [],
                "tags": [],
                "excerpt": "",
                "content": "Content processing error",
                "word_count": 0
            }
    
    def _extract_featured_image(self, item: Dict[str, Any]) -> str:
        """Extract featured image URL from WordPress item using multiple methods."""
        try:
            # Method 1: Check for featured_media field with embedded data
            featured_media_id = item.get("featured_media", 0)
            
            if featured_media_id and featured_media_id > 0:
                # Look for embedded media
                if "_embedded" in item and "wp:featuredmedia" in item["_embedded"]:
                    for media in item["_embedded"]["wp:featuredmedia"]:
                        if str(media.get("id", "")) == str(featured_media_id):
                            # Get the source URL from media details
                            media_details = media.get("media_details", {})
                            if media_details:
                                sizes = media_details.get("sizes", {})
                                
                                # Try different sizes in order of preference
                                for size_name in ["medium_large", "medium", "large", "full"]:
                                    if size_name in sizes:
                                        source_url = sizes[size_name].get("source_url", "")
                                        if source_url:
                                            return source_url
                                
                                # Fallback to any available size
                                for size_name, size_data in sizes.items():
                                    source_url = size_data.get("source_url", "")
                                    if source_url:
                                        return source_url
                            
                            # Direct source_url fallback
                            source_url = media.get("source_url", "")
                            if source_url:
                                return source_url
                
                # Method 2: Try to fetch media URL from WordPress REST API if we have base_url
                # This is a synchronous fallback - frontend will also try async fetch
                if hasattr(self, 'base_url') and self.base_url:
                    try:
                        import requests
                        media_url = f"{self.base_url}/wp-json/wp/v2/media/{featured_media_id}"
                        response = requests.get(media_url, timeout=2)
                        if response.status_code == 200:
                            media_data = response.json()
                            media_details = media_data.get("media_details", {})
                            if media_details:
                                sizes = media_details.get("sizes", {})
                                # Try different sizes in order of preference
                                for size_name in ["medium_large", "medium", "large", "full"]:
                                    if size_name in sizes:
                                        source_url = sizes[size_name].get("source_url", "")
                                        if source_url:
                                            logger.info(f"Fetched featured image from REST API: {source_url}")
                                            return source_url
                                # Fallback to any available size
                                for size_name, size_data in sizes.items():
                                    source_url = size_data.get("source_url", "")
                                    if source_url:
                                        logger.info(f"Fetched featured image from REST API (fallback): {source_url}")
                                        return source_url
                            # Direct source_url fallback
                            source_url = media_data.get("source_url", "")
                            if source_url:
                                logger.info(f"Fetched featured image from REST API (direct): {source_url}")
                                return source_url
                    except Exception as e:
                        logger.debug(f"Could not fetch media from REST API: {e}, frontend will fetch async")
                
                # Return empty string - frontend will fetch via REST API using media ID
                return ""
            
            # Method 3: Check for direct image fields in the item
            direct_image_fields = ['featured_image', 'thumbnail', 'image', 'featured_image_url', 'post_thumbnail']
            for field in direct_image_fields:
                if field in item and item[field]:
                    image_url = str(item[field]).strip()
                    if image_url and image_url != '0' and image_url != 'false':
                        return image_url
            
            # Method 4: Check for image in content
            content = self._safe_get_text(item.get("content", {}), "rendered", "")
            if content:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                img_tags = soup.find_all('img')
                if img_tags:
                    # Return the first image found
                    first_img = img_tags[0]
                    src = first_img.get('src', '')
                    if src and src.startswith('http'):
                        return src
            
            return ""
            
        except Exception as e:
            return ""
    
    def _extract_image_from_content(self, content: str) -> str:
        """Extract first image URL from content HTML."""
        try:
            if not content:
                return ""
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            img_tags = soup.find_all('img')
            
            if img_tags:
                for img in img_tags:
                    src = img.get('src', '')
                    if src and (src.startswith('http') or src.startswith('/')):
                        logger.info(f"Found image in content: {src}")
                        return src
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting image from content: {e}")
            return ""
    
    def _safe_get_text(self, obj: Dict, key: str, default: str = "") -> str:
        """Safely get text from nested dictionary."""
        try:
            value = obj.get(key, default)
            if isinstance(value, str):
                # Remove any problematic characters
                return value.replace('\x00', '').replace('\r', '').replace('\n', ' ')[:5000]
            return str(value)[:5000] if value else default
        except:
            return default
    
    def _safe_get_author(self, item: Dict) -> str:
        """Safely get author name."""
        try:
            embedded = item.get("_embedded", {})
            authors = embedded.get("author", [])
            if authors and len(authors) > 0:
                return str(authors[0].get("name", "Unknown"))
            return "Unknown"
        except:
            return "Unknown"
    
    def _clean_post_data(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate post data."""
        try:
            # Extract and clean basic fields
            cleaned = {
                "id": str(post.get("id", "")),
                "title": self._safe_get_text(post.get("title", {}), "rendered", ""),
                "slug": str(post.get("slug", "")),
                "type": str(post.get("type", "post")),
                "url": str(post.get("link", "")),
                "date": str(post.get("date", "")),
                "modified": str(post.get("modified", "")),
                "author": "SCS Engineers",  # Default author
                "categories": [],
                "tags": [],
                "excerpt": "",
                "content": "",
                "word_count": 0
            }
            
            # Clean content
            raw_content = self._safe_get_text(post.get("content", {}), "rendered", "")
            cleaned["content"] = self.clean_html_content(raw_content)
            cleaned["word_count"] = len(cleaned["content"].split())
            
            # Clean excerpt
            excerpt_raw = self._safe_get_text(post.get("excerpt", {}), "rendered", "")
            if excerpt_raw:
                cleaned["excerpt"] = self.clean_html_content(excerpt_raw)
            
            # Handle featured image with improved extraction
            featured_image_url = self._extract_featured_image(post)
            featured_media_id = post.get("featured_media", 0)
            
            if featured_image_url:
                cleaned["featured_image"] = featured_image_url
                cleaned["featured_image_url"] = featured_image_url
                cleaned["thumbnail"] = featured_image_url
                cleaned["featured_media"] = featured_media_id
            else:
                # Ensure featured_image field is always present
                cleaned["featured_image"] = ""
                cleaned["featured_image_url"] = ""
                cleaned["thumbnail"] = ""
                cleaned["featured_media"] = featured_media_id
            
            # Skip if content is too short or empty
            if len(cleaned["content"]) < 50:
                return None
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning post data: {e}")
            return None
    
    async def fetch_all_post_types(self, selected_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch all published content from all post types.
        
        Args:
            selected_types: Optional list of specific post types to fetch. If None, fetches all public types.
        """
        all_content = []
        
        try:
            # First, get all available post types
            types_response = await self.client.get(f"{self.base_url}/types")
            types_response.raise_for_status()
            types_data = types_response.json()
            
            # Filter to only post types that are available in REST API
            public_types = []
            type_info_map = {}  # Store type info for REST base lookup
            
            logger.info(f"Analyzing {len(types_data)} post types from WordPress API...")
            
            for post_type, info in types_data.items():
                logger.info(f"Checking post type '{post_type}': public={info.get('public')}, show_in_rest={info.get('show_in_rest')}, rest_base={info.get('rest_base')}")
                
                # Include if it has a rest_base (means it's available in REST API)
                # OR if it's public (we'll try to fetch it anyway)
                if info.get('rest_base') or info.get('show_in_rest'):
                    public_types.append(post_type)
                    type_info_map[post_type] = info
                    rest_base = info.get('rest_base', post_type)
                    logger.info(f"✅ INCLUDING post type: '{post_type}' with REST base: '{rest_base}'")
                else:
                    logger.info(f"⏭️  SKIPPING post type: '{post_type}' (no REST API support)")
            
            # Ensure posts and pages are always included (fallback)
            if 'post' not in public_types:
                public_types.append('post')
                type_info_map['post'] = {'rest_base': 'posts'}
                logger.warning("'post' type not found in types API, adding manually")
            if 'page' not in public_types:
                public_types.append('page')
                type_info_map['page'] = {'rest_base': 'pages'}
                logger.warning("'page' type not found in types API, adding manually")
            
            # Filter by selected types if provided
            if selected_types:
                logger.info(f"🎯 Filtering to selected post types: {selected_types}")
                # Only include post types that are in the selected list
                filtered_types = [pt for pt in public_types if pt in selected_types]
                logger.info(f"✅ Post types after filtering: {filtered_types}")
                public_types = filtered_types
            
            if not public_types:
                logger.warning("No post types to index after filtering!")
                return all_content
            
            logger.info(f"✨ FINAL POST TYPES TO INDEX: {public_types}")
            logger.info(f"📊 Total post types to fetch: {len(public_types)}")
            
            # Fetch content from each post type
            for post_type in public_types:
                try:
                    page = 1
                    per_page = 50
                    post_type_count = 0  # Track count per post type
                    
                    logger.info(f"Starting to fetch '{post_type}' items...")
                    
                    while True:
                        # Get the correct REST base for this post type
                        rest_base = type_info_map.get(post_type, {}).get('rest_base', post_type)
                        endpoint = f"{self.base_url}/{rest_base}"
                        
                        logger.info(f"Fetching '{post_type}' (page {page}) from endpoint: {endpoint}")
                        
                        try:
                            response = await self.client.get(
                                endpoint,
                                params={
                                    "per_page": per_page,
                                    "page": page,
                                    "status": "publish",  # Only publish for now
                                    "_embed": False
                                }
                            )
                            
                            # Check response status
                            if response.status_code == 404:
                                logger.info(f"No more pages for '{post_type}' (404 on page {page})")
                                break
                            elif response.status_code == 400:
                                # Check if it's the "invalid page number" error
                                try:
                                    error_data = response.json()
                                    if error_data.get('code') == 'rest_post_invalid_page_number':
                                        logger.info(f"Reached last page for '{post_type}' (page {page} doesn't exist)")
                                        break
                                except:
                                    pass
                                # If it's a different 400 error, try to continue
                                logger.warning(f"400 error for '{post_type}' page {page}, but not 'invalid page number' - continuing")
                            
                            response.raise_for_status()
                            
                            # Get pagination info from headers
                            total_pages = response.headers.get('X-WP-TotalPages', '0')
                            total_items = response.headers.get('X-WP-Total', '0')
                            
                            logger.info(f"'{post_type}' - Page {page}/{total_pages}, Total items: {total_items}")
                            
                            # Check if we've reached the last page according to headers
                            if total_pages and page >= int(total_pages):
                                logger.info(f"Reached last page for '{post_type}' according to headers (page {page} of {total_pages})")
                                # Process this last page, then break after
                                
                        except httpx.HTTPStatusError as e:
                            if e.response.status_code == 400:
                                # Check if it's the invalid page number error
                                try:
                                    error_data = e.response.json()
                                    if error_data.get('code') == 'rest_post_invalid_page_number':
                                        logger.info(f"All '{post_type}' pages fetched (invalid page number on page {page})")
                                        break
                                except:
                                    pass
                                logger.warning(f"400 error for '{post_type}': {e}")
                                break
                            elif e.response.status_code == 404:
                                logger.warning(f"Endpoint not found for '{post_type}': {endpoint}")
                                break
                            elif e.response.status_code == 401:
                                logger.error(f"Authentication required for '{post_type}'")
                                break
                            else:
                                logger.error(f"HTTP {e.response.status_code} for '{post_type}': {e}")
                                break
                        except Exception as e:
                            logger.error(f"Error fetching page {page} of '{post_type}': {e}")
                            break
                        
                        batch_items = response.json()
                        if not batch_items or len(batch_items) == 0:
                            logger.info(f"Empty response for '{post_type}' page {page}, stopping")
                            break
                        
                        # Process items one by one
                        for item in batch_items:
                            try:
                                cleaned_item = self._clean_post_data(item)
                                if cleaned_item:
                                    # Ensure type is set correctly
                                    cleaned_item['type'] = post_type
                                    all_content.append(cleaned_item)
                                    post_type_count += 1
                            except Exception as e:
                                logger.error(f"Error processing {post_type} item {item.get('id', 'unknown')}: {e}")
                                continue
                        
                        logger.info(f"Fetched {len(batch_items)} {post_type} items (page {page}), type total: {post_type_count}")
                        
                        # Check if this was the last page based on headers
                        if total_pages and page >= int(total_pages):
                            logger.info(f"This was the last page for '{post_type}' ({page} of {total_pages})")
                            break
                        
                        # Move to next page
                        page += 1
                        
                        # Safety limit to prevent infinite loops
                        if page > 100:  # Max 100 pages per type = 5000 items per type
                            logger.warning(f"Reached safety limit for '{post_type}', stopping at page {page}")
                            break
                    
                    # Log summary for this post type
                    logger.info(f"Completed fetching '{post_type}': {post_type_count} items indexed")
                    
                except Exception as e:
                    error_msg = str(e) if str(e) else f"{type(e).__name__} (no message)"
                    error_type = type(e).__name__
                    import traceback
                    error_trace = traceback.format_exc()
                    logger.error(f"Error fetching post type {post_type}: {error_type}: {error_msg}")
                    logger.debug(f"Full traceback: {error_trace}")
                    continue
        
        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__} (no message)"
            error_type = type(e).__name__
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error fetching post types: {error_type}: {error_msg}")
            logger.debug(f"Full traceback: {error_trace}")
        
        # Log breakdown by type
        type_counts = {}
        for item in all_content:
            item_type = item.get('type', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        
        logger.info(f"Total items from all post types fetched: {len(all_content)}")
        logger.info(f"Breakdown by type: {type_counts}")
        
        return all_content

    async def get_all_content(self, selected_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch and process all WordPress content from all post types.
        
        Args:
            selected_types: Optional list of specific post types to fetch. If None, fetches all public types.
        """
        logger.info("Starting content fetch from WordPress...")
        
        if selected_types:
            logger.info(f"Fetching only selected post types: {selected_types}")
        else:
            logger.info("Fetching all available public post types")
        
        try:
            # Fetch all content from specified or all post types
            all_content = await self.fetch_all_post_types(selected_types)
            
            logger.info(f"Successfully fetched {len(all_content)} content items")
            return all_content
            
        except Exception as e:
            logger.error(f"Error in get_all_content: {e}")
            # Return empty list to prevent complete failure
            return []
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
