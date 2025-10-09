"""
Cerebras LLM integration for query rewriting and answering.
"""
import logging
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI
import asyncio
import json
from config import settings

logger = logging.getLogger(__name__)


class CerebrasLLM:
    """Cerebras LLM client for query rewriting and answering."""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.cerebras_api_key,
            base_url=settings.cerebras_api_base
        )
        self.model = settings.cerebras_model
    
    def rewrite_query(self, original_query: str, context: str = "") -> str:
        """Rewrite and expand the search query for better retrieval."""
        try:
            prompt = f"""
You are a search query optimization expert. Your task is to rewrite and expand the user's search query to improve search results.

Original query: "{original_query}"
Context: {context}

Please provide:
1. A rewritten query that maintains the original intent but uses more specific and searchable terms
2. 2-3 alternative query variations that might capture different aspects of the search intent
3. Key terms and synonyms that should be considered

Format your response as JSON:
{{
    "rewritten_query": "the main rewritten query",
    "alternative_queries": ["alternative 1", "alternative 2", "alternative 3"],
    "key_terms": ["term1", "term2", "term3"],
    "synonyms": ["synonym1", "synonym2"]
}}

Keep the rewritten query concise but comprehensive. Focus on terms that would appear in relevant documents.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful search query optimization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                parsed_result = json.loads(result)
                return parsed_result.get("rewritten_query", original_query)
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw response
                return result
                
        except Exception as e:
            logger.error(f"Error rewriting query: {e}")
            return original_query
    
    def expand_query(self, query: str) -> List[str]:
        """Expand a query into multiple related queries."""
        try:
            prompt = f"""
Given the search query: "{query}"

Generate 3-5 related search queries that a user might also be interested in. These should be:
- Related to the same topic but from different angles
- Using different terminology or synonyms
- Covering different aspects of the topic

Return only the queries, one per line, without numbering or bullet points.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful search query expansion assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            result = response.choices[0].message.content.strip()
            
            # Split by lines and clean up
            queries = [q.strip() for q in result.split('\n') if q.strip()]
            
            # Add original query if not already present
            if query not in queries:
                queries.insert(0, query)
            
            return queries[:5]  # Limit to 5 queries
            
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return [query]
    
    def generate_answer(self, query: str, search_results: List[Dict[str, Any]], custom_instructions: str = "") -> str:
        """Generate a comprehensive answer based on search results."""
        try:
            if not search_results:
                return "I couldn't find any relevant information to answer your question."
            
            # Prepare context from search results
            context_parts = []
            for i, result in enumerate(search_results[:5], 1):  # Use top 5 results
                context_parts.append(f"""
Source {i}: {result['title']}
URL: {result['url']}
Content: {result['excerpt'] or result.get('content', '')[:500]}...
""")
            
            context = "\n".join(context_parts)
            
            # Use custom instructions if provided, otherwise use default
            custom_instr = custom_instructions.strip() if custom_instructions else ""
            
            if custom_instr:
                # Use ONLY custom instructions when provided
                base_instructions = f"""
Based on the following search results, answer the user's question.

IMPORTANT: Follow these custom instructions EXACTLY:
{custom_instr}
"""
            else:
                # Use default instructions only when no custom instructions are provided
                base_instructions = """
Based on the following search results, provide a comprehensive answer to the user's question.

Instructions:
1. Provide a clear, well-structured answer based on the search results
2. Cite specific sources when making claims
3. If the search results don't fully answer the question, acknowledge this
4. Use a helpful and informative tone
5. Keep the answer concise but comprehensive (2-3 paragraphs max)
"""
            
            prompt = f"""{base_instructions}

Question: "{query}"

Search Results:
{context}

Answer:
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant that provides accurate, well-sourced answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "I encountered an error while generating an answer. Please try again."
    
    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """Summarize content to a specified length."""
        try:
            prompt = f"""
Summarize the following content in approximately {max_length} characters or less. 
Focus on the main points and key information.

Content:
{content}

Summary:
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful content summarization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing content: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract key terms and concepts from text."""
        try:
            prompt = f"""
Extract the most important keywords and key phrases from the following text. 
Focus on terms that would be useful for search and categorization.

Text:
{text}

