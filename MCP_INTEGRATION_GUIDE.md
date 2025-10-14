# MCP Integration Guide for Hybrid Search

## Overview

This guide shows you how to integrate the Model Context Protocol (MCP) server with your hybrid search system, allowing AI assistants like Claude to directly query your WordPress content.

## What is MCP?

MCP (Model Context Protocol) is Anthropic's protocol for connecting AI assistants to external tools and data sources. By creating an MCP server, you can expose your hybrid search functionality to Claude and other AI tools.

## Architecture

```
┌─────────────────┐
│   AI Assistant  │ (Claude)
│    (Client)     │
└────────┬────────┘
         │ MCP Protocol
         │ (stdio/SSE)
         ↓
┌─────────────────┐
│   MCP Server    │ (mcp_server.py)
│  hybrid-search  │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────┐
│     Hybrid Search System            │
├─────────────────────────────────────┤
│  • SimpleHybridSearch               │
│  • Qdrant Vector Database           │
│  • Cerebras LLM                     │
│  • WordPress Content Fetcher        │
└─────────────────────────────────────┘
```

## Installation

### 1. Install MCP SDK

```bash
pip install mcp
```

### 2. Update requirements.txt

Add to your `requirements.txt`:

```
# MCP Server Support
mcp==0.9.0
```

### 3. Configure Environment Variables

Make sure your `.env` file has all required variables:

```env
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-key  # Optional

# Cerebras LLM
CEREBRAS_API_KEY=your-cerebras-key
CEREBRAS_API_BASE=https://api.cerebras.ai/v1

# OpenAI (for embeddings)
OPENAI_API_KEY=your-openai-key

# WordPress
WORDPRESS_URL=https://www.scsengineers.com
WORDPRESS_API_URL=https://www.scsengineers.com/wp-json/wp/v2
WORDPRESS_USERNAME=your-username
WORDPRESS_PASSWORD=your-password
```

## Available MCP Tools

The MCP server exposes the following tools:

### 1. `search_wordpress_content`

Search WordPress content using hybrid search with AI reranking.

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, 1-50, default: 10): Maximum number of results
- `enable_ai_reranking` (boolean, default: true): Use AI reranking
- `ai_weight` (number, 0.0-1.0, default: 0.7): Weight for AI score

**Example:**
```json
{
  "query": "energy audit services",
  "limit": 5,
  "enable_ai_reranking": true,
  "ai_weight": 0.7
}
```

### 2. `search_with_answer`

Search and get an AI-generated answer based on results.

**Parameters:**
- `query` (string, required): The search query
- `limit` (integer, default: 10): Maximum results to consider
- `custom_instructions` (string, optional): Custom AI instructions

**Example:**
```json
{
  "query": "What are SCS Engineers' environmental services?",
  "limit": 10,
  "custom_instructions": "Focus on sustainability practices"
}
```

### 3. `get_search_stats`

Get statistics about indexed content.

**Parameters:** None

**Returns:**
- Total documents
- Collection information
- System configuration

### 4. `index_wordpress_content`

Index or reindex WordPress content.

**Parameters:**
- `force_reindex` (boolean, default: false): Force reindexing
- `post_types` (array, optional): Specific post types to index

**Example:**
```json
{
  "force_reindex": true,
  "post_types": ["post", "page"]
}
```

### 5. `get_document_by_id`

Retrieve a specific document by ID.

**Parameters:**
- `document_id` (string, required): WordPress post ID

### 6. `expand_query`

Use AI to expand a search query.

**Parameters:**
- `query` (string, required): Original query

## Usage

### Option 1: Using with Claude Desktop

1. **Locate your Claude Desktop config file:**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add the MCP server configuration:**

```json
{
  "mcpServers": {
    "hybrid-search": {
      "command": "python",
      "args": [
        "/Users/ivanm/Desktop/aisearch-main/mcp_server.py"
      ],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "CEREBRAS_API_KEY": "your-api-key-here",
        "WORDPRESS_URL": "https://www.scsengineers.com",
        "WORDPRESS_API_URL": "https://www.scsengineers.com/wp-json/wp/v2",
        "WORDPRESS_USERNAME": "your-username",
        "WORDPRESS_PASSWORD": "your-password",
        "OPENAI_API_KEY": "your-openai-key"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Use the tools in Claude:**

```
Search for environmental consulting services in the WordPress content
```

Claude will automatically use the `search_wordpress_content` tool!

### Option 2: Using MCP Inspector (for Testing)

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Run the inspector
mcp-inspector python mcp_server.py
```

This opens a web UI where you can test all the MCP tools.

### Option 3: Using via API (Custom Integration)

Create a client application:

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_hybrid_search():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env={
            "QDRANT_URL": "http://localhost:6333",
            # ... other env vars
        }
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {tools}")
            
            # Call search tool
            result = await session.call_tool(
                "search_wordpress_content",
                {
                    "query": "energy audit",
                    "limit": 5
                }
            )
            print(f"Search results: {result}")

asyncio.run(use_hybrid_search())
```

## Running the MCP Server Standalone

You can also run the MCP server directly for testing:

```bash
# Make sure all services are running
# 1. Start Qdrant (if using local instance)
docker run -p 6333:6333 qdrant/qdrant

# 2. Run the MCP server
python mcp_server.py
```

The server will run on stdio and wait for MCP protocol messages.

## Integration with Existing FastAPI Service

You can run both the FastAPI service AND the MCP server:

```bash
# Terminal 1: Run FastAPI service (HTTP endpoints)
python main.py

# Terminal 2: Run MCP server (for AI assistants)
python mcp_server.py
```

They share the same underlying search system but serve different clients:
- **FastAPI** → WordPress plugin, web applications
- **MCP Server** → AI assistants (Claude, etc.)

## Troubleshooting

### Issue: "MCP SDK not installed"

**Solution:**
```bash
pip install mcp
```

### Issue: "Search system not initialized"

**Solution:**
- Ensure Qdrant is running
- Check environment variables in `mcp_config.json`
- Verify API keys are correct

### Issue: "No results found"

**Solution:**
- First index content using `index_wordpress_content` tool
- Check WordPress credentials
- Verify WordPress API is accessible

## Advanced Usage

### Custom Tool Development

You can extend the MCP server with additional tools:

```python
# In mcp_server.py, add a new tool:

Tool(
    name="analyze_search_trends",
    description="Analyze search trends over time",
    inputSchema={
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to analyze",
                "default": 7
            }
        }
    }
)

# Add the handler:
async def _analyze_trends(self, args: Dict[str, Any]) -> Dict[str, Any]:
    # Your custom logic here
    pass
```

### Using with Multiple WordPress Sites

Modify `mcp_config.json` to support multiple sites:

```json
{
  "mcpServers": {
    "hybrid-search-site1": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "WORDPRESS_URL": "https://site1.com",
        ...
      }
    },
    "hybrid-search-site2": {
      "command": "python",
      "args": ["mcp_server.py"],
      "env": {
        "WORDPRESS_URL": "https://site2.com",
        ...
      }
    }
  }
}
```

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Access Control**: Limit MCP server access to trusted AI assistants
3. **Rate Limiting**: Consider adding rate limits for expensive operations
4. **Logging**: Monitor MCP server logs for unusual activity

## Next Steps

1. Install the MCP SDK: `pip install mcp`
2. Configure your environment variables
3. Test with MCP Inspector
4. Integrate with Claude Desktop
5. Start using AI-powered search!

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [MCP GitHub](https://github.com/anthropics/anthropic-sdk-python)
- [Claude Desktop](https://claude.ai/download)

