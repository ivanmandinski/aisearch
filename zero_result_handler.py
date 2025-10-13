"""
Zero-Result Query Handler
Provides suggestions and alternatives when search returns no results.
"""
import logging
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)


class ZeroResultHandler:
    """Handle queries that return no results."""
    
    def __init__(self, llm_client=None, search_system=None):
        self.llm_client = llm_client
        self.search_system = search_system
        
        # Common typo corrections
        self.typo_corrections = {
            'envrionmental': 'environmental',
            'compilance': 'compliance',
            'asessment': 'assessment',
            'enviromental': 'environmental',
            'auditting': 'auditing',
            'consutling': 'consulting',
            'enginering': 'engineering',
        }
    
    async def handle_zero_results(
        self, 
        query: str, 
        original_filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Handle zero-result query and provide helpful alternatives.
        
        Returns:
            {
                'suggestions': List of alternative queries,
                'corrected_query': Typo-corrected query if applicable,
                'related_searches': Related successful searches,
                'broadened_results': Results from broader search,
                'message': Helpful message to user
            }
        """
        try:
            logger.info(f"Handling zero results for query: {query}")
            
            result = {
                'suggestions': [],
                'corrected_query': None,
                'related_searches': [],
                'broadened_results': [],
                'message': 'No results found'
            }
            
            # 1. Check for typos and suggest corrections
            corrected = self._check_typos(query)
            if corrected != query:
                result['corrected_query'] = corrected
                result['message'] = f'Did you mean "{corrected}"?'
                
                # Try search with corrected query
                if self.search_system:
                    corrected_results, _ = await self.search_system.search(
                        corrected, 
                        limit=5,
                        enable_ai_reranking=False  # Save cost for corrections
                    )
                    if corrected_results:
                        result['broadened_results'] = corrected_results
                        return result
            
            # 2. Generate alternative query suggestions using LLM
            if self.llm_client:
                suggestions = await self._generate_alternatives(query)
                result['suggestions'] = suggestions
            
            # 3. Try broadening the search (remove filters, simplify query)
            if self.search_system:
                broadened_results = await self._try_broader_search(query, original_filters)
                if broadened_results:
                    result['broadened_results'] = broadened_results
                    result['message'] = 'No exact matches found, but here are related results:'
            
            # 4. Get related searches from analytics
            related = self._get_related_searches(query)
            if related:
                result['related_searches'] = related
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling zero results: {e}")
            return {
                'suggestions': [],
                'message': 'No results found. Try different keywords.'
            }
    
    def _check_typos(self, query: str) -> str:
        """Check for common typos and correct them."""
        query_lower = query.lower()
        
        for typo, correction in self.typo_corrections.items():
            if typo in query_lower:
                corrected = query_lower.replace(typo, correction)
                # Preserve original case style
                if query[0].isupper():
                    corrected = corrected.capitalize()
                logger.info(f"Typo correction: {query} → {corrected}")
                return corrected
        
        return query
    
    async def _generate_alternatives(self, query: str) -> List[str]:
        """Generate alternative query suggestions using LLM."""
        try:
            if not self.llm_client:
                return []
            
            prompt = f"""The search query "{query}" returned no results. 
Suggest 5 alternative search queries that might help the user find what they're looking for.

Consider:
- Synonyms and related terms
- Broader or more specific versions
- Common variations
- Domain-specific terminology (environmental, compliance, engineering, audits)

Return ONLY the alternative queries, one per line, without explanations.
"""
            
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {"role": "system", "content": "You are a helpful search assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=300
            )
            
            result = response.choices[0].message.content.strip()
            suggestions = [line.strip() for line in result.split('\n') if line.strip()]
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Error generating alternatives: {e}")
            return []
    
    async def _try_broader_search(
        self, 
        query: str, 
        original_filters: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """Try a broader search by removing filters and simplifying query."""
        try:
            if not self.search_system:
                return []
            
            # Remove filters (broaden search)
            results, _ = await self.search_system.search(
                query,
                limit=5,
                enable_ai_reranking=False  # Save cost
            )
            
            if results:
                return results
            
            # Try with simplified query (remove common words)
            simplified = self._simplify_query(query)
            if simplified != query:
                results, _ = await self.search_system.search(
                    simplified,
                    limit=5,
                    enable_ai_reranking=False
                )
                if results:
                    return results
            
            # Try with just the most important word
            important_word = self._extract_important_word(query)
            if important_word:
                results, _ = await self.search_system.search(
                    important_word,
                    limit=5,
                    enable_ai_reranking=False
                )
                return results
            
            return []
            
        except Exception as e:
            logger.error(f"Error in broader search: {e}")
            return []
    
    def _simplify_query(self, query: str) -> str:
        """Simplify query by removing common words."""
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = query.lower().split()
        filtered = [w for w in words if w not in stop_words]
        return ' '.join(filtered) if filtered else query
    
    def _extract_important_word(self, query: str) -> Optional[str]:
        """Extract the most important word from query."""
        words = query.lower().split()
        
        # Remove stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'how', 'what', 'why', 'when', 'where'}
        important_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Return longest word (often most specific)
        if important_words:
            return max(important_words, key=len)
        
        return None
    
    def _get_related_searches(self, query: str) -> List[str]:
        """Get related searches from analytics (popular searches with similar terms)."""
        try:
            # This would query WordPress analytics for related searches
            # For now, return empty list (implement when WordPress integration is complete)
            return []
            
        except Exception as e:
            logger.error(f"Error getting related searches: {e}")
            return []
    
    def track_zero_result(self, query: str, metadata: Dict[str, Any] = None):
        """Track zero-result queries for analysis."""
        try:
            logger.warning(f"Zero results for query: {query}")
            # This would log to analytics for later analysis
            # Helps identify content gaps
            
        except Exception as e:
            logger.error(f"Error tracking zero result: {e}")