Provide 5-10 key terms, one per line, without numbering or bullet points.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful keyword extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            
            # Split by lines and clean up
            keywords = [k.strip() for k in result.split('\n') if k.strip()]
            
            return keywords[:10]  # Limit to 10 keywords
            
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []
    
    def classify_query_intent(self, query: str) -> Dict[str, Any]:
        """Classify the intent and type of the search query."""
        try:
            prompt = f"""
Analyze the following search query and classify its intent and characteristics:

Query: "{query}"

Please classify:
1. Intent type (informational, navigational, transactional, exploratory)
2. Query complexity (simple, moderate, complex)
3. Expected result type (article, tutorial, news, product, etc.)
4. Domain/topic area
5. Time sensitivity (current, historical, evergreen)

Respond in JSON format:
{{
    "intent_type": "informational|navigational|transactional|exploratory",
    "complexity": "simple|moderate|complex",
    "result_type": "article|tutorial|news|product|other",
    "domain": "brief domain description",
    "time_sensitivity": "current|historical|evergreen"
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful query analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # Return default classification if parsing fails
                return {
                    "intent_type": "informational",
                    "complexity": "moderate",
                    "result_type": "article",
                    "domain": "general",
                    "time_sensitivity": "evergreen"
                }
                
        except Exception as e:
            logger.error(f"Error classifying query intent: {e}")
            return {
                "intent_type": "informational",
                "complexity": "moderate",
                "result_type": "article",
                "domain": "general",
                "time_sensitivity": "evergreen"
            }
    
    async def process_query_async(self, query: str) -> Dict[str, Any]:
        """Process a query asynchronously with multiple LLM operations."""
        try:
            # Run multiple operations concurrently
            tasks = [
                asyncio.create_task(asyncio.to_thread(self.rewrite_query, query)),
                asyncio.create_task(asyncio.to_thread(self.expand_query, query)),
                asyncio.create_task(asyncio.to_thread(self.classify_query_intent, query))
            ]
            
            rewritten_query, expanded_queries, intent_classification = await asyncio.gather(*tasks)
            
            return {
                "original_query": query,
                "rewritten_query": rewritten_query,
                "expanded_queries": expanded_queries,
                "intent_classification": intent_classification
            }
            
        except Exception as e:
            logger.error(f"Error processing query asynchronously: {e}")
            return {
                "original_query": query,
                "rewritten_query": query,
                "expanded_queries": [query],
                "intent_classification": {
                    "intent_type": "informational",
                    "complexity": "moderate",
                    "result_type": "article",
                    "domain": "general",
                    "time_sensitivity": "evergreen"
                }
            }
    
    def rerank_results(
        self, 
        query: str, 
        results: List[Dict[str, Any]],
        custom_instructions: str = "",
        ai_weight: float = 0.7
    ) -> Dict[str, Any]:
        """
        Use LLM to rerank search results based on semantic relevance.
        
        Args:
            query: User's search query
            results: List of search results with titles, excerpts, scores
            custom_instructions: User's custom instructions for AI
            ai_weight: How much to weight AI score (0-1)
            
        Returns:
            {
                'results': Reranked results with ai_score and hybrid_score,
                'metadata': Stats about reranking
            }
        """
        import time
        start_time = time.time()
        
        try:
            if not results:
                return {'results': [], 'metadata': {}}
            
            logger.info(f"AI Reranking {len(results)} results for query: '{query}'")
            
            # Prepare results for LLM
            results_text = self._format_results_for_reranking(results)
            
            # Build system prompt with custom instructions
            system_prompt = """You are an expert search relevance analyzer. 
