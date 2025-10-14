# Hybrid Search System - Complete Architecture Diagram

## System Overview
A professional hybrid search system combining TF-IDF keyword search, semantic search, and AI reranking powered by Cerebras LLM.

---

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         HYBRID SEARCH SYSTEM FLOW                             ║
║                              Version 2.9.0                                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝


┌───────────────────────────────────────────────────────────────────────────────┐
│                          STEP 1: USER INTERACTION                             │
│                         (WordPress Frontend)                                  │
└───────────────────────────────────────────────────────────────────────────────┘

    👤 User enters query: "environmental compliance services"
                │
                │ (Browser)
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   WordPress Plugin Frontend                         │
    │   📁 wordpress-plugin/assets/js/hybrid-search.js    │
    │                                                      │
    │   • User types in search box                        │
    │   • Debounced autocomplete suggestions (optional)   │
    │   • Submit search query                             │
    │   • Display loading state                           │
    └─────────────────────────────────────────────────────┘
                │
                │ AJAX POST Request
                │ {
                │   query: "environmental compliance services",
                │   limit: 10,
                │   offset: 0,
                │   enable_ai_reranking: true,
                │   ai_weight: 0.7,
                │   include_answer: false
                │ }
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   WordPress Plugin AJAX Handler                     │
    │   📁 wordpress-plugin/includes/AJAX/AJAXManager.php │
    │                                                      │
    │   • Validate request                                │
    │   • Track analytics (query logged)                  │
    │   • Forward to backend API                          │
    └─────────────────────────────────────────────────────┘
                │
                │ HTTP POST (Railway/Cloud)
                │ https://your-api.railway.app/search
                ▼


┌───────────────────────────────────────────────────────────────────────────────┐
│                       STEP 2: BACKEND API PROCESSING                          │
│                         (FastAPI Service)                                     │
└───────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────┐
    │   FastAPI Endpoint: POST /search                    │
    │   📁 main.py                                        │
    │                                                      │
    │   • Receive search request                          │
    │   • Validate parameters                             │
    │   • Initialize timer for metrics                    │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   Optional: Query Analysis (LLM)                    │
    │   📁 cerebras_llm.py                                │
    │                                                      │
    │   • Analyze user intent (optional)                  │
    │   • Rewrite query if needed                         │
    │   • Extract key terms                               │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   Search System Orchestrator                        │
    │   📁 simple_hybrid_search.py                        │
    │                                                      │
    │   ➡️  Forward to hybrid search engine               │
    └─────────────────────────────────────────────────────┘
                │
                ▼


┌───────────────────────────────────────────────────────────────────────────────┐
│                    STEP 3: QUERY EXPANSION (Optional)                         │
│                       (Synonym & LLM-based)                                   │
└───────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────┐
    │   Query Expander                                    │
    │   📁 query_expander.py                              │
    │                                                      │
    │   Input: "environmental compliance services"        │
    │                                                      │
    │   Process:                                          │
    │   1. Dictionary-based synonym expansion             │
    │      • environmental → ecological, sustainability   │
    │      • compliance → regulatory, conformance         │
    │      • services → solutions, consulting             │
    │                                                      │
    │   2. Generate query variations:                     │
    │      ✓ "environmental compliance services"          │
    │      ✓ "ecological compliance services"             │
    │      ✓ "environmental regulatory services"          │
    │      ✓ "sustainability conformance solutions"       │
    │                                                      │
    │   Output: 3-5 query variations                      │
    └─────────────────────────────────────────────────────┘
                │
                ▼


┌───────────────────────────────────────────────────────────────────────────────┐
│                  STEP 4: TF-IDF KEYWORD SEARCH                                │
│                    (Initial Candidate Retrieval)                              │
└───────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────┐
    │   TF-IDF Vectorizer                                 │
    │   📁 simple_hybrid_search.py                        │
    │                                                      │
    │   Database: 2,892+ indexed documents                │
    │   Features: 10,000 TF-IDF features                  │
    │   N-grams: (1, 2) - unigrams & bigrams              │
    │                                                      │
    │   For EACH expanded query:                          │
    │   1. Transform query → TF-IDF vector                │
    │   2. Calculate cosine similarity vs all docs        │
    │   3. Get top N candidates                           │
    │   4. Combine & deduplicate results                  │
    └─────────────────────────────────────────────────────┘
                │
                │ Cosine Similarity Calculation
                │ similarity = query_vector · doc_vector
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   Top 30 Candidates Retrieved                       │
    │   (3× limit if AI reranking enabled)                │
    │                                                      │
    │   1. "Compliance Services" ........ Score: 0.92     │
    │   2. "Environmental Regs Guide" .... Score: 0.88    │
    │   3. "Regulatory Consulting" ....... Score: 0.85    │
    │   4. "Impact Assessment" ........... Score: 0.82    │
    │   5. "Training Programs" ........... Score: 0.78    │
    │   ...                                                │
    │   30. "General Engineering" ........ Score: 0.12    │
    │                                                      │
    │   Results sorted by TF-IDF score (descending)       │
    └─────────────────────────────────────────────────────┘
                │
                ▼


