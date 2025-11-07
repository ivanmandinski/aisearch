"""
Cerebras LLM integration for query rewriting and answering.
"""
import logging
import re
from typing import List, Dict, Any, Optional
import openai
from openai import OpenAI, AsyncOpenAI
import asyncio
import json
from config import settings

logger = logging.getLogger(__name__)


class CerebrasLLM:
    """Cerebras LLM client for query rewriting and answering."""
    
    def __init__(self):
        # Synchronous client for backwards compatibility
        self.client = OpenAI(
            api_key=settings.cerebras_api_key,
            base_url=settings.cerebras_api_base
        )
        # Async client for better performance
        self.async_client = AsyncOpenAI(
            api_key=settings.cerebras_api_key,
            base_url=settings.cerebras_api_base
        )
        self.model = settings.cerebras_model
        self.strict_mode = getattr(settings, 'strict_ai_answer_mode', True)  # Only use search results for answers
    
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
            
            # CRITICAL FIX: Extract JSON from markdown code blocks if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                # Try to extract JSON from generic code blocks
                parts = result.split("```")
                if len(parts) >= 2:
                    # Take the middle part (between first and second ```)
                    potential_json = parts[1].strip()
                    if potential_json.startswith('{'):
                        result = potential_json
            
            # Try to parse JSON response
            try:
                parsed_result = json.loads(result)
                rewritten = parsed_result.get("rewritten_query", original_query)
                # Ensure we return a clean string, not JSON
                if isinstance(rewritten, str) and len(rewritten.strip()) > 0:
                    return rewritten
                else:
                    return original_query
            except json.JSONDecodeError:
                # If JSON parsing fails, check if result is already a query string
                # (sometimes LLM returns just the query without JSON)
                if len(result) < 200 and not result.startswith('{'):
                    # Looks like a query string, return it
                    return result
                # Otherwise, return original query to avoid malformed queries
                logger.warning(f"Failed to parse query rewrite JSON, using original query")
                return original_query
                
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
            
            # Define strict_warning for both branches
            strict_warning = "STRICT MODE ENABLED: " if self.strict_mode else ""
            
            if custom_instr:
                # Use ONLY custom instructions when provided
                base_instructions = f"""
STRICT MODE: You MUST answer using ONLY the provided search results.

CRITICAL RULES - DO NOT VIOLATE:
1. ONLY use information that appears in the search results
2. Do NOT add ANY external knowledge, assumptions, or context
3. Do NOT infer what the user might be looking for
4. Do NOT add details that don't appear in the results
5. NEVER mention topics, terms, or concepts that don't appear in the search results - even to say they're not there
6. ONLY state what IS in the results - do NOT mention what is NOT in the results

HOW TO ANSWER - STEP BY STEP:
1. Read all source titles and excerpts
2. Extract ONLY facts that are explicitly stated
3. If you see conflicting information, mention both sources
4. Cite your sources clearly (Source 1, Source 2)
5. If information isn't in the results, simply omit it - DO NOT mention it

BAD EXAMPLES (DON'T DO THIS):
❌ "James Walsh is a musician, singer, and songwriter"
   → WRONG! You added "musician" - that's not in search results!
❌ "I cannot find information about James Walsh being a musician or singer"
   → WRONG! Don't mention "musician" or "singer" at all - they're not in the results!
❌ "The search results do not include information about biography, musician, singer, or Starsailor"
   → WRONG! These terms are not in the results, so don't mention them!
❌ "The project is located in California"
   → WRONG! You inferred location from company info - not in results!
❌ "SCS provides comprehensive environmental consulting services"
   → TOO VAGUE! Be specific - what does 'comprehensive' mean?

GOOD EXAMPLES (DO THIS):
✅ "The search results show James Walsh is the CEO of SCS Engineers (Source 1). He was elected to the Environmental Research and Education Foundation board (Source 1)."
✅ "Based on Source 1, the project involved soil remediation. Source 2 mentions the project lasted 18 months."
✅ "According to Source 1, SCS Engineers provides hazardous waste management services. Source 2 adds that they also offer environmental compliance consulting."

REMEMBER: If it's not in the search results, it doesn't exist. Don't mention it at all.

CONTEXT: User is likely looking for professional information about SCS Engineers. Common queries: staff members, services, projects, environmental solutions.

CUSTOM INSTRUCTIONS (follow these EXACTLY):
{custom_instr}
"""
            else:
                # Use default instructions only when no custom instructions are provided
                base_instructions = f"""
STRICT MODE: You MUST answer using ONLY the provided search results.

CRITICAL RULES - DO NOT VIOLATE:
1. ONLY use information that appears in the search results below
2. Do NOT add ANY external knowledge, assumptions, or context
3. Do NOT infer what the user might be looking for
4. Do NOT add details that don't appear in the results
5. NEVER mention topics, terms, or concepts that don't appear in the search results - even to say they're not there
6. ONLY state what IS in the results - do NOT mention what is NOT in the results

HOW TO ANSWER - STEP BY STEP:
1. Read all source titles and excerpts
2. Extract ONLY facts that are explicitly stated
3. If you see conflicting information, mention both sources
4. Cite your sources clearly (Source 1, Source 2)
5. If information isn't in the results, simply omit it - DO NOT mention it

BAD EXAMPLES (DON'T DO THIS):
❌ "James Walsh is a musician, singer, and songwriter"
   → WRONG! You added "musician" - that's not in search results!
❌ "I cannot find information about James Walsh being a musician or singer"
   → WRONG! Don't mention "musician" or "singer" at all - they're not in the results!
❌ "The search results do not include information about biography, musician, singer, or Starsailor"
   → WRONG! These terms are not in the results, so don't mention them!
❌ "The project is located in California"
   → WRONG! You inferred location from company info - not in results!
❌ "SCS provides comprehensive environmental consulting services"
   → TOO VAGUE! Be specific - what does 'comprehensive' mean?

GOOD EXAMPLES (DO THIS):
✅ "The search results show James Walsh is the CEO of SCS Engineers (Source 1). He was elected to the Environmental Research and Education Foundation board (Source 1)."
✅ "Based on Source 1, the project involved soil remediation. Source 2 mentions the project lasted 18 months."
✅ "According to Source 1, SCS Engineers provides hazardous waste management services. Source 2 adds that they also offer environmental compliance consulting."

REMEMBER: If it's not in the search results, it doesn't exist. Don't mention it at all.

CONTEXT: User is likely looking for professional information about SCS Engineers. Common queries: staff members, services, projects, environmental solutions. Avoid making this sound like generic web content.
"""
            
            prompt = f"""{base_instructions}

Question: "{query}"

Search Results:
{context}

Answer:
"""
            
            system_message = """You are a research assistant that answers questions using ONLY the provided search results. You MUST NOT use any external knowledge, assumptions, or information not explicitly present in the search results."""
            
            if self.strict_mode:
                system_message += """ 

CRITICAL STRICT MODE RULES:
1. Do NOT add ANY context that is not in the search results
2. Do NOT infer what the user might be looking for
3. Do NOT add details like "musician, singer, songwriter" unless they appear in the results
4. If results don't mention something, do NOT mention it either - even to say it's not there
5. NEVER mention topics, terms, or concepts from external knowledge - only use what's in the search results
6. Simply state what IS in the results, nothing more, nothing less

Example of what NOT to do:
❌ "There is no information about James Walsh being a musician" 
   → Don't add "musician" - that's not in the search results!
❌ "I cannot find information about James Walsh's biography as a musician or singer"
   → Don't mention "musician", "singer", or "biography" - these aren't in the results!
❌ "The search results do not mention James Walsh in relation to musician, singer, Starsailor, or biography"
   → Don't mention any of these terms - they're not in the results!

✅ "Based on the search results, James Walsh is the CEO of SCS Engineers."
   → Only uses what's actually in the results"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Convert markdown links to HTML links
            answer = self._convert_markdown_links_to_html(answer)
            
            # Validate that the answer is based on search results
            answer = self._validate_answer_context(answer, search_results)
            
            logger.info(f"Generated answer for query: {query[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "I encountered an error while generating an answer. Please try again."
    
    def _convert_markdown_links_to_html(self, text: str) -> str:
        """
        Convert markdown links [text](url) to HTML links <a href="url">text</a>.
        Also converts plain URLs to clickable links.
        
        Args:
            text: Text that may contain markdown links or plain URLs
            
        Returns:
            Text with HTML links
        """
        import re
        
        # Convert markdown links [text](url) to HTML
        text = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
            text
        )
        
        # Convert plain URLs to clickable links (but not if already in <a> tags)
        # Match URLs that are not already inside HTML tags
        url_pattern = r'(?<!["\'>])(https?://[^\s<>"\'{}|\\^`\[\]]+)(?!["\'])(?![^<]*>)'
        text = re.sub(
            url_pattern,
            r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>',
            text
        )
        
        # Convert Source references to links if we have search results
        # Pattern: "Source 1" -> link to first result
        # This will be handled by the frontend if needed
        
        return text
    
    def _validate_answer_context(self, answer: str, search_results: List[Dict[str, Any]]) -> str:
        """Validate that the answer is based on search results and filter out irrelevant terms."""
        try:
            # Extract key terms from search results
            search_content = []
            for result in search_results[:5]:  # Check top 5 results
                content = (result.get('excerpt', '') or result.get('content', '') or result.get('title', '')).lower()
                search_content.append(content)
            
            combined_content = ' '.join(search_content)
            
            # Extract words from search results (for validation)
            search_words = set(re.findall(r'\b\w{4,}\b', combined_content.lower()))  # Words 4+ chars
            
            # Check for phrases that mention terms not in search results
            # Common problematic patterns
            problematic_patterns = [
                r'cannot find.*?about.*?(?:musician|singer|songwriter|biography|starsailor)',
                r'do not.*?include.*?information.*?about.*?(?:musician|singer|songwriter|biography|starsailor)',
                r'no information.*?about.*?(?:musician|singer|songwriter|biography|starsailor)',
                r'does not mention.*?(?:musician|singer|songwriter|biography|starsailor)',
                r'not.*?in.*?the.*?results.*?(?:musician|singer|songwriter|biography|starsailor)',
            ]
            
            # Check if answer contains problematic patterns
            answer_lower = answer.lower()
            for pattern in problematic_patterns:
                matches = re.finditer(pattern, answer_lower, re.IGNORECASE)
                for match in matches:
                    # Found a problematic mention - remove that sentence
                    sentence_start = max(0, answer.rfind('.', 0, match.start()) + 1)
                    sentence_end = answer.find('.', match.end())
                    if sentence_end == -1:
                        sentence_end = len(answer)
                    else:
                        sentence_end += 1
                    
                    # Remove the problematic sentence
                    answer = answer[:sentence_start].strip() + ' ' + answer[sentence_end:].strip()
                    answer = re.sub(r'\s+', ' ', answer).strip()
                    logger.warning(f"Removed sentence mentioning terms not in search results: {match.group()}")
            
            # Check if answer contains source references
            has_source_refs = any(f"Source {i}" in answer for i in range(1, 6))
            
            # If no source references and answer seems generic, add disclaimer
            if not has_source_refs and len(answer) > 100:
                # Check if answer might be using external knowledge
                generic_phrases = [
                    "in general", "typically", "usually", "commonly", "generally",
                    "it is known that", "research shows", "studies indicate",
                    "experts say", "according to experts", "it is widely known"
                ]
                
                if any(phrase in answer.lower() for phrase in generic_phrases):
                    disclaimer = "\n\n*Note: This answer is based on the available search results. For more specific information, please review the individual sources listed below.*"
                    answer += disclaimer
            
            return answer
            
        except Exception as e:
            logger.warning(f"Answer validation failed: {e}")
            return answer
    
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
            # CRITICAL FIX: Don't rewrite query if it's already malformed JSON
            # This prevents double-processing and malformed queries
            if query.startswith('```') or (query.strip().startswith('{') and query.strip().endswith('}')):
                logger.warning(f"⚠️ Query appears to be malformed JSON, skipping rewriting: {query[:100]}")
                return {
                    "original_query": query,
                    "rewritten_query": query,  # Return original, don't rewrite
                    "expanded_queries": [query],
                    "intent_classification": {
                        "intent_type": "informational",
                        "complexity": "moderate",
                        "result_type": "article",
                        "domain": "general",
                        "time_sensitivity": "evergreen"
                    }
                }
            
            # Run multiple operations concurrently
            tasks = [
                asyncio.create_task(asyncio.to_thread(self.rewrite_query, query)),
                asyncio.create_task(asyncio.to_thread(self.expand_query, query)),
                asyncio.create_task(asyncio.to_thread(self.classify_query_intent, query))
            ]
            
            rewritten_query, expanded_queries, intent_classification = await asyncio.gather(*tasks)
            
            # CRITICAL FIX: Ensure rewritten_query is a string, not JSON
            # Sometimes rewrite_query returns JSON string instead of just the query
            if isinstance(rewritten_query, str) and rewritten_query.strip().startswith('{'):
                try:
                    import json
                    parsed = json.loads(rewritten_query)
                    if 'rewritten_query' in parsed:
                        rewritten_query = parsed['rewritten_query']
                        logger.info(f"✅ Extracted rewritten_query from JSON: {rewritten_query}")
                except json.JSONDecodeError:
                    pass  # Not JSON, use as-is
            
            # Ensure rewritten_query is a clean string
            if not isinstance(rewritten_query, str) or len(rewritten_query.strip()) == 0:
                rewritten_query = query  # Fallback to original
            
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
    
    async def rerank_results_async(
        self, 
        query: str, 
        results: List[Dict[str, Any]],
        custom_instructions: str = "",
        ai_weight: float = 0.7,
        post_type_priority: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to rerank search results based on semantic relevance (async version).
        
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
            system_prompt = """You are an expert search relevance analyzer for SCS Engineers, a professional environmental consulting firm.