Your job is to score how well each search result matches the user's query based on semantic relevance, user intent, and content quality."""

            if custom_instructions:
                system_prompt += f"\n\n🎯 CUSTOM RANKING CRITERIA (HIGH PRIORITY):\n{custom_instructions}"
            
            # Build user prompt
            user_prompt = f"""
Analyze these search results for the query: "{query}"

{results_text}

📊 SCORING CRITERIA (Rate each result 0-100):

1. **Semantic Relevance** (40 points)
   - Does the content match the query's semantic meaning?
   - Is it exactly what the user is looking for?

2. **User Intent** (30 points)
   - Does it address what the user wants to accomplish?
   - For "how to" queries: Does it provide actionable steps?
   - For "what is" queries: Does it provide clear explanations?
   - For purchase intent: Does it offer products/services?

3. **Content Quality** (20 points)
   - Based on title and excerpt, does it seem comprehensive?
   - Is it from a credible source (inferred from title/URL)?
   - Does it appear to be high-quality content?

4. **Specificity** (10 points)
   - Is it specifically about the topic or too broad/general?
   - Does it cover the exact aspect the user asked about?

{f"5. **Custom Criteria** (HIGHEST PRIORITY):{chr(10)}{custom_instructions}" if custom_instructions else ""}

🎯 RETURN FORMAT:
Return a JSON array with scores for EACH result (include all {len(results)} results):
[
  {{"id": "1", "ai_score": 95, "reason": "Direct answer to query with actionable steps"}},
  {{"id": "2", "ai_score": 88, "reason": "Comprehensive guide covering all aspects"}},
  {{"id": "3", "ai_score": 72, "reason": "Related but somewhat general"}},
  ...
]

⚠️ IMPORTANT:
- Include ALL {len(results)} results in the SAME ORDER
- Be strict but fair in scoring
- Higher score = more relevant to the query
- Consider the custom criteria if provided
- Scores should range from 0-100
"""

            # Call LLM
            logger.info("Calling Cerebras LLM for reranking...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent scoring
                max_tokens=2000
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            logger.info(f"LLM response received ({len(response_text)} chars)")
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            ai_scores = json.loads(response_text)
            logger.info(f"Parsed {len(ai_scores)} AI scores")
            
            # Update results with AI scores
            reranked_results = []
            for result in results:
                # Find matching AI score
                ai_result = next((r for r in ai_scores if str(r.get('id')) == str(result['id'])), None)
                
                if ai_result:
                    tfidf_score = result.get('score', 0.0)
                    ai_score = ai_result['ai_score'] / 100  # Normalize to 0-1
                    
                    # Calculate hybrid score using custom weight
                    tfidf_weight = 1.0 - ai_weight
                    hybrid_score = (tfidf_score * tfidf_weight) + (ai_score * ai_weight)
                    
                    result['ai_score'] = ai_score
                    result['ai_reason'] = ai_result.get('reason', '')
                    result['hybrid_score'] = hybrid_score
                    result['score'] = hybrid_score  # Update main score for sorting
                    
                    logger.debug(f"Result '{result['title'][:50]}': TF-IDF={tfidf_score:.3f}, AI={ai_score:.3f}, Hybrid={hybrid_score:.3f}")
                else:
                    # Fallback if AI didn't score this result
                    result['ai_score'] = result.get('score', 0.0)
                    result['hybrid_score'] = result.get('score', 0.0)
                    result['ai_reason'] = 'No AI scoring available'
                    logger.warning(f"No AI score for result ID: {result['id']}")
                
                reranked_results.append(result)
            
            # Sort by hybrid score (highest first)
            reranked_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
            
            # Calculate stats
            response_time = time.time() - start_time
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            cost = (tokens_used / 1_000_000) * 0.10  # Cerebras pricing (~$0.10 per 1M tokens)
            
            metadata = {
                'ai_reranking_used': True,
                'ai_response_time': response_time,
                'ai_tokens_used': tokens_used,
                'ai_cost': cost,
                'ai_weight': ai_weight,
                'tfidf_weight': 1.0 - ai_weight,
                'custom_instructions_used': bool(custom_instructions),
                'results_reranked': len(reranked_results)
            }
            
            logger.info(f"✅ AI reranking complete! Time: {response_time:.2f}s, Cost: ${cost:.6f}, Tokens: {tokens_used}")
            logger.info(f"Top result: '{reranked_results[0]['title']}' (hybrid: {reranked_results[0]['hybrid_score']:.3f})")
            
            return {
                'results': reranked_results,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Error in AI reranking: {e}")
            # Fallback to original scores
            return {
                'results': results,
                'metadata': {
                    'ai_reranking_used': False,
                    'ai_error': str(e)
                }
            }
    
    def _format_results_for_reranking(self, results: List[Dict[str, Any]]) -> str:
        """Format results as text for LLM."""
        formatted = []
        for i, result in enumerate(results, 1):
            excerpt = result.get('excerpt', '')
            if len(excerpt) > 300:
                excerpt = excerpt[:300] + '...'
            
            formatted.append(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Result {i} (ID: {result['id']}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 Title: {result['title']}
🏷️  Type: {result.get('type', 'unknown')}
📝 Excerpt: {excerpt}
⭐ TF-IDF Score: {result.get('score', 0):.3f}
""")
        return "\n".join(formatted)
    
    def test_connection(self) -> bool:
        """Test the connection to Cerebras API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, this is a test message."}
                ],
                max_tokens=10
            )
            
            return response.choices[0].message.content is not None
            
        except Exception as e:
            logger.error(f"Error testing Cerebras connection: {e}")
            return False

