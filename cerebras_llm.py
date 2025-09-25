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
    
    def generate_answer(self, query: str, search_results: List[Dict[str, Any]]) -> str:
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
Content: {result['excerpt'] or result['content'][:500]}...
""")
            
            context = "\n".join(context_parts)
            
            prompt = f"""
Based on the following search results, provide a comprehensive answer to the user's question.

Question: "{query}"

Search Results:
{context}

Instructions:
1. Provide a clear, well-structured answer based on the search results
2. Cite specific sources when making claims
3. If the search results don't fully answer the question, acknowledge this
4. Use a helpful and informative tone
5. Keep the answer concise but comprehensive (2-3 paragraphs max)

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