BUSINESS CONTEXT:
- SCS Engineers provides environmental, engineering, and consulting services
- Main services include: waste management, environmental compliance, sustainability consulting
- Post types you'll see:
  * "scs-professionals": Staff member profiles with expertise
  * "scs-services": Service descriptions and capabilities
  * "page": General pages (About, Services, Projects, Contact)
  * "post": Blog articles, case studies, news

YOUR JOB:
Score search results based on how well they match user queries for this business context.
Consider business priorities: professional expertise, service offerings, and user intent."""

            if custom_instructions:
                system_prompt += f"\n\n🎯 CUSTOM RANKING CRITERIA (HIGHEST PRIORITY):\n{custom_instructions}"
            
            # Build user prompt
            user_prompt = f"""
Analyze these search results for the query: "{query}"

{results_text}

📊 SCORING CRITERIA (Rate each result 0-100):

1. **Semantic Relevance** (45 points)
   - Does the content match the query's semantic meaning?
   - Is it exactly what the user is looking for?
   
   EXAMPLES:
   ✅ Query: "hazardous waste management" → Result: "Hazardous Waste Management Services" (Score: 95 - exact match)
   ✅ Query: "toxic site remediation" → Result: "Environmental Remediation Services" (Score: 85 - conceptually related)
   ❌ Query: "water treatment" → Result: "Solid Waste Management" (Score: 25 - not relevant)

