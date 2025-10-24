# Hybrid Search API Documentation

**Version:** 2.15.1  
**Base URL:** `https://your-api-domain.com`  
**Protocol:** HTTPS  
**Authentication:** Optional (API Key)

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)
7. [SDKs & Libraries](#sdks--libraries)

---

## Overview

The Hybrid Search API provides AI-powered semantic search capabilities for WordPress content. It combines traditional keyword search (TF-IDF) with modern AI reranking using Cerebras LLM to deliver highly relevant search results.

### Key Features

- **Hybrid Search**: Combines keyword matching with semantic understanding
- **AI Reranking**: Uses LLM to rerank results based on relevance
- **AI Answer Generation**: Generates comprehensive answers from search results
- **Query Expansion**: Automatically expands queries with synonyms
- **Real-time Indexing**: Supports real-time document indexing
- **Advanced Filtering**: Filter results by type, author, categories, and tags

---

## Authentication

Currently, the API is open for authorized domains. Future versions will require API keys.

### Headers (Future)

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

---

## Endpoints

### 1. Search Content

Perform a hybrid search on indexed content.

**Endpoint:** `POST /search`

#### Request Body

```json
{
  "query": "renewable energy solutions",
  "limit": 10,
  "include_answer": true,
  "ai_instructions": "Focus on technical details and cost analysis",
  "enable_ai_reranking": true,
  "ai_weight": 0.7,
  "ai_reranking_instructions": "Prioritize recent and authoritative sources",
  "filters": {
    "type": "post",
    "categories": ["technology", "environment"]
  }
}
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | ✅ Yes | - | Search query (2-500 characters) |
| `limit` | integer | ❌ No | 10 | Number of results (1-100) |
| `include_answer` | boolean | ❌ No | false | Generate AI answer from results |
| `ai_instructions` | string | ❌ No | "" | Custom instructions for AI answer |
| `enable_ai_reranking` | boolean | ❌ No | true | Enable AI reranking of results |
| `ai_weight` | float | ❌ No | 0.7 | AI score weight (0.0-1.0) |
| `ai_reranking_instructions` | string | ❌ No | "" | Custom reranking criteria |
| `filters` | object | ❌ No | null | Filter results (type, author, categories, tags) |
| `strict_ai_answer_mode` | boolean | ❌ No | true | Only use search results for answers |

#### Response

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "1234",
        "title": "Solar Energy: A Comprehensive Guide",
        "url": "https://example.com/solar-energy-guide",
        "excerpt": "Explore the latest solar energy technologies...",
        "type": "post",
        "date": "2024-01-15",
        "author": "John Doe",
        "categories": [
          {"id": "1", "name": "Technology", "slug": "technology"}
        ],
        "tags": [
          {"id": "10", "name": "Solar", "slug": "solar"}
        ],
        "score": 0.95,
        "ai_score": 0.93,
        "hybrid_score": 0.94,
        "ai_reason": "Directly addresses renewable energy with detailed technical analysis",
        "featured_image": "https://example.com/images/solar.jpg",
        "word_count": 1250,
        "relevance": "high"
      }
    ]
  },
  "metadata": {
    "query": "renewable energy solutions",
    "total_results": 25,
    "response_time": 245.6,
    "has_answer": true,
    "answer": "Based on the search results, renewable energy solutions include...",
    "request_id": "req_abc123",
    "ai_reranking_used": true,
    "ai_response_time": 1.2,
    "ai_tokens_used": 1500,
    "ai_cost": 0.00015,
    "ai_weight": 0.7,
    "tfidf_weight": 0.3
  },
  "message": "Search completed successfully"
}
```

#### Error Response

```json
{
  "success": false,
  "error": {
    "code": "INVALID_QUERY",
    "message": "Query must be at least 2 characters",
    "timestamp": "2024-01-15T10:30:45Z",
    "request_id": "req_abc123",
    "details": {
      "field": "query",
      "min_length": 2,
      "actual_length": 1
    }
  }
}
```

---

### 2. Index Content

Index WordPress content for search.

**Endpoint:** `POST /index`

#### Request Body

```json
{
  "force_reindex": false,
  "post_types": ["post", "page", "product"]
}
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `force_reindex` | boolean | ❌ No | false | Force reindexing even if index exists |
| `post_types` | array | ❌ No | null | Specific post types to index (null = all) |

#### Response

```json
{
  "success": true,
  "message": "Successfully indexed 250 documents",
  "indexed_count": 250,
  "total_count": 250,
  "processing_time": 45.3
}
```

---

### 3. Index Single Document

Index a single document (for real-time updates).

**Endpoint:** `POST /index-single`

#### Request Body

```json
{
  "document": {
    "id": "1234",
    "title": "New Article Title",
    "slug": "new-article-title",
    "type": "post",
    "url": "https://example.com/new-article",
    "date": "2024-01-15T10:30:45Z",
    "modified": "2024-01-15T10:30:45Z",
    "author": "John Doe",
    "categories": [],
    "tags": [],
    "excerpt": "This is a brief excerpt...",
    "content": "Full article content here...",
    "word_count": 500,
    "featured_image": "https://example.com/image.jpg"
  }
}
```

#### Response

```json
{
  "success": true,
  "message": "Successfully indexed: New Article Title"
}
```

---

### 4. Delete Document

Remove a document from the search index.

**Endpoint:** `DELETE /delete-document/{document_id}`

#### URL Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | ✅ Yes | Document ID to delete |

#### Response

```json
{
  "success": true,
  "message": "Successfully deleted document: 1234"
}
```

---

### 5. Health Check

Get API health status.

**Endpoint:** `GET /health`

#### Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45Z",
  "services": {
    "search_system": "healthy",
    "vector_db": "healthy",
    "llm_service": "healthy",
    "wordpress_client": "healthy"
  },
  "version": "2.15.1",
  "uptime": 345600
}
```

---

### 6. Quick Health Check

Fast health check endpoint (for load balancers).

**Endpoint:** `GET /health/quick`

#### Response

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:45Z"
}
```

---

### 7. Get Statistics

Get search and indexing statistics.

**Endpoint:** `GET /stats`

#### Response

```json
{
  "index_stats": {
    "collection_name": "wordpress_content",
    "total_documents": 1250,
    "indexed_vectors": 1250,
    "status": "green",
    "tfidf_fitted": true,
    "document_count": 1250
  },
  "service_info": {
    "api_version": "2.15.1",
    "max_search_results": 100,
    "search_timeout": 30
  }
}
```

---

### 8. Get Suggestions

Get query suggestions based on partial input.

**Endpoint:** `GET /suggest`

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | ✅ Yes | - | Partial query (min 2 chars) |
| `limit` | integer | ❌ No | 5 | Max suggestions (1-10) |

#### Response

```json
{
  "query": "renew",
  "suggestions": [
    "renewable energy",
    "renewable resources",
    "renewable power",
    "renewable technology",
    "renewable solutions"
  ],
  "count": 5
}
```

---

### 9. Delete Collection

Delete the entire search collection (admin only).

**Endpoint:** `DELETE /collection`

#### Response

```json
{
  "message": "Collection deleted successfully"
}
```

---

## Error Handling

### Error Response Format

All error responses follow a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "timestamp": "2024-01-15T10:30:45Z",
    "request_id": "req_abc123",
    "details": {
      "additional": "context"
    }
  }
}
```

### Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request |
| `INVALID_QUERY` | 400 | Invalid query parameters |
| `QUERY_TOO_SHORT` | 400 | Query below minimum length |
| `QUERY_TOO_LONG` | 400 | Query exceeds maximum length |
| `INVALID_LIMIT` | 400 | Invalid limit parameter |
| `INVALID_OFFSET` | 400 | Invalid offset parameter |
| `MISSING_PARAMETER` | 400 | Required parameter missing |
| `UNAUTHORIZED` | 401 | Authentication required |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |
| `SEARCH_FAILED` | 500 | Search operation failed |
| `INDEX_FAILED` | 500 | Indexing operation failed |
| `LLM_ERROR` | 500 | LLM service error |
| `DATABASE_ERROR` | 500 | Database error |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Rate Limiting

Rate limits are applied per IP address:

- **Search**: 60 requests/minute
- **Index**: 10 requests/minute
- **Suggestions**: 120 requests/minute

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1610712045
```

### Rate Limit Error

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please try again later.",
    "timestamp": "2024-01-15T10:30:45Z",
    "details": {
      "retry_after": 45
    }
  }
}
```

---

## Examples

### Example 1: Basic Search

```bash
curl -X POST https://your-api.com/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "WordPress plugins",
    "limit": 5
  }'
```

### Example 2: Search with AI Answer

