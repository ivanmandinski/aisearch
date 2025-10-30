"""
Query suggestions and autocomplete functionality.
Combines LLM suggestions with popular searches from analytics.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Generate query suggestions for autocomplete."""
    
    def __init__(self, llm_client=None, analytics_db=None):
        self.llm_client = llm_client
        self.analytics_db = analytics_db
        self.suggestion_cache = {}  # Cache suggestions
        self.cache_ttl = 3600  # 1 hour
    
    async def get_suggestions(
        self, 
        partial_query: str, 
        limit: int = 5,
        include_popular: bool = True
    ) -> List[str]:
        """Get suggestions for partial query."""
        try:
            if len(partial_query) < 2:
                return []
            
            # Check cache first
            cache_key = f"{partial_query.lower()}_{limit}"
            cached = self._get_cached_suggestion(cache_key)
            if cached:
                logger.debug(f"Returning cached suggestions for: {partial_query}")
                return cached
            
            suggestions = []
            
            # 1. Get popular searches that match prefix
            if include_popular and self.analytics_db:
                popular = await self._get_popular_matches(partial_query, limit=3)
                suggestions.extend(popular)
            
            # 2. Get LLM-generated suggestions
            if self.llm_client and len(suggestions) < limit:
                remaining = limit - len(suggestions)
                llm_suggestions = await self._get_llm_suggestions(partial_query, remaining)
                suggestions.extend(llm_suggestions)
            
            # 3. Remove duplicates, preserve order
            unique_suggestions = []
            seen = set()
            for s in suggestions:
                s_lower = s.lower()
                if s_lower not in seen:
                    unique_suggestions.append(s)
                    seen.add(s_lower)
            
            result = unique_suggestions[:limit]
            
            # Cache the result
            self._cache_suggestion(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting suggestions: {e}")
            return []
    
    async def _get_popular_matches(self, prefix: str, limit: int = 3) -> List[str]:
        """Get popular searches that match the prefix."""
        try:
            # This would query your WordPress analytics database
            # For now, return empty list (implement after WordPress integration)
            return []
            
        except Exception as e:
            logger.error(f"Error getting popular matches: {e}")
            return []
    
    async def _get_llm_suggestions(self, partial_query: str, limit: int) -> List[str]:
        """Get LLM-generated query completions."""
        try:
            if not self.llm_client:
                return []
            
            # Use LLM to complete/expand the partial query
            prompt = f"""Given the partial search query "{partial_query}", suggest {limit} complete search queries that a user might want to search for.

Focus on:
- Completing the partial query naturally
- Related searches users might want
- Common variations and expansions
- Domain-relevant queries (environmental, compliance, engineering, audits)

Return ONLY the suggested queries, one per line, without numbering or explanations.

Example:
Partial: "environ"
Suggestions:
environmental compliance
environmental impact assessment
environmental consulting services
environmental regulations
"""
            
            # Use async client to avoid blocking the event loop
            response = await self.llm_client.async_client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {"role": "system", "content": "You are a helpful search suggestion assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse line-by-line
            suggestions = [line.strip() for line in result.split('\n') if line.strip()]
            
            # Filter out suggestions that don't start with the partial query
            # (allow some flexibility)
            filtered = [
                s for s in suggestions 
                if partial_query.lower() in s.lower()
            ]
            
            return filtered[:limit]
            
        except Exception as e:
            logger.error(f"Error getting LLM suggestions: {e}")
            return []
    
    def _get_cached_suggestion(self, key: str) -> List[str]:
        """Get suggestion from cache if not expired."""
        if key in self.suggestion_cache:
            cached_data, timestamp = self.suggestion_cache[key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self.cache_ttl:
                return cached_data
            else:
                # Expired, remove from cache
                del self.suggestion_cache[key]
        return None
    
    def _cache_suggestion(self, key: str, suggestions: List[str]):
        """Cache suggestion result."""
        self.suggestion_cache[key] = (suggestions, datetime.now())
    
    def get_trending_searches(self, limit: int = 10, hours: int = 24) -> List[Dict[str, Any]]:
        """Get trending search queries from recent analytics."""
        try:
            # This would query your analytics for trending searches
            # Return format: [{"query": "...", "count": N, "trend": "up"}]
            return []
            
        except Exception as e:
            logger.error(f"Error getting trending searches: {e}")
            return []

