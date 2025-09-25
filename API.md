# Hybrid Search API Documentation

## Overview

The Hybrid Search API provides advanced search capabilities for WordPress content using a combination of dense vector search, sparse keyword matching, and LLM-powered query processing.

## Base URL

- **Local Development**: `http://localhost:8000`
- **Production**: `https://your-api.railway.app`

## Authentication

Currently, the API does not require authentication for basic operations. Future versions may include API key authentication.

## Endpoints

### 1. Health Check

Check the health status of the API and its dependencies.

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "qdrant": "healthy",
    "cerebras_llm": "healthy",
    "wordpress": "initialized"
  }
}
```

**Status Codes:**
- `200`: All services healthy
- `503`: Service unavailable

---

### 2. Search

Perform hybrid search on indexed content.

```http
POST /search
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "machine learning tutorials",
  "limit": 10,
  "include_answer": false,
  "filters": {
    "type": "post",
    "author": "john_doe",
    "categories": ["technology", "programming"],
    "tags": ["python", "ai"]
  }
}
```

**Parameters:**
- `query` (string, required): Search query
- `limit` (integer, optional): Maximum results (1-50, default: 10)
- `include_answer` (boolean, optional): Include AI-generated answer
- `filters` (object, optional): Search filters

**Response:**
```json
{
  "query": "machine learning tutorials",
  "results": [
    {
      "id": 123,
      "title": "Introduction to Machine Learning",
      "slug": "introduction-machine-learning",
      "type": "post",
      "url": "https://example.com/introduction-machine-learning/",
      "date": "2024-01-10T08:00:00Z",
      "modified": "2024-01-12T14:30:00Z",
      "author": "John Doe",
      "categories": [
        {
          "id": 5,
          "name": "Technology",
          "slug": "technology"
        }
      ],
      "tags": [
        {
          "id": 12,
          "name": "Python",
          "slug": "python"
        }
      ],
      "excerpt": "Learn the fundamentals of machine learning...",
      "content": "Machine learning is a subset of artificial intelligence...",
      "score": 0.85,
      "relevance": "high"
    }
  ],
  "total_results": 1,
  "processing_time": 0.245,
  "answer": "Machine learning tutorials cover fundamental concepts...",
  "query_analysis": {
    "original_query": "machine learning tutorials",
    "rewritten_query": "machine learning tutorial guide introduction",
    "expanded_queries": [
      "machine learning tutorials",
      "ML tutorial guide",
      "artificial intelligence learning"
    ],
    "intent_classification": {
      "intent_type": "informational",
      "complexity": "moderate",
      "result_type": "tutorial",
      "domain": "technology",
      "time_sensitivity": "evergreen"
    }
  }
}
```

**Status Codes:**
- `200`: Search successful
- `400`: Invalid request
- `500`: Search failed

---

### 3. Index Content

Index WordPress content for search.

```http
POST /index
Content-Type: application/json
```

**Request Body:**
```json
{
  "force_reindex": false
}
```

**Parameters:**
- `force_reindex` (boolean, optional): Force reindexing even if index exists

**Response:**
```json
{
  "success": true,
  "message": "Successfully indexed 150 documents",
  "documents_indexed": 150,
  "processing_time": 45.2
}
```

**Status Codes:**
- `200`: Indexing successful
- `404`: No content found
- `500`: Indexing failed

---

### 4. Statistics

Get indexing and search statistics.

```http
GET /stats
```

**Response:**
```json
{
  "index_stats": {
    "collection_name": "wordpress_content",
    "total_documents": 150,
    "indexed_vectors": 150,
    "status": "green"
  },
  "service_info": {
    "api_version": "1.0.0",
    "max_search_results": 10,
    "search_timeout": 30
  }
}
```

**Status Codes:**
- `200`: Statistics retrieved
- `503`: Service not initialized

---

### 5. Query Suggestions

Get query suggestions based on partial input.

```http
GET /suggest?query=partial&limit=5
```

**Parameters:**
- `query` (string, required): Partial query for suggestions
- `limit` (integer, optional): Maximum suggestions (1-10, default: 5)

**Response:**
```json
{
  "query": "machine",
  "suggestions": [
    "machine learning",
    "machine learning tutorials",
    "machine learning algorithms",
    "machine learning python",
    "machine learning basics"
  ]
}
```

**Status Codes:**
- `200`: Suggestions retrieved
- `400`: Invalid parameters
- `503`: LLM service unavailable

---

## Search Filters

### Content Type Filter
```json
{
  "filters": {
    "type": "post"  // or "page"
  }
}
```

### Author Filter
```json
{
  "filters": {
    "author": "john_doe"
  }
}
```

### Category Filter
```json
{
  "filters": {
    "categories": ["technology", "programming"]
  }
}
```

### Tag Filter
```json
{
  "filters": {
    "tags": ["python", "ai", "tutorial"]
  }
}
```

### Combined Filters
```json
{
  "filters": {
    "type": "post",
    "author": "john_doe",
    "categories": ["technology"],
    "tags": ["python"]
  }
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request parameters",
  "status_code": 400,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 404 Not Found
```json
{
  "error": "No content found in WordPress",
  "status_code": 404,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 500 Internal Server Error
```json
{
  "error": "Search failed: Connection timeout",
  "status_code": 500,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 503 Service Unavailable
```json
{
  "error": "Search service not initialized",
  "status_code": 503,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Rate Limits

Currently, no rate limits are enforced. Future versions may include:
- 100 requests per minute per IP
- 1000 requests per hour per API key

## Response Times

Typical response times:
- **Health Check**: < 100ms
- **Search**: 200-500ms
- **Indexing**: 30-60 seconds (depends on content size)
- **Statistics**: < 50ms
- **Suggestions**: 100-300ms

## Examples

### Basic Search
```bash
curl -X POST https://your-api.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "python programming", "limit": 5}'
```

### Search with AI Answer
```bash
curl -X POST https://your-api.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how to optimize WordPress performance",
    "include_answer": true,
    "limit": 3
  }'
```

### Filtered Search
```bash
curl -X POST https://your-api.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tutorials",
    "filters": {
      "type": "post",
      "categories": ["programming", "tutorials"]
    }
  }'