2. **User Intent** (40 points)
   - Does it address what the user wants to accomplish?
   
   INTENT SCORING:
   • PERSON NAME ("James Walsh"): scs-professionals profile → Score: 95, Article mentioning person → Score: 75, Generic → Score: 30
   • EXECUTIVE ROLE ("Who is the CEO?"): scs-professionals profile with role in title → Score: 100, Profile mentioning role → Score: 95, Press release naming CEO → Score: 90, Article mentioning CEO → Score: 70, Generic → Score: 30
   • SERVICE ("hazardous waste"): scs-services page → Score: 95, Case study → Score: 80, Blog post → Score: 50
   • HOW-TO ("how to"): Step-by-step guide → Score: 90, Case study → Score: 70, General page → Score: 40
   • NAVIGATIONAL ("contact"): Exact page → Score: 100, Related page → Score: 65, Article → Score: 25
   • TRANSACTIONAL ("request quote"): Action page → Score: 95, Mentions service → Score: 60, Article → Score: 35

   SPECIAL CASE - CEO/PRESIDENT QUERIES:
   When query asks "Who is the CEO?" or similar:
   - Professional profile of CURRENT CEO with role in title → Score: 100 (CRITICAL!)
   - Professional profile mentioning CEO role → Score: 95
   - Press release announcing CEO → Score: 90
   - Article mentioning CEO → Score: 70
   - Other professionals → Score: 30-40
   - Blog posts about leadership → Score: 40-50

