# Complete Search Logic - How It Works

## Overview
Your hybrid search system uses **TF-IDF + Vector embeddings + AI reranking + Post Type Priority** to return the most relevant results.

## Complete Search Flow

### 1. **Query Expansion** (Optional)
- Input: User query "environmental compliance"
- Process: Expands to related queries using synonyms
- Output: `["environmental compliance", "environmental audit", "regulatory compliance"]`
- Code: `simple_hybrid_search.py:361-370`

### 2. **Hybrid Search - TF-IDF + Vector**
- **TF-IDF Search**: Matches keywords in documents
- **Vector Search**: Uses semantic embeddings (sentence-transformers)
- Combines results from both methods
- Sorts by initial relevance score
- Code: `simple_hybrid_search.py:380-400`

### 3. **Post Type Priority** ⭐ **NEW**
- **Input**: Priority list like `['post', 'page', 'scs-professionals']`
- **Process**: Re-sorts results so higher priority post types appear first
- **Logic**: Within same score, 'post' appears before 'page'
- **Code**: `simple_hybrid_search.py:748-777` + `406-410
- **Example**:
  ```
  Before: [page: score=0.9, post: score=0.9, page: score=0.8]
  After:  [post: score=0.9, post: score=0.9, page: score=0.8, page: score=0.9]
  ```

### 4. **AI Reranking** (if enabled)
- **Input**: Top N candidates from previous step
- **Process**: LLM analyzes each result's relevance to the query
- **Scoring**: 
  - Semantic Relevance (40%)
  - User Intent (30%)
  - Content Quality (20%)
  - Specificity (10%)
  - **Custom AI Instructions** (highest priority)
- **Output**: Hybrid score combining TF-IDF + AI scores
- **Code**: `cerebras_llm.py:404-580`

### 5. **Pagination**
- Applies offset/limit to return the requested page
- Returns only the requested number of results
- Code: `simple_hybrid_search.py:432-442`

### 6. **WordPress Plugin Processing**
- Receives results from API
- Applies additional WordPress-specific filtering
- Returns to frontend
- Code: `wordpress-plugin/includes/API/SearchAPI.php`

## How to Ensure Correct Priority

### ✅ **Current Implementation**
1. **API accepts priority**: `post_type_priority` parameter in SearchRequest
2. **Priority applied early**: Before AI reranking, after initial TF-IDF search
3. **Preserved through AI**: Results maintain type information for AI to consider
4. **Final sorting**: Priority order enforced after AI reranking

### 📊 **Example Flow**

**Query**: "environmental compliance"
**Priority**: `['post', 'page']`

1. TF-IDF/Vector search returns 20 candidates with scores
2. Post type priority sorts them:
   ```
   post:0.95, page:0.95, post:0.90, page:0.90...
   ```
3. Top 10 go to AI reranking
4. AI scores them for semantic relevance
5. Hybrid scores combine: TF-IDF (30%) + AI (70%)
6. Final results maintain priority within score tiers
7. Return top 10 to WordPress

### 🔍 **How to Verify Priority Works**

Check the logs for:
```
Applying post type priority: ['post', 'page']
```

Or check the API response in WordPress logs:
```php
// wordpress-plugin/includes/API/SearchAPI.php:115
error_log('Hybrid Search: Request data being sent to Railway API: ' . json_encode($request_data));
```

## API Request Format

From WordPress plugin to Railway API:
```json
{
  "query": "environmental compliance",
  "limit": 10,
  "enable_ai_reranking": true,
  "ai_weight": 0.7,
  "ai_reranking_instructions": "Prioritize recent compliance documents",
  "post_type_priority": ["post", "page", "scs-professionals"]
}
```

## Search Result Structure

Each result contains:
```json
{
  "id": "12345",
  "title": "Environmental Compliance Guide",
  "url": "...",
  "type": "post",  // Used for priority sorting
  "score": 0.95,   // Final hybrid score
  "excerpt": "...",
  "categories": [],
  "tags": []
}
```

## Key Files

1. **API Endpoint**: `main.py:259-465` - Handles requests
2. **Search Logic**: `simple_hybrid_search.py:325-465` - Core search
3. **Priority Sorting**: `simple_hybrid_search.py:748-777` - Post type priority
4. **AI Reranking**: `cerebras_llm.py:404-580` - Semantic reranking
5. **WordPress Integration**: `wordpress-plugin/includes/API/SearchAPI.php` - Plugin

## Summary

✅ **TF-IDF + Vector** search for broad coverage
✅ **Post Type Priority** ensures important content types appear first  
✅ **AI Reranking** with custom instructions for semantic relevance
✅ **Pagination** for efficient result delivery
✅ **WordPress integration** handles additional WordPress-specific logic

Your search now combines keyword matching, semantic understanding, AI intelligence, and type priority to deliver the best results!