┌───────────────────────────────────────────────────────────────────────────────┐
│                    STEP 5: AI RERANKING (Optional)                            │
│                      (Cerebras LLM - llama-3.3-70b)                           │
└───────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────┐
    │   AI Reranking Decision                             │
    │                                                      │
    │   IF enable_ai_reranking == true:                   │
    │      ✅ Proceed with AI reranking                   │
    │   ELSE:                                             │
    │      ⏭️  Skip to STEP 7 (return TF-IDF results)    │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   Prepare LLM Prompt                                │
    │   📁 cerebras_llm.py → rerank_results()             │
    │                                                      │
    │   • Take top 20 candidates                          │
    │   • Format results with ID, title, excerpt          │
    │   • Include TF-IDF scores                           │
    │   • Add custom reranking instructions (if any)      │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   Cerebras API Call                                 │
    │   🌐 https://api.cerebras.ai/v1/chat/completions    │
    │                                                      │
    │   Model: llama-3.3-70b                              │
    │   Temperature: 0.1 (deterministic)                  │
    │   Max Tokens: 2000                                  │
    │                                                      │
    │   System Prompt:                                    │
    │   "You are an expert search relevance analyzer.     │
    │    Score each result 0-100 based on:               │
    │    • Semantic Relevance (40%)                       │
    │    • User Intent Match (30%)                        │
    │    • Content Quality (20%)                          │
    │    • Specificity (10%)"                             │
    │                                                      │
    │   User Prompt:                                      │
    │   "Analyze these results for:                       │
    │    'environmental compliance services'              │
    │                                                      │
    │    Result 1 (ID: 123):                              │
    │    Title: Compliance Services Overview              │
    │    Excerpt: Comprehensive environmental...          │
    │    TF-IDF: 0.92                                     │
    │                                                      │
    │    Result 2 (ID: 456):                              │
    │    Title: Environmental Regulations Guide           │
    │    Excerpt: Detailed guide to...                    │
    │    TF-IDF: 0.88                                     │
    │    ...                                              │
    │                                                      │
    │    Return JSON: [                                   │
    │      {id: '123', ai_score: 88, reason: '...'},     │
    │      {id: '456', ai_score: 96, reason: '...'}      │
    │    ]"                                               │
    └─────────────────────────────────────────────────────┘
                │
                │ LLM Processing (~1-2 seconds)
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   AI Scores Received                                │
    │                                                      │
    │   [                                                  │
    │     {                                                │
    │       id: "456",                                     │
    │       ai_score: 96,                                  │
    │       reason: "Comprehensive regulatory guide..."   │
    │     },                                               │
    │     {                                                │
    │       id: "123",                                     │
    │       ai_score: 88,                                  │
    │       reason: "Service-focused, highly relevant..." │
    │     },                                               │
    │     ...                                              │
    │   ]                                                  │
    │                                                      │
    │   Tokens Used: ~1,500-2,000                         │
    │   Cost: ~$0.00015-$0.0002 per search                │
    │   Response Time: 1-2 seconds                        │
    └─────────────────────────────────────────────────────┘
                │
                ▼


