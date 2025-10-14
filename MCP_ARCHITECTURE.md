# MCP Integration Architecture

## Overview

This document explains how the MCP (Model Context Protocol) server integrates with your existing hybrid search system.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │  WordPress       │         │  AI Assistants   │                 │
│  │  Plugin          │         │  (Claude, etc.)  │                 │
│  │                  │         │                  │                 │
│  │  - Search UI     │         │  - MCP Client    │                 │
│  │  - Admin Panel   │         │  - Tool Calling  │                 │
│  │  - Analytics     │         │  - Context Mgmt  │                 │
│  └────────┬─────────┘         └────────┬─────────┘                 │
│           │                            │                             │
└───────────┼────────────────────────────┼─────────────────────────────┘
            │                            │
            │ HTTP/AJAX                  │ MCP Protocol (stdio/SSE)
            │                            │
┌───────────┼────────────────────────────┼─────────────────────────────┐
│           │     API LAYER              │                             │
├───────────┼────────────────────────────┼─────────────────────────────┤
│           ↓                            ↓                             │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │  FastAPI         │         │  MCP Server      │                 │
│  │  (main.py)       │         │  (mcp_server.py) │                 │
│  │                  │         │                  │                 │
│  │ POST /search     │◄────────┤ search_wordpress │                 │
│  │ POST /index      │         │ _content()       │                 │
│  │ GET  /stats      │         │ get_stats()      │                 │
│  │ GET  /suggest    │         │ expand_query()   │                 │
│  └────────┬─────────┘         └────────┬─────────┘                 │
│           │                            │                             │
│           │ Shared Components          │                             │
│           └────────────┬───────────────┘                             │
│                        │                                             │
└────────────────────────┼─────────────────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────────────────┐
│                        │  CORE LAYER                                 │
├────────────────────────┼─────────────────────────────────────────────┤
│                        ↓                                             │
│  ┌──────────────────────────────────────────────────────┐          │
│  │          SimpleHybridSearch                          │          │
│  │          (simple_hybrid_search.py)                   │          │
│  │                                                       │          │
│  │  • search()                                          │          │
│  │  • search_with_answer()                              │          │
│  │  • index_documents()                                 │          │
│  │  • get_stats()                                       │          │
│  └──────────────┬───────────────────┬───────────────────┘          │
│                 │                   │                               │
│     ┌───────────┼───────────────────┼──────────┐                   │
│     │           ↓                   ↓          │                   │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │ Qdrant   │  │ Cerebras │  │ LlamaIndex  │  │ WordPress    │   │
│  │ Manager  │  │ LLM      │  │ Orchestrator│  │ Client       │   │
│  └──────────┘  └──────────┘  └─────────────┘  └──────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────┼─────────────────────────────────────────────┐
│                        │  DATA LAYER                                 │
├────────────────────────┼─────────────────────────────────────────────┤
│                        ↓                                             │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐                │
│  │ Qdrant   │  │ WordPress    │  │ Analytics DB  │                │
│  │ Vector DB│  │ MySQL/Posts  │  │ (SQLite/MySQL)│                │
│  └──────────┘  └──────────────┘  └───────────────┘                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. MCP Server (`mcp_server.py`)

**Purpose:** Expose hybrid search functionality to AI assistants via MCP protocol

**Key Features:**
- Tool registration (6 tools)
- Async request handling
- Error handling and logging
- Service initialization

**Tools Exposed:**
```python
1. search_wordpress_content    # Basic hybrid search
2. search_with_answer          # Search + AI answer
3. get_search_stats            # Index statistics
4. index_wordpress_content     # Content indexing
5. get_document_by_id          # Retrieve specific doc
6. expand_query                # Query expansion
```

**Protocol:** stdio (standard input/output) for communication

### 2. FastAPI Service (`main.py`)

**Purpose:** HTTP API for WordPress plugin and web applications

**Endpoints:**
```
POST   /search           # Hybrid search
POST   /index            # Index content
POST   /index-single     # Index single doc
DELETE /delete-document  # Remove doc
GET    /stats            # Statistics
GET    /suggest          # Suggestions
GET    /health           # Health check
```

**Protocol:** HTTP/REST

### 3. Shared Core Components

Both the MCP server and FastAPI service use the same core components:

#### `SimpleHybridSearch`
- Main search orchestrator
- Combines semantic + keyword search
- AI reranking
- Result fusion

#### `CerebrasLLM`
- LLM integration
- Query processing
- Answer generation
- Reranking

#### `QdrantManager`
- Vector database operations
- Point insertion/deletion
- Collection management

#### `WordPressContentFetcher`
- Fetch posts, pages, custom types
- Transform to searchable documents
- Handle pagination

## Data Flow

### Search Request Flow (MCP)

```
1. User asks Claude: "Search for energy audits"
   
2. Claude calls MCP tool:
   tool: search_wordpress_content
   args: {query: "energy audits", limit: 10}
   
3. MCP Server (mcp_server.py):
   - Receives tool call
   - Validates arguments
   - Calls SimpleHybridSearch.search()
   
4. SimpleHybridSearch:
   - Generates embedding (OpenAI)
   - Semantic search (Qdrant)
   - Keyword search (BM25)
   - Fuses results
   - AI reranking (Cerebras)
   
5. Results returned to MCP Server:
   - Formats as JSON
   - Returns via MCP protocol
   
6. Claude receives results:
   - Parses result data
   - Presents to user
```

### Search Request Flow (WordPress Plugin)