```

### Get Suggestions
```bash
curl "https://your-api.railway.app/suggest?query=machine&limit=3"
```

### Index Content
```bash
curl -X POST https://your-api.railway.app/index \
  -H "Content-Type: application/json" \
  -d '{"force_reindex": true}'
```

## SDK Examples

### Python
```python
import requests

# Basic search
response = requests.post('https://your-api.railway.app/search', json={
    'query': 'machine learning',
    'limit': 10
})

results = response.json()
print(f"Found {results['total_results']} results")

# Search with answer
response = requests.post('https://your-api.railway.app/search', json={
    'query': 'how to deploy WordPress',
    'include_answer': True
})

data = response.json()
print(f"Answer: {data['answer']}")
```

### JavaScript
```javascript
// Basic search
const response = await fetch('https://your-api.railway.app/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'machine learning',
    limit: 10
  })
});

const results = await response.json();
console.log(`Found ${results.total_results} results`);
```

### PHP
```php
<?php
// Basic search
$data = [
    'query' => 'machine learning',
    'limit' => 10
];

$options = [
    'http' => [
        'header' => "Content-type: application/json\r\n",
        'method' => 'POST',
        'content' => json_encode($data)
    ]
];

$context = stream_context_create($options);
$result = file_get_contents('https://your-api.railway.app/search', false, $context);
$response = json_decode($result, true);

echo "Found " . $response['total_results'] . " results";
?>
```

## Webhook Support

Future versions may include webhook support for:
- Content indexing events
- Search analytics
- Error notifications

## Changelog

### v1.0.0
- Initial release
- Hybrid search functionality
- WordPress integration
- AI-powered query processing
- Railway deployment support
