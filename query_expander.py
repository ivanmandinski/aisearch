"""
Query Expansion and Synonym System
Expands queries with synonyms and related terms for better recall.
"""
import logging
from typing import List, Set, Dict, Any
import re

logger = logging.getLogger(__name__)


class QueryExpander:
    """Expand queries with synonyms and related terms."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        
        # Domain-specific synonym dictionary (Environmental/Engineering)
        self.synonyms = {
            # Environmental terms
            'environmental': ['ecological', 'green', 'sustainability', 'eco-friendly', 'nature'],
            'pollution': ['contamination', 'emissions', 'effluent', 'discharge', 'waste'],
            'sustainability': ['sustainable', 'eco-friendly', 'green', 'environmental'],
            'remediation': ['cleanup', 'restoration', 'rehabilitation', 'recovery', 'decontamination'],
            'assessment': ['evaluation', 'analysis', 'study', 'review', 'examination', 'audit'],
            
            # Compliance terms
            'compliance': ['regulatory', 'conformance', 'adherence', 'conformity', 'regulation'],
            'regulation': ['rule', 'requirement', 'standard', 'law', 'guideline', 'policy'],
            'permit': ['license', 'authorization', 'approval', 'certification'],
            
            # Engineering terms
            'audit': ['assessment', 'evaluation', 'review', 'inspection', 'examination', 'analysis'],
            'inspection': ['examination', 'review', 'audit', 'survey', 'assessment'],
            'engineering': ['technical', 'design', 'planning', 'development'],
            'design': ['planning', 'engineering', 'development', 'blueprint', 'specification'],
            
            # Services
            'consulting': ['advisory', 'consultancy', 'guidance', 'expert', 'professional'],
            'services': ['solutions', 'offerings', 'capabilities', 'expertise'],
            'analysis': ['study', 'assessment', 'evaluation', 'examination', 'review'],
            
            # Energy terms
            'energy': ['power', 'electricity', 'fuel', 'renewable'],
            'efficiency': ['optimization', 'performance', 'productivity', 'improvement'],
            'renewable': ['solar', 'wind', 'sustainable', 'green energy', 'clean energy'],
            
            # Waste management
            'waste': ['refuse', 'garbage', 'trash', 'disposal', 'recycling'],
            'recycling': ['reclamation', 'recovery', 'reuse', 'waste management'],
            'landfill': ['disposal site', 'waste facility', 'dump'],
            
            # Water/Air
            'water': ['wastewater', 'stormwater', 'groundwater', 'aquatic'],
            'air': ['atmospheric', 'emissions', 'air quality', 'ventilation'],
            'soil': ['ground', 'earth', 'sediment', 'land'],
            
            # Project types
            'project': ['initiative', 'program', 'development', 'work'],
            'study': ['research', 'investigation', 'analysis', 'examination'],
            'report': ['document', 'publication', 'analysis', 'findings'],
        }
        
        # Build reverse index for faster lookup
        self.reverse_synonyms = {}
        for word, syns in self.synonyms.items():
            for syn in syns:
                if syn not in self.reverse_synonyms:
                    self.reverse_synonyms[syn] = []
                self.reverse_synonyms[syn].append(word)
    
    def expand_query(self, query: str, max_expansions: int = 5) -> List[str]:
        """
        Expand query with synonyms and variations.
        
        Args:
            query: Original search query
            max_expansions: Maximum number of expanded queries to return
            
        Returns:
            List of expanded queries (including original)
        """
        try:
            expanded_queries = [query]  # Always include original
            
            query_lower = query.lower()
            words = re.findall(r'\b\w+\b', query_lower)
            
            # Find synonyms for each word
            all_synonyms = {}
            for word in words:
                if word in self.synonyms:
                    all_synonyms[word] = self.synonyms[word]
                elif word in self.reverse_synonyms:
                    all_synonyms[word] = self.reverse_synonyms[word]
            
            # Generate variations by replacing words with synonyms
            if all_synonyms:
                for word, syns in list(all_synonyms.items())[:2]:  # Limit to 2 words to avoid explosion
                    for syn in syns[:3]:  # Max 3 synonyms per word
                        expanded = query_lower.replace(word, syn)
                        if expanded != query_lower and expanded not in expanded_queries:
                            expanded_queries.append(expanded)
                            if len(expanded_queries) >= max_expansions:
                                break
                    if len(expanded_queries) >= max_expansions:
                        break
            
            logger.info(f"Expanded '{query}' to {len(expanded_queries)} variations")
            return expanded_queries[:max_expansions]
            
        except Exception as e:
            logger.error(f"Error expanding query: {e}")
            return [query]
    
    async def expand_with_llm(self, query: str, max_expansions: int = 5) -> List[str]:
        """Expand query using LLM for more intelligent variations."""
        try:
            if not self.llm_client:
                return self.expand_query(query, max_expansions)
            
            # Get synonym-based expansions
            synonym_expansions = self.expand_query(query, max_expansions=3)
            
            # Get LLM expansions
            prompt = f"""Given the search query "{query}", suggest {max_expansions} related search queries using synonyms and alternative phrasings.

Focus on:
- Using synonyms for key terms
- Alternative ways to phrase the same question
- Related topics users might also search for
- Domain-specific terminology (environmental, compliance, engineering)

Return ONLY the queries, one per line.
"""
            
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {"role": "system", "content": "You are a search query expansion expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=300
            )
            
            result = response.choices[0].message.content.strip()
            llm_expansions = [line.strip() for line in result.split('\n') if line.strip()]
            
            # Combine and deduplicate
            all_expansions = synonym_expansions + llm_expansions
            unique_expansions = []
            seen = set()
            
            for exp in all_expansions:
                exp_lower = exp.lower()
                if exp_lower not in seen:
                    unique_expansions.append(exp)
                    seen.add(exp_lower)
            
            return unique_expansions[:max_expansions]
            
        except Exception as e:
            logger.error(f"Error expanding query with LLM: {e}")
            return self.expand_query(query, max_expansions)
    
    def get_synonyms(self, word: str) -> List[str]:
        """Get synonyms for a specific word."""
        word_lower = word.lower()
        
        if word_lower in self.synonyms:
            return self.synonyms[word_lower]
        elif word_lower in self.reverse_synonyms:
            return self.reverse_synonyms[word_lower]
        
        return []
    
    def add_custom_synonyms(self, word: str, synonyms: List[str]):
        """Add custom synonyms at runtime."""
        word_lower = word.lower()
        
        if word_lower not in self.synonyms:
            self.synonyms[word_lower] = []
        
        for syn in synonyms:
            syn_lower = syn.lower()
            if syn_lower not in self.synonyms[word_lower]:
                self.synonyms[word_lower].append(syn_lower)
            
            # Update reverse index
            if syn_lower not in self.reverse_synonyms:
                self.reverse_synonyms[syn_lower] = []
            if word_lower not in self.reverse_synonyms[syn_lower]:
                self.reverse_synonyms[syn_lower].append(word_lower)
        
        logger.info(f"Added custom synonyms for '{word}': {synonyms}")

