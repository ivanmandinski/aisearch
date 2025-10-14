# MCP Integration - Quick Start Guide

## What You've Built

You now have an **MCP (Model Context Protocol) server** that exposes your hybrid search system to AI assistants like Claude. This means:

✅ Claude can search your WordPress content directly  
✅ AI assistants can index new content automatically  
✅ You can ask questions and get AI-generated answers from your content  
✅ Query expansion and semantic search are available to AI tools

## Installation (5 minutes)

### Step 1: Install MCP SDK

```bash
cd /Users/ivanm/Desktop/aisearch-main
pip install mcp
```

### Step 2: Test the MCP Server

```bash
# Test basic functionality
python test_mcp_client.py

# Test indexing
python test_mcp_client.py index

# Interactive search mode
python test_mcp_client.py interactive
```

## Using with Claude Desktop

### Step 1: Find Your Config File

**macOS:**
```bash
open ~/Library/Application\ Support/Claude/
```

**Windows:**
```
%APPDATA%\Claude\
```

### Step 2: Edit `claude_desktop_config.json`

Copy the contents from `mcp_config.json` or add this:

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
        "CEREBRAS_API_KEY": "your-cerebras-key",
        "WORDPRESS_URL": "https://www.scsengineers.com",
        "WORDPRESS_API_URL": "https://www.scsengineers.com/wp-json/wp/v2",
        "WORDPRESS_USERNAME": "your-wp-username",
        "WORDPRESS_PASSWORD": "your-wp-password",
        "OPENAI_API_KEY": "your-openai-key"
      }
    }
  }
}
```

### Step 3: Restart Claude Desktop

Close and reopen Claude Desktop.

### Step 4: Test It!

Open Claude and try these commands:

```
1. "Search for energy audit services in the WordPress content"
   
2. "What are the top 5 results for 'environmental consulting'?"
   
3. "Index the latest WordPress posts"
   
4. "Get statistics about the search index"
   
5. "Search for sustainability practices and give me a summary answer"
```

Claude will automatically use your MCP server! 🎉

## Example Conversations with Claude

### Example 1: Basic Search

**You:** "Search for 'landfill gas' in the WordPress content"

**Claude:** *Uses `search_wordpress_content` tool*
```
I found 12 results about landfill gas:

1. Landfill Gas-to-Energy Solutions (Score: 0.92)
   URL: https://www.scsengineers.com/landfill-gas-energy/
   
2. Renewable Energy Projects (Score: 0.87)
   URL: https://www.scsengineers.com/renewable-energy/
   
[... more results ...]
```

### Example 2: AI-Generated Answer

**You:** "What does SCS Engineers do for environmental consulting? Give me a detailed answer."

**Claude:** *Uses `search_with_answer` tool*
```
Based on the WordPress content, SCS Engineers provides comprehensive environmental consulting services including:

1. Environmental Impact Assessments
2. Remediation Planning and Implementation
3. Regulatory Compliance Assistance
4. Sustainability Consulting
5. Air Quality Monitoring

[... detailed answer based on actual content ...]

(Based on 8 WordPress pages)
```

### Example 3: Content Management

**You:** "Index the latest WordPress posts"

**Claude:** *Uses `index_wordpress_content` tool*
```
✅ Successfully indexed 247 WordPress documents
Processing time: 45.3 seconds

Breakdown:
- Posts: 156
- Pages: 78
- Custom types: 13
```

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   Claude Desktop                      │
│              (or any MCP client)                      │
└────────────────────┬─────────────────────────────────┘
                     │ MCP Protocol
                     │ (stdio)
                     ↓
┌──────────────────────────────────────────────────────┐
│              mcp_server.py                            │
│         (MCP Server - New!)                           │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────┐
│          Existing Hybrid Search System                │
├──────────────────────────────────────────────────────┤
│  • SimpleHybridSearch (simple_hybrid_search.py)      │
│  • Qdrant Vector DB (qdrant_manager.py)              │
│  • Cerebras LLM (cerebras_llm.py)                    │
│  • WordPress Client (wordpress_client.py)            │
└──────────────────────────────────────────────────────┘
                     ↑
                     │
┌────────────────────┴─────────────────────────────────┐
│            WordPress Site                             │
│        www.scsengineers.com                          │
└──────────────────────────────────────────────────────┘
```

## Available Tools

### 🔍 `search_wordpress_content`
Search with hybrid search and AI reranking

### 🤖 `search_with_answer`
Search + get AI-generated answer

### 📊 `get_search_stats`
View index statistics

### 📥 `index_wordpress_content`
Index/reindex WordPress content

### 📄 `get_document_by_id`
Retrieve specific document

### 🌟 `expand_query`
AI-powered query expansion

## Running Both Services

You can run both the FastAPI service (for your WordPress plugin) and the MCP server (for AI assistants) simultaneously:

```bash
# Terminal 1: FastAPI for WordPress plugin
python main.py

# Terminal 2: MCP server for Claude (if running standalone)
python mcp_server.py
```

**Note:** When using with Claude Desktop, you don't need to run `mcp_server.py` manually - Claude starts it automatically!

## Troubleshooting

### "MCP SDK not found"
```bash
pip install mcp
```

### "Services not initialized"
Check that:
- Qdrant is running (port 6333)
- Environment variables are set in `mcp_config.json`
- API keys are valid

### "No results found"
First index content:
```
"Index all WordPress content"
```

### Check Logs
```bash
# MCP server logs
tail -f /path/to/logs/mcp_server.log

# FastAPI logs
tail -f /path/to/logs/main.log
```

## Next Steps

1. ✅ Install MCP SDK
2. ✅ Test with `test_mcp_client.py`
3. ✅ Configure Claude Desktop
4. 🚀 Start using AI-powered search!

## Advanced: JavaScript Integration

You can also call the MCP server from your WordPress plugin's JavaScript:

```javascript
// In wordpress-plugin/assets/js/hybrid-search.js
// Add MCP integration for enhanced AI features

class MCPSearchIntegration {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
        this.mcpEndpoint = apiUrl + '/mcp-bridge'; // Future: HTTP bridge
    }
    
    async searchWithAI(query) {
        // This would require an HTTP bridge to MCP
        // For now, use the existing FastAPI endpoints
        
        const response = await fetch(this.apiUrl + '/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                include_answer: true,
                enable_ai_reranking: true,
                ai_weight: 0.7
            })
        });
        
        return await response.json();
    }
}

// Usage in your existing code:
const mcpIntegration = new MCPSearchIntegration(window.hybridSearchConfig.apiUrl);
```

## Security Notes

⚠️ **Important:**
- Never commit API keys to git
- Use environment variables for sensitive data
- Limit MCP server access to trusted clients
- Monitor usage and set rate limits

## Learn More

- 📖 [Full Integration Guide](MCP_INTEGRATION_GUIDE.md)
- 🔗 [MCP Documentation](https://modelcontextprotocol.io/)
- 💻 [Test Client Examples](test_mcp_client.py)

---

**Questions?** Check the [full guide](MCP_INTEGRATION_GUIDE.md) or the MCP documentation.