3. **Content Quality** (10 points)
   - Based on title and excerpt, does it seem comprehensive?
   - Is it from a credible source (inferred from title/URL)?
   - Does it appear to be high-quality content?

4. **Specificity** (5 points)
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

            # Call LLM asynchronously
            logger.info("Calling Cerebras LLM for reranking (async)...")
            response = await self.async_client.chat.completions.create(
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
            logger.debug(f"Response preview: {response_text[:500]}")
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Validate response_text before parsing
            if not response_text or not response_text.strip():
                logger.error(f"Empty response_text after extraction. Original: {response.choices[0].message.content[:200]}")
                raise ValueError("Empty JSON response from LLM")
            
            # Try to parse JSON with better error handling
            try:
                ai_scores = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response text that failed to parse: {response_text[:500]}")
                # Try to extract JSON array from the text
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    logger.info("Attempting to extract JSON array from text")
                    ai_scores = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from LLM response: {e}")
            
            # Validate that ai_scores is a list
            if not isinstance(ai_scores, list):
                logger.error(f"AI scores is not a list: {type(ai_scores)}, value: {ai_scores}")
                raise ValueError(f"Expected list of scores, got {type(ai_scores)}")
            
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
                    
                    # Add ranking explanation for admin users
                    result['ranking_explanation'] = {
                        'tfidf_score': round(tfidf_score, 4),
                        'ai_score': round(ai_score, 4),
                        'ai_score_raw': ai_result['ai_score'],  # 0-100 scale
                        'hybrid_score': round(hybrid_score, 4),
                        'tfidf_weight': round(tfidf_weight, 2),
                        'ai_weight': round(ai_weight, 2),
                        'ai_reason': ai_result.get('reason', ''),
                        'post_type': result.get('type', 'unknown'),
                        'position_before_priority': None,  # Will be set after sorting
                    }
                    
                    logger.debug(f"Result '{result['title'][:50]}': TF-IDF={tfidf_score:.3f}, AI={ai_score:.3f}, Hybrid={hybrid_score:.3f}")
                else:
                    # Fallback if AI didn't score this result
                    result['ai_score'] = result.get('score', 0.0)
                    result['hybrid_score'] = result.get('score', 0.0)
                    result['ai_reason'] = 'No AI scoring available'
                    result['ranking_explanation'] = {
                        'tfidf_score': round(result.get('score', 0.0), 4),
                        'ai_score': None,
                        'ai_score_raw': None,
                        'hybrid_score': round(result.get('score', 0.0), 4),
                        'tfidf_weight': 1.0,
                        'ai_weight': 0.0,
                        'ai_reason': 'No AI scoring available',
                        'post_type': result.get('type', 'unknown'),
                        'position_before_priority': None,
                    }
                    logger.warning(f"No AI score for result ID: {result['id']}")
                
                reranked_results.append(result)
            
            # Sort by hybrid score (highest first), then by post type priority within same score
            priority_map = {}
            if post_type_priority and len(post_type_priority) > 0:
                priority_map = {post_type: idx for idx, post_type in enumerate(post_type_priority)}
                def get_priority_value(result):
                    post_type = result.get('type', '')
                    return priority_map.get(post_type, 9999)
                # Sort by: hybrid_score DESC, then priority ASC (lower idx = higher priority)
                # Use negative priority to make lower idx sort first when reverse=True
                reranked_results.sort(key=lambda x: (x.get('hybrid_score', 0), -get_priority_value(x)), reverse=True)
                logger.info(f"Sorted with post type priority: {post_type_priority}")
            else:
                reranked_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
            
            # Filter out results marked as not relevant by AI
            filtered_results = []
            not_relevant_keywords = [
                'not relevant',
                'not the same',
                'not related',
                'unrelated',
                'does not match',
                'does not address',
                'irrelevant',
                'not applicable',
                'wrong',
                'incorrect',
                'different person',
                'different topic',
                'different subject'
            ]
            
            for result in reranked_results:
                ai_reason = result.get('ai_reason', '').lower()
                ai_score_raw = result.get('ranking_explanation', {}).get('ai_score_raw', None)
                
                # Check if AI explicitly marked as not relevant
                is_not_relevant = False
                
                # Check AI reasoning text for not relevant keywords
                if ai_reason:
                    for keyword in not_relevant_keywords:
                        if keyword in ai_reason:
                            is_not_relevant = True
                            logger.info(f"🚫 Filtering out result '{result.get('title', '')[:50]}' - AI reason: '{ai_reason[:100]}'")
                            break
                
                # Also filter if AI score is very low (below 30) AND reason contains negative indicators
                if not is_not_relevant and ai_score_raw is not None:
                    if ai_score_raw < 30 and any(keyword in ai_reason for keyword in ['not', 'different', 'wrong', 'incorrect']):
                        is_not_relevant = True
                        logger.info(f"🚫 Filtering out result '{result.get('title', '')[:50]}' - Low AI score ({ai_score_raw}) with negative reasoning")
                
                if not is_not_relevant:
                    filtered_results.append(result)
                else:
                    logger.debug(f"Filtered out: {result.get('title', 'Unknown')[:50]} - Reason: {ai_reason[:100]}")
            
            if len(filtered_results) < len(reranked_results):
                logger.info(f"🚫 Filtered out {len(reranked_results) - len(filtered_results)} not relevant results")
            
            # Add position and priority info to ranking explanation after filtering
            for idx, result in enumerate(filtered_results):
                if 'ranking_explanation' in result:
                    result['ranking_explanation']['final_position'] = idx + 1
                    result['ranking_explanation']['post_type_priority'] = priority_map.get(result.get('type', ''), 9999)
                    result['ranking_explanation']['priority_order'] = post_type_priority if post_type_priority else []
            
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
                'post_type_priority_applied': bool(post_type_priority),
                'results_reranked': len(reranked_results),
                'results_filtered': len(reranked_results) - len(filtered_results)
            }
            
            logger.info(f"✅ AI reranking complete! Time: {response_time:.2f}s, Cost: ${cost:.6f}, Tokens: {tokens_used}")
            if filtered_results:
                logger.info(f"Top result: '{filtered_results[0]['title']}' (hybrid: {filtered_results[0]['hybrid_score']:.3f})")
            
            return {
                'results': filtered_results,
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
    
    def rerank_results(
        self, 
        query: str, 
        results: List[Dict[str, Any]],
        custom_instructions: str = "",
        ai_weight: float = 0.7,
        post_type_priority: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to rerank search results based on semantic relevance (sync wrapper).
        
        This is a synchronous wrapper around rerank_results_async for backwards compatibility.
        Use rerank_results_async directly in async contexts for better performance.
        
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
            system_prompt = """You are an expert search relevance analyzer for SCS Engineers, a professional environmental consulting firm.

BUSINESS CONTEXT:
- SCS Engineers provides environmental, engineering, and consulting services
- Main services include: waste management, environmental compliance, sustainability consulting
- Post types you'll see:
  * "scs-professionals": Staff member profiles with expertise
  * "scs-services": Service descriptions and capabilities
  * "page": General pages (About, Services, Projects, Contact)
  * "post": Blog articles, case studies, news

YOUR JOB:
Score search results based on how well they match user queries for this business context.
Consider business priorities: professional expertise, service offerings, and user intent."""

            if custom_instructions:
                system_prompt += f"\n\n🎯 CUSTOM RANKING CRITERIA (HIGHEST PRIORITY):\n{custom_instructions}"
            
            # Build user prompt
            user_prompt = f"""
Analyze these search results for the query: "{query}"

{results_text}

📊 SCORING CRITERIA (Rate each result 0-100):

1. **Semantic Relevance** (45 points)
   - Does the content match the query's semantic meaning?
   - Is it exactly what the user is looking for?
   
   EXAMPLES:
   ✅ Query: "hazardous waste management" → Result: "Hazardous Waste Management Services" (Score: 95 - exact match)
   ✅ Query: "toxic site remediation" → Result: "Environmental Remediation Services" (Score: 85 - conceptually related)
   ❌ Query: "water treatment" → Result: "Solid Waste Management" (Score: 25 - not relevant)

2. **User Intent** (40 points)
   - Does it address what the user wants to accomplish?
   
   INTENT SCORING:
   • PERSON NAME ("James Walsh"): scs-professionals profile → Score: 95, Article mentioning person → Score: 75, Generic → Score: 30
   • EXECUTIVE ROLE ("Who is the CEO?"): scs-professionals profile with role in title → Score: 100, Profile mentioning role → Score: 95, Press release naming CEO → Score: 90, Article mentioning CEO → Score: 70, Generic → Score: 30
   • SERVICE ("hazardous waste"): scs-services page → Score: 95, Case study → Score: 80, Blog post → Score: 50
   • HOW-TO ("how to"): Step-by-step guide → Score: 90, Case study → Score: 70, General page → Score: 40
   • NAVIGATIONAL ("contact"): Exact page → Score: 100, Related page → Score: 65, Article → Score: 25
   • TRANSACTIONAL ("request quote"): Action page → Score: 95, Mentions service → Score: 60, Article → Score: 35

   SPECIAL CASE - CEO/PRESIDENT QUERIES:
   When query asks "Who is the CEO?" or similar:
   - Professional profile of CURRENT CEO with role in title → Score: 100 (CRITICAL!)
   - Professional profile mentioning CEO role → Score: 95
   - Press release announcing CEO → Score: 90
   - Article mentioning CEO → Score: 70
   - Other professionals → Score: 30-40
   - Blog posts about leadership → Score: 40-50

3. **Content Quality** (10 points)
   - Based on title and excerpt, does it seem comprehensive?
   - Is it from a credible source (inferred from title/URL)?
   - Does it appear to be high-quality content?

4. **Specificity** (5 points)
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
            logger.debug(f"Response preview: {response_text[:500]}")
            
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Validate response_text before parsing
            if not response_text or not response_text.strip():
                logger.error(f"Empty response_text after extraction. Original: {response.choices[0].message.content[:200]}")
                raise ValueError("Empty JSON response from LLM")
            
            # Try to parse JSON with better error handling
            try:
                ai_scores = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Response text that failed to parse: {response_text[:500]}")
                # Try to extract JSON array from the text
                import re
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    logger.info("Attempting to extract JSON array from text")
                    ai_scores = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from LLM response: {e}")
            
            # Validate that ai_scores is a list
            if not isinstance(ai_scores, list):
                logger.error(f"AI scores is not a list: {type(ai_scores)}, value: {ai_scores}")
                raise ValueError(f"Expected list of scores, got {type(ai_scores)}")
            
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
                    
                    # Add ranking explanation for admin users
                    result['ranking_explanation'] = {
                        'tfidf_score': round(tfidf_score, 4),
                        'ai_score': round(ai_score, 4),
                        'ai_score_raw': ai_result['ai_score'],  # 0-100 scale
                        'hybrid_score': round(hybrid_score, 4),
                        'tfidf_weight': round(tfidf_weight, 2),
                        'ai_weight': round(ai_weight, 2),
                        'ai_reason': ai_result.get('reason', ''),
                        'post_type': result.get('type', 'unknown'),
                        'position_before_priority': None,  # Will be set after sorting
                    }
                    
                    logger.debug(f"Result '{result['title'][:50]}': TF-IDF={tfidf_score:.3f}, AI={ai_score:.3f}, Hybrid={hybrid_score:.3f}")
                else:
                    # Fallback if AI didn't score this result
                    result['ai_score'] = result.get('score', 0.0)
                    result['hybrid_score'] = result.get('score', 0.0)
                    result['ai_reason'] = 'No AI scoring available'
                    result['ranking_explanation'] = {
                        'tfidf_score': round(result.get('score', 0.0), 4),
                        'ai_score': None,
                        'ai_score_raw': None,
                        'hybrid_score': round(result.get('score', 0.0), 4),
                        'tfidf_weight': 1.0,
                        'ai_weight': 0.0,
                        'ai_reason': 'No AI scoring available',
                        'post_type': result.get('type', 'unknown'),
                        'position_before_priority': None,
                    }
                    logger.warning(f"No AI score for result ID: {result['id']}")
                
                reranked_results.append(result)
            
            # Sort by hybrid score (highest first), then by post type priority within same score
            priority_map = {}
            if post_type_priority and len(post_type_priority) > 0:
                priority_map = {post_type: idx for idx, post_type in enumerate(post_type_priority)}
                def get_priority_value(result):
                    post_type = result.get('type', '')
                    return priority_map.get(post_type, 9999)
                # Sort by: hybrid_score DESC, then priority ASC (lower idx = higher priority)
                # Use negative priority to make lower idx sort first when reverse=True
                reranked_results.sort(key=lambda x: (x.get('hybrid_score', 0), -get_priority_value(x)), reverse=True)
                logger.info(f"Sorted with post type priority: {post_type_priority}")
            else:
                reranked_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
            
            # Filter out results marked as not relevant by AI
            filtered_results = []
            not_relevant_keywords = [
                'not relevant',
                'not the same',
                'not related',
                'unrelated',
                'does not match',
                'does not address',
                'irrelevant',
                'not applicable',
                'wrong',
                'incorrect',
                'different person',
                'different topic',
                'different subject'
            ]
            
            for result in reranked_results:
                ai_reason = result.get('ai_reason', '').lower()
                ai_score_raw = result.get('ranking_explanation', {}).get('ai_score_raw', None)
                
                # Check if AI explicitly marked as not relevant
                is_not_relevant = False
                
                # Check AI reasoning text for not relevant keywords
                if ai_reason:
                    for keyword in not_relevant_keywords:
                        if keyword in ai_reason:
                            is_not_relevant = True
                            logger.info(f"🚫 Filtering out result '{result.get('title', '')[:50]}' - AI reason: '{ai_reason[:100]}'")
                            break
                
                # Also filter if AI score is very low (below 30) AND reason contains negative indicators
                if not is_not_relevant and ai_score_raw is not None:
                    if ai_score_raw < 30 and any(keyword in ai_reason for keyword in ['not', 'different', 'wrong', 'incorrect']):
                        is_not_relevant = True
                        logger.info(f"🚫 Filtering out result '{result.get('title', '')[:50]}' - Low AI score ({ai_score_raw}) with negative reasoning")
                
                if not is_not_relevant:
                    filtered_results.append(result)
                else:
                    logger.debug(f"Filtered out: {result.get('title', 'Unknown')[:50]} - Reason: {ai_reason[:100]}")
            
            if len(filtered_results) < len(reranked_results):
                logger.info(f"🚫 Filtered out {len(reranked_results) - len(filtered_results)} not relevant results")
            
            # Add position and priority info to ranking explanation after filtering
            for idx, result in enumerate(filtered_results):
                if 'ranking_explanation' in result:
                    result['ranking_explanation']['final_position'] = idx + 1
                    result['ranking_explanation']['post_type_priority'] = priority_map.get(result.get('type', ''), 9999)
                    result['ranking_explanation']['priority_order'] = post_type_priority if post_type_priority else []
            
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
                'post_type_priority_applied': bool(post_type_priority),
                'results_reranked': len(reranked_results),
                'results_filtered': len(reranked_results) - len(filtered_results)
            }
            
            logger.info(f"✅ AI reranking complete! Time: {response_time:.2f}s, Cost: ${cost:.6f}, Tokens: {tokens_used}")
            if filtered_results:
                logger.info(f"Top result: '{filtered_results[0]['title']}' (hybrid: {filtered_results[0]['hybrid_score']:.3f})")
            
            return {
                'results': filtered_results,
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
        """Format results as text for LLM (optimized - shorter format)."""
        formatted = []
        for i, result in enumerate(results, 1):
            excerpt = result.get('excerpt', '')
            # OPTIMIZATION: Reduce excerpt length for faster processing
            if len(excerpt) > 200:  # Reduced from 300
                excerpt = excerpt[:200] + '...'
            
            # OPTIMIZATION: Shorter format to reduce token usage
            formatted.append(f"{i}. ID:{result['id']} | {result['title']} ({result.get('type', 'unknown')}) | Score:{result.get('score', 0):.3f}\n   {excerpt}")
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