```
1. User types in search box
   
2. JavaScript (hybrid-search.js):
   - Captures input
   - Debounced AJAX call
   
3. WordPress AJAX Handler:
   - Validates nonce
   - Forwards to FastAPI
   
4. FastAPI (main.py):
   POST /search
   - Receives HTTP request
   - Calls SimpleHybridSearch.search()
   
5. SimpleHybridSearch:
   - Same process as MCP flow
   
6. Results returned:
   - FastAPI → WordPress → JavaScript → UI
```

## Key Differences: MCP vs HTTP API

| Aspect | MCP Server | FastAPI Service |
|--------|------------|-----------------|
| **Protocol** | stdio/SSE | HTTP/REST |
| **Client** | AI assistants | WordPress, browsers |
| **Auth** | Environment-based | API keys, nonces |
| **Format** | MCP Tools | JSON endpoints |
| **Startup** | On-demand by client | Always running |
| **State** | Stateless | Session support |
| **Caching** | Client-side | Server-side |

## Communication Patterns

### MCP Communication

```python
# Client → Server (stdin)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_wordpress_content",
    "arguments": {
      "query": "environmental services",
      "limit": 5
    }
  }
}

# Server → Client (stdout)
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"results\": [...]}"
      }
    ]
  }
}
```

### HTTP Communication

```javascript
// Client → Server
POST /search HTTP/1.1
Content-Type: application/json

{
  "query": "environmental services",
  "limit": 5,
  "enable_ai_reranking": true
}

// Server → Client
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "results": [...],
  "metadata": {...}
}
```

## Deployment Scenarios

### Scenario 1: Production WordPress Site

```
┌──────────────┐
│ WordPress    │
│ + Plugin     │
└──────┬───────┘
       │ AJAX
       ↓
┌──────────────┐
│ FastAPI      │
│ (Railway/    │
│  Cloud)      │
└──────────────┘
```

### Scenario 2: Development with AI Assistant

```
┌──────────────┐
│ Claude       │
│ Desktop      │
└──────┬───────┘
       │ MCP
       ↓
┌──────────────┐
│ MCP Server   │
│ (Local)      │
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ Local Qdrant │
│ + Services   │
└──────────────┘
```

### Scenario 3: Both Running Together

```
┌──────────────┐     ┌──────────────┐
│ WordPress    │     │ Claude       │
│ Plugin       │     │ Desktop      │
└──────┬───────┘     └──────┬───────┘
       │ HTTP               │ MCP
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│ FastAPI      │     │ MCP Server   │
│ :8000        │     │ stdio        │
└──────┬───────┘     └──────┬───────┘
       │                    │
       └──────────┬─────────┘
                  │
                  ↓
       ┌──────────────────┐
       │ Shared Services  │
       │                  │
       │ • Qdrant         │
       │ • Cerebras LLM   │
       │ • WordPress DB   │
       └──────────────────┘
```

## Security Considerations

### MCP Server

✅ **Pros:**
- Runs locally (trusted environment)
- No network exposure
- Environment-based config

⚠️ **Considerations:**
- Ensure API keys are not logged
- Limit file system access
- Monitor resource usage

### FastAPI Service

✅ **Implemented:**
- CORS configuration
- Request validation
- Error handling

⚠️ **Consider Adding:**
- API key authentication
- Rate limiting
- Request logging
- IP whitelisting

## Performance Characteristics

### MCP Server

- **Cold Start:** ~2-5 seconds (service initialization)
- **Search Latency:** 200-500ms (typical)
- **Concurrent Requests:** Limited by stdio (sequential)
- **Memory:** Shared with core services

### FastAPI Service

- **Cold Start:** ~3-10 seconds (service initialization)
- **Search Latency:** 200-500ms (typical)
- **Concurrent Requests:** High (async workers)
- **Memory:** Dedicated process

## Monitoring & Debugging

### MCP Server Logs

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python mcp_server.py

# View in Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp-server-hybrid-search.log
```

### FastAPI Logs

```bash
# Run with verbose logging
uvicorn main:app --log-level debug

# View Railway logs
railway logs
```

## Future Enhancements

### Potential Improvements

1. **HTTP Bridge for MCP**
   - Allow MCP over HTTP (not just stdio)
   - Enable remote MCP clients

2. **Unified Analytics**
   - Track MCP usage alongside HTTP API
   - Combined dashboard

3. **Caching Layer**
   - Shared cache between MCP and FastAPI
   - Redis integration

4. **Advanced Tools**
   - Document summarization
   - Trend analysis
   - Semantic clustering

5. **Multi-tenancy**
   - Support multiple WordPress sites
   - Isolated indexes

## Testing

### Test MCP Integration

```bash
# 1. Test setup
./scripts/test_mcp_setup.sh --test

# 2. Test client
python test_mcp_client.py

# 3. Interactive mode
python test_mcp_client.py interactive
```

### Test HTTP API

```bash
# 1. Start server
python main.py

# 2. Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'
```

## Conclusion

The MCP integration adds a powerful new interface to your hybrid search system without modifying the core functionality. Both the MCP server and FastAPI service share the same robust search engine, providing consistent results across different clients and use cases.

**Key Benefits:**
- ✅ AI assistants can search your content
- ✅ No code duplication
- ✅ Consistent search quality
- ✅ Easy to maintain
- ✅ Flexible deployment options

For implementation details, see:
- [Quick Start Guide](MCP_QUICKSTART.md)
- [Full Integration Guide](MCP_INTEGRATION_GUIDE.md)
- [MCP Server Code](mcp_server.py)
- [Test Client](test_mcp_client.py)