```bash
curl -X POST https://your-api.com/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to optimize WordPress performance?",
    "limit": 10,
    "include_answer": true,
    "ai_instructions": "Provide step-by-step instructions"
  }'
```

### Example 3: Search with Custom Reranking

```bash
curl -X POST https://your-api.com/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SEO best practices",
    "limit": 10,
    "enable_ai_reranking": true,
    "ai_weight": 0.8,
    "ai_reranking_instructions": "Prioritize recent articles and actionable tips"
  }'
```

### Example 4: Filtered Search

```bash
curl -X POST https://your-api.com/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "technology",
    "limit": 20,
    "filters": {
      "type": "post",
      "categories": ["technology", "innovation"],
      "author": "John Doe"
    }
  }'
```

### Example 5: Index Content

```bash
curl -X POST https://your-api.com/index \
  -H "Content-Type: application/json" \
  -d '{
    "force_reindex": false,
    "post_types": ["post", "page"]
  }'
```

### Example 6: Python Client

```python
import requests

# Search with AI answer
response = requests.post('https://your-api.com/search', json={
    'query': 'renewable energy',
    'limit': 10,
    'include_answer': True,
    'enable_ai_reranking': True,
    'ai_weight': 0.7
})

data = response.json()
if data['success']:
    print(f"Found {data['metadata']['total_results']} results")
    print(f"AI Answer: {data['metadata']['answer']}")
    
    for result in data['data']['results']:
        print(f"- {result['title']} (score: {result['hybrid_score']:.2f})")
else:
    print(f"Error: {data['error']['message']}")
```

### Example 7: JavaScript/TypeScript Client

```typescript
interface SearchRequest {
  query: string;
  limit?: number;
  include_answer?: boolean;
  enable_ai_reranking?: boolean;
  ai_weight?: number;
}

interface SearchResponse {
  success: boolean;
  data?: {
    results: Array<any>;
  };
  metadata?: {
    total_results: number;
    answer?: string;
  };
  error?: {
    code: string;
    message: string;
  };
}

async function search(params: SearchRequest): Promise<SearchResponse> {
  const response = await fetch('https://your-api.com/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });
  
  return response.json();
}

// Usage
const results = await search({
  query: 'machine learning',
  limit: 15,
  include_answer: true,
  enable_ai_reranking: true,
  ai_weight: 0.75
});

if (results.success) {
  console.log(`Found ${results.metadata.total_results} results`);
  console.log(`Answer: ${results.metadata.answer}`);
}
```

---

## SDKs & Libraries

### Official SDKs

- **Python SDK**: `pip install hybrid-search-sdk`
- **JavaScript/TypeScript SDK**: `npm install hybrid-search-sdk`
- **PHP SDK**: `composer require hybrid-search/sdk`

### WordPress Plugin

The official WordPress plugin provides seamless integration:

```php
// WordPress shortcode
[hybrid_search]

// PHP usage
$search = HybridSearch\API\SearchAPI::getInstance();
$results = $search->search('query', ['limit' => 10]);
```

---

## Best Practices

### 1. Query Optimization

- Keep queries concise and specific
- Use quotation marks for exact phrases
- Leverage filters to narrow results

### 2. AI Reranking

- Use `ai_weight` between 0.6-0.8 for best results
- Provide specific `ai_reranking_instructions` for domain-specific needs
- Disable AI reranking for simple keyword searches

### 3. Performance

- Cache search results on your end
- Use pagination instead of large `limit` values
- Implement debouncing for search-as-you-type

### 4. Cost Optimization

- Disable `include_answer` when not needed
- Disable `enable_ai_reranking` for non-critical searches
- Use suggestions endpoint for autocomplete

---

## Support

- **Documentation**: https://docs.hybrid-search.com
- **Issues**: https://github.com/hybrid-search/issues
- **Email**: support@hybrid-search.com
- **Discord**: https://discord.gg/hybrid-search

---

## Changelog

### Version 2.15.1 (Latest)

- ✨ Added comprehensive error handling
- ✨ Added async/await for LLM calls
- ✨ Removed magic numbers, centralized constants
- 🐛 Fixed pagination deduplication
- 📚 Added comprehensive API documentation
- ⚡ Performance improvements in TF-IDF search

### Version 2.15.0

- ✨ AI reranking with customizable weights
- ✨ Query expansion support
- 🐛 Fixed zero-result handling
- ⚡ Improved caching

---

**Last Updated:** January 2024  
**API Version:** 2.15.1