┌───────────────────────────────────────────────────────────────────────────────┐
│                     STEP 6: HYBRID SCORE CALCULATION                          │
│                        (Weighted Combination)                                 │
└───────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────┐
    │   Hybrid Scoring Formula                            │
    │                                                      │
    │   For each result:                                  │
    │                                                      │
    │   hybrid_score = (tfidf_score × tfidf_weight)       │
    │                + (ai_score × ai_weight)             │
    │                                                      │
    │   Where:                                            │
    │   • tfidf_weight = 1 - ai_weight                    │
    │   • ai_weight = 0.7 (default, configurable)         │
    │   • ai_score normalized to 0-1 (÷ 100)              │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   Example Calculations:                             │
    │                                                      │
    │   Result ID: 456                                    │
    │   ┌───────────────────────────────────────────┐    │
    │   │ TF-IDF Score:  0.88                        │    │
    │   │ AI Score:      0.96 (96 ÷ 100)            │    │
    │   │ AI Weight:     0.7                         │    │
    │   │                                            │    │
    │   │ Hybrid = (0.88 × 0.3) + (0.96 × 0.7)      │    │
    │   │        = 0.264 + 0.672                     │    │
    │   │        = 0.936 ⭐ (RANK #1)               │    │
    │   └───────────────────────────────────────────┘    │
    │                                                      │
    │   Result ID: 123                                    │
    │   ┌───────────────────────────────────────────┐    │
    │   │ TF-IDF Score:  0.92                        │    │
    │   │ AI Score:      0.88                        │    │
    │   │                                            │    │
    │   │ Hybrid = (0.92 × 0.3) + (0.88 × 0.7)      │    │
    │   │        = 0.276 + 0.616                     │    │
    │   │        = 0.892 (RANK #2)                   │    │
    │   └───────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   Sort by Hybrid Score (Descending)                 │
    │   Take Top N Results (limit = 10)                   │
    └─────────────────────────────────────────────────────┘
                │
                ▼


┌───────────────────────────────────────────────────────────────────────────────┐
│                      STEP 7: RESPONSE FORMATTING                              │
│                         (API Response)                                        │
└───────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────┐
    │   Build JSON Response                               │
    │   📁 main.py                                        │
    │                                                      │
    │   {                                                  │
    │     "success": true,                                │
    │     "results": [                                    │
    │       {                                             │
    │         "id": "456",                                │
    │         "title": "Environmental Regulations Guide", │
    │         "url": "https://site.com/env-regs",        │
    │         "excerpt": "Detailed guide...",            │
    │         "type": "post",                            │
    │         "date": "2024-01-15",                      │
    │         "author": "SCS Engineers",                │
    │         "categories": [...],                       │
    │         "tags": [...],                             │
    │         "score": 0.936,                            │
    │         "relevance": "high"                        │
    │       },                                            │
    │       ...9 more results                            │
    │     ],                                              │
    │     "pagination": {                                │
    │       "offset": 0,                                 │
    │       "limit": 10,                                 │
    │       "has_more": true,                            │
    │       "next_offset": 10,                           │
    │       "total_results": 30                          │
    │     },                                              │
    │     "metadata": {                                  │
    │       "query": "environmental compliance services",│
    │       "total_results": 30,                         │
    │       "returned_results": 10,                      │
    │       "response_time": 1420,  // milliseconds     │
    │       "ai_reranking_used": true,                  │
    │       "ai_weight": 0.7,                            │
    │       "tfidf_weight": 0.3                          │
    │     }                                               │
    │   }                                                 │
    └─────────────────────────────────────────────────────┘
                │
                │ HTTP Response (200 OK)
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   WordPress Plugin Receives Response                │
    │   📁 includes/AJAX/AJAXManager.php                  │
    │                                                      │
    │   • Parse JSON response                             │
    │   • Track analytics (CTR, result clicks)            │
    │   • Cache results (optional)                        │
    │   • Forward to frontend                             │
    └─────────────────────────────────────────────────────┘
                │
                ▼


┌───────────────────────────────────────────────────────────────────────────────┐
│                       STEP 8: FRONTEND DISPLAY                                │
│                         (WordPress UI)                                        │
└───────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────┐
    │   JavaScript Rendering                              │
    │   📁 assets/js/hybrid-search.js                     │
    │                                                      │
    │   • Hide loading state                              │
    │   • Clear previous results                          │
    │   • Render search results with:                     │
    │     - Title (linked)                                │
    │     - Excerpt                                       │
    │     - Metadata (date, author, type)                 │
    │     - Relevance indicator                           │
    │   • Render pagination controls                      │
    │   • Show metadata (response time, count)            │
    │   • Highlight query terms (optional)                │
    │   • Track result clicks for analytics               │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    ┌─────────────────────────────────────────────────────┐
    │   User Sees Results                                 │
    │   ════════════════════════════════════════════      │
    │                                                      │
    │   🔍 Search Results (10 of 30)                      │
    │   ⚡ Found in 1.42 seconds                          │
    │                                                      │
    │   ┌────────────────────────────────────────────┐   │
    │   │ 📄 Environmental Regulations Guide         │   │
    │   │ 🔗 https://site.com/env-regs               │   │
    │   │                                            │   │
    │   │ Detailed guide to environmental            │   │
    │   │ regulations and compliance requirements... │   │
    │   │                                            │   │
    │   │ 📅 Jan 15, 2024 | ✍️ SCS Engineers        │   │
    │   │ 🎯 Relevance: High (93.6%)                │   │
    │   └────────────────────────────────────────────┘   │
    │                                                      │
    │   ┌────────────────────────────────────────────┐   │
    │   │ 📄 Compliance Services Overview            │   │
    │   │ ...                                        │   │
    │   └────────────────────────────────────────────┘   │
    │                                                      │
    │   ... (8 more results)                              │
    │                                                      │
    │   ◀ Previous  |  1 [2] 3  |  Next ▶               │
    └─────────────────────────────────────────────────────┘
                │
                ▼
    👤 User clicks result → Analytics tracked (CTR)
                │
                ▼
    📊 Analytics stored in WordPress database
```

---

## Component Details

### 1. WordPress Plugin Components

```
wordpress-plugin/
├── hybrid-search.php              # Main plugin file
├── includes/
│   ├── API/
│   │   ├── APIClient.php          # HTTP client for backend API
│   │   └── SearchAPI.php          # Search API wrapper
│   ├── AJAX/
│   │   └── AJAXManager.php        # Handle AJAX search requests
│   ├── Admin/
│   │   ├── AdminManager.php       # Admin settings page
│   │   └── DashboardWidget.php    # Analytics dashboard
│   ├── Database/
│   │   ├── AnalyticsRepository.php # Search analytics storage
│   │   └── CTRRepository.php      # Click-through rate tracking
│   ├── Services/
│   │   ├── CacheService.php       # Result caching
│   │   ├── SmartCacheService.php  # Smart cache invalidation
│   │   └── AutoIndexService.php   # Auto-index on content update
│   └── Frontend/
│       ├── FrontendManager.php    # Frontend integration
│       └── ShortcodeManager.php   # [hybrid_search] shortcode
└── assets/
    ├── js/
    │   ├── hybrid-search.js       # Main search UI logic
    │   ├── hybrid-search-ui.js    # UI components
    │   └── hybrid-search-autocomplete.js # Autocomplete
    └── css/
        └── hybrid-search-enhanced.css # Styles
```

### 2. Backend API Components

```
Backend (Python/FastAPI)
├── main.py                        # FastAPI app & endpoints
├── simple_hybrid_search.py        # Main search engine
├── cerebras_llm.py               # AI reranking & answers
├── query_expander.py             # Query expansion
├── qdrant_manager.py             # Vector database client
├── wordpress_client.py           # WordPress content fetcher
├── content_chunker.py            # Document chunking
├── zero_result_handler.py        # Handle zero results
└── suggestions.py                # Autocomplete suggestions
```

---

## Data Flow Diagram

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ (1) User Query
       ▼
┌─────────────────────────────────────┐
│   WordPress Plugin (Frontend)       │
│   - Search UI                       │
│   - AJAX Handler                    │
│   - Analytics Tracking              │
└──────┬──────────────────────────────┘
       │
       │ (2) HTTP POST /search
       ▼
┌─────────────────────────────────────┐
│   FastAPI Backend (main.py)         │
│   - Request validation              │
│   - Query processing                │
│   - Response formatting             │
└──────┬──────────────────────────────┘
       │
       │ (3) search()
       ▼
┌─────────────────────────────────────┐
│   Hybrid Search Engine              │
│   - Query expansion                 │
│   - TF-IDF search                   │
│   - AI reranking                    │
└──────┬──────────────────────────────┘
       │
       ├─────────────────┬──────────────┬─────────────┐
       │                 │              │             │
       ▼                 ▼              ▼             ▼
┌─────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│   Qdrant    │  │  Cerebras    │  │  Query   │  │  TF-IDF  │
│   Vector    │  │    LLM       │  │ Expander │  │ Vectors  │
│   Database  │  │   (AI API)   │  │          │  │          │
└─────────────┘  └──────────────┘  └──────────┘  └──────────┘
    (Optional)      (Reranking)      (Synonyms)   (Keywords)
```

---

## Indexing Flow

```
╔═══════════════════════════════════════════════════════════════╗
║                    CONTENT INDEXING FLOW                      ║
╚═══════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────┐
│  TRIGGER: Manual Reindex OR Auto-Index (on post save)       │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  WordPress Content Fetcher (wordpress_client.py)            │
│                                                              │
│  • Fetch all posts, pages, custom post types               │
│  • Extract: title, content, excerpt, metadata              │
│  • Filter by post status (published only)                  │
│                                                              │
│  Output: List of documents                                  │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Content Chunker (content_chunker.py)                       │
│                                                              │
│  • Split long documents into chunks                         │
│  • Chunk size: 1000 chars                                   │
│  • Overlap: 200 chars (preserve context)                    │
│  • Maintain metadata for each chunk                         │
│                                                              │
│  Example:                                                    │
│  Long article (5000 chars) → 5-6 chunks                    │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  TF-IDF Vectorization                                        │
│                                                              │
│  • Fit TF-IDF vectorizer on all chunks                      │
│  • Generate sparse vectors (10,000 features)                │
│  • Store for keyword search                                 │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Optional: Semantic Embeddings                               │
│                                                              │
│  • Generate 384-dim embeddings (Sentence Transformers)      │
│  • Store in Qdrant vector database                          │
│  • Enable semantic search (future feature)                  │
└─────────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│  Index Status: ✅ Ready for Search                          │
│                                                              │
│  📊 Statistics:                                              │
│  • Total documents indexed: 2,892                           │
│  • Total chunks: 3,450+                                     │
│  • Index size: ~50 MB                                       │
│  • Time to index: ~2-3 minutes                              │
└─────────────────────────────────────────────────────────────┘
```

---

## AI Reranking Details

### Why AI Reranking?

**Problem with TF-IDF alone:**
- Only matches keywords, not meaning
- "environmental compliance" vs "regulatory requirements" → missed semantic similarity
- Can't understand user intent or context

**Solution: Hybrid TF-IDF + AI**
- TF-IDF gets high-recall candidates (fast, broad)
- AI reranks for precision (slower, but only top N)
- Best of both worlds: speed + intelligence

### Reranking Algorithm

```python
# 1. Get initial candidates (fast)
candidates = tfidf_search(query, limit=30)  # 3× requested limit

# 2. Take top 20 for AI reranking
top_candidates = candidates[:20]

# 3. Get AI scores
ai_scores = llm.rerank(query, top_candidates)
# Returns: [{"id": "123", "ai_score": 88, "reason": "..."}, ...]

# 4. Calculate hybrid scores
for result in top_candidates:
    tfidf_score = result['score']
    ai_score = ai_scores[result['id']] / 100  # normalize
    
    hybrid_score = (tfidf_score × 0.3) + (ai_score × 0.7)
    result['hybrid_score'] = hybrid_score

# 5. Sort by hybrid score
results = sorted(top_candidates, key=lambda x: x['hybrid_score'], reverse=True)

# 6. Return top N
return results[:10]
```

### Cost & Performance

| Metric | Value |
|--------|-------|
| **Model** | Cerebras llama-3.3-70b |
| **Tokens per search** | 1,500-2,000 |
| **Cost per search** | $0.00015-$0.0002 |
| **Response time** | 1-2 seconds |
| **Monthly cost (10K searches)** | ~$1.50-$2.00 |

---

## Configuration Options

### WordPress Admin Settings

```
Settings → Hybrid Search

┌───────────────────────────────────────────────────────┐
│  Backend API Configuration                            │
│  ────────────────────────────────────────────────     │
│  API URL: https://your-api.railway.app               │
│  API Timeout: 30 seconds                              │
│  [Test Connection]                                    │
├───────────────────────────────────────────────────────┤
│  Search Settings                                      │
│  ────────────────────────────────────────────────     │
│  ☑ Enable AI Reranking                               │
│  AI Weight: 70% ████████████████░░░░░░░░ 100%        │
│  Results per page: 10                                 │
│  Enable query expansion: ☑                           │
├───────────────────────────────────────────────────────┤
│  Custom AI Instructions (Optional)                    │
│  ────────────────────────────────────────────────     │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Prioritize recent content and case studies      │ │
│  └─────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────┤
│  Analytics                                            │
│  ────────────────────────────────────────────────     │
│  ☑ Track search analytics                            │
│  ☑ Track click-through rates (CTR)                   │
│  Analytics retention: 90 days                         │
└───────────────────────────────────────────────────────┘
```

---

## Key Features

### ✅ Implemented Features

1. **Hybrid Search**
   - TF-IDF keyword search
   - AI reranking with Cerebras LLM
   - Configurable weights

2. **Query Enhancement**
   - Synonym-based expansion
   - LLM-based query rewriting
   - Multi-query search

3. **Content Management**
   - Auto-indexing on content updates
   - Manual reindex via admin
   - Chunking for long documents

4. **Analytics**
   - Search query tracking
   - Click-through rate (CTR)
   - Zero-result tracking
   - Admin dashboard with stats

5. **Performance**
   - Smart caching
   - Pagination support
   - Response time tracking

6. **User Experience**
   - Autocomplete suggestions
   - Real-time search
   - Professional UI
   - Relevance indicators

### 🔜 Future Enhancements

- Semantic search with embeddings (Qdrant)
- Faceted search (filter by type, date, author)
- Natural language answers (LLM-generated)
- A/B testing for reranking weights
- MCP (Model Context Protocol) integration

---

## API Endpoints

### Search Endpoint

```
POST /search
Content-Type: application/json

Request:
{
  "query": "environmental compliance services",
  "limit": 10,
  "offset": 0,
  "enable_ai_reranking": true,
  "ai_weight": 0.7,
  "ai_reranking_instructions": "",
  "include_answer": false
}

Response:
{
  "success": true,
  "results": [...],
  "pagination": {...},
  "metadata": {
    "query": "environmental compliance services",
    "total_results": 30,
    "returned_results": 10,
    "response_time": 1420,
    "ai_reranking_used": true,
    "ai_weight": 0.7
  }
}
```

### Index Endpoint

```
POST /index
Content-Type: application/json

Request:
{
  "force_reindex": false,
  "post_types": ["post", "page"]
}

Response:
{
  "success": true,
  "message": "Successfully indexed 2,892 documents",
  "indexed_count": 2892,
  "total_count": 2892,
  "processing_time": 145.23
}
```

### Other Endpoints

- `GET /health` - Health check
- `GET /stats` - Index statistics
- `GET /suggest?query=env` - Autocomplete suggestions
- `POST /index-single` - Index single document
- `DELETE /delete-document/{id}` - Delete document

---

## Technology Stack

### Frontend (WordPress)
- **Language**: PHP 7.4+
- **Framework**: WordPress 5.0+
- **JavaScript**: Vanilla JS (ES6+)
- **CSS**: Custom CSS with modern features
- **AJAX**: WordPress REST API compatible

### Backend (API)
- **Language**: Python 3.9+
- **Framework**: FastAPI
- **Search**: scikit-learn (TF-IDF)
- **Vector DB**: Qdrant (optional)
- **LLM**: Cerebras AI (llama-3.3-70b)
- **Async**: asyncio, httpx

### Infrastructure
- **Hosting**: Railway (or any cloud)
- **Database**: Qdrant Cloud (vector storage)
- **Cache**: Redis (optional, future)
- **CDN**: Cloudflare (optional)

---

## Performance Metrics

### Search Performance

| Metric | Target | Actual |
|--------|--------|--------|
| **Search latency (no AI)** | < 200ms | 150-200ms |
| **Search latency (with AI)** | < 2s | 1.4-2s |
| **Index size** | N/A | ~50 MB |
| **Documents indexed** | N/A | 2,892+ |
| **Throughput** | 100 req/s | 50-100 req/s |

### Cost Metrics

| Item | Monthly Cost |
|------|-------------|
| **Cerebras API** (10K searches) | $1.50-$2.00 |
| **Railway hosting** | $5-$20 |
| **Qdrant Cloud** (optional) | $0-$25 |
| **Total** | ~$6.50-$47/month |

---

## Monitoring & Debugging

### Health Checks

```bash
# Check API health
curl https://your-api.railway.app/health

# Check index stats
curl https://your-api.railway.app/stats
```

### Logs

```bash
# Backend logs (Railway)
railway logs

# WordPress logs
tail -f wp-content/debug.log
```

### Admin Dashboard

WordPress Admin → Dashboard → Hybrid Search Widget

Shows:
- Total searches (last 30 days)
- Top queries
- Zero-result queries
- Average response time
- AI reranking usage %

---

**End of Architecture Document**

