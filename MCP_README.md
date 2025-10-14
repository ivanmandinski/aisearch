# MCP Integration for Hybrid Search 🚀

**Expose your WordPress hybrid search to AI assistants like Claude!**

---

## 🎯 What This Does

This MCP (Model Context Protocol) integration allows AI assistants to directly:
- 🔍 Search your WordPress content using hybrid search
- 🤖 Get AI-generated answers from your content
- 📊 View search statistics and analytics
- 📥 Index and manage content
- 🌟 Expand queries intelligently

## 📚 Quick Links

- **[Quick Start Guide](MCP_QUICKSTART.md)** - Get started in 5 minutes
- **[Integration Guide](MCP_INTEGRATION_GUIDE.md)** - Detailed setup and usage
- **[Architecture Overview](MCP_ARCHITECTURE.md)** - Technical deep dive

## ⚡ Quick Start

### 1. Install

```bash
pip install mcp
```

### 2. Test

```bash
python test_mcp_client.py
```

### 3. Use with Claude

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hybrid-search": {
      "command": "python",
      "args": ["/Users/ivanm/Desktop/aisearch-main/mcp_server.py"],
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "CEREBRAS_API_KEY": "your-key",
        "WORDPRESS_URL": "https://www.scsengineers.com",
        "WORDPRESS_API_URL": "https://www.scsengineers.com/wp-json/wp/v2",
        "WORDPRESS_USERNAME": "username",
        "WORDPRESS_PASSWORD": "password",
        "OPENAI_API_KEY": "your-openai-key"
      }
    }
  }
}
```

### 4. Try It!

Open Claude and say:

```
"Search for environmental consulting services in the WordPress content"
```

## 📦 What's Included

```
aisearch-main/
├── mcp_server.py                 # MCP server implementation
├── mcp_config.json               # Claude Desktop configuration
├── test_mcp_client.py            # Test client with examples
├── MCP_QUICKSTART.md             # 5-minute setup guide
├── MCP_INTEGRATION_GUIDE.md      # Complete documentation
├── MCP_ARCHITECTURE.md           # Technical architecture
├── env.mcp.example               # Environment variables reference
└── scripts/
    ├── run_mcp_server.sh         # Run MCP server
    └── test_mcp_setup.sh         # Verify setup
```

## 🛠️ Available Tools

### For AI Assistants

When you connect Claude (or any MCP client), these tools become available:

| Tool | Description |
|------|-------------|
| `search_wordpress_content` | Hybrid search with AI reranking |
| `search_with_answer` | Search + AI-generated answer |
| `get_search_stats` | View index statistics |
| `index_wordpress_content` | Index/reindex content |
| `get_document_by_id` | Retrieve specific document |
| `expand_query` | AI-powered query expansion |

## 🏗️ Architecture

```
Claude Desktop (MCP Client)
         ↓
    MCP Server (mcp_server.py)
         ↓
  Hybrid Search System
         ↓
  ┌──────┴──────┬────────┬───────────┐
  ↓             ↓        ↓           ↓
Qdrant     Cerebras   LlamaIndex  WordPress
Vector DB     LLM    Orchestrator   Content
```

## 🧪 Testing

### Basic Test
```bash
python test_mcp_client.py
```

### Test Indexing
```bash
python test_mcp_client.py index
```

### Interactive Mode
```bash
python test_mcp_client.py interactive
```

### Verify Setup
```bash
./scripts/test_mcp_setup.sh --test
```

## 💡 Use Cases

### 1. Content Discovery
**You:** "Find all pages about sustainability"  
**Claude:** *Uses `search_wordpress_content` to find relevant pages*

### 2. Smart Q&A
**You:** "What environmental services does the company offer?"  
**Claude:** *Uses `search_with_answer` to generate comprehensive answer*

### 3. Content Management
**You:** "Index all new blog posts"  
**Claude:** *Uses `index_wordpress_content` with filters*

### 4. Analytics
**You:** "How many documents are indexed?"  
**Claude:** *Uses `get_search_stats` to provide insights*

## 🔐 Security

- ✅ Runs locally (no cloud exposure)
- ✅ Environment-based configuration
- ✅ API keys in secure config
- ⚠️ Keep `claude_desktop_config.json` secure
- ⚠️ Don't commit API keys to git

## 🚦 Running Both Services

You can run both the FastAPI service (for WordPress) and MCP server (for AI) simultaneously:

```bash
# Terminal 1: HTTP API for WordPress plugin
python main.py

# Terminal 2: MCP server is auto-started by Claude Desktop
# (or run manually for testing)
python mcp_server.py
```

## 🐛 Troubleshooting

### "MCP SDK not installed"
```bash
pip install mcp
```

### "Service not initialized"
- Ensure Qdrant is running: `docker run -p 6333:6333 qdrant/qdrant`
- Check environment variables in config
- Verify API keys

### "No results found"
First index content:
```
Tell Claude: "Index all WordPress content"
```

### Check logs
```bash
# MCP server logs (in Claude Desktop)
tail -f ~/Library/Logs/Claude/mcp-server-hybrid-search.log

# Or run manually to see output
python mcp_server.py
```

## 📊 Performance

- **Search:** 200-500ms typical
- **Indexing:** ~2-5s per 100 documents
- **Cold start:** 2-5s (service initialization)

## 🔄 Integration with Existing System

The MCP server **does not replace** your existing FastAPI service. They work together:

- **FastAPI** → Serves WordPress plugin (HTTP)
- **MCP Server** → Serves AI assistants (MCP protocol)
- **Shared Core** → Same search engine, same results

## 🎓 Learn More

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Anthropic MCP GitHub](https://github.com/anthropics/anthropic-sdk-python)
- [Claude Desktop](https://claude.ai/download)

## 📝 Examples

### Example 1: Search from Claude

**Prompt:**
```
Search the WordPress site for "landfill gas projects" and show me the top 5 results
```

**Claude will:**
1. Call `search_wordpress_content` tool
2. Get hybrid search results
3. Format and present them to you

### Example 2: Get an Answer

**Prompt:**
```
What does SCS Engineers do in the renewable energy sector? Give me a detailed answer based on their website.
```

**Claude will:**
1. Call `search_with_answer` tool
2. Search for relevant content
3. Use Cerebras LLM to generate answer
4. Cite sources

### Example 3: Content Management

**Prompt:**
```
Index all blog posts from WordPress
```

**Claude will:**
1. Call `index_wordpress_content` with filters
2. Fetch posts from WordPress
3. Index in Qdrant
4. Report results

## 🚀 Next Steps

1. ✅ Read the [Quick Start Guide](MCP_QUICKSTART.md)
2. ✅ Install MCP SDK: `pip install mcp`
3. ✅ Configure Claude Desktop
4. ✅ Test with `test_mcp_client.py`
5. 🎉 Start using AI-powered search!

## 🤝 Contributing

This MCP integration is part of your hybrid search system. To add new tools:

1. Add tool definition in `mcp_server.py`
2. Implement handler method
3. Test with `test_mcp_client.py`
4. Update documentation

## 📄 License

Same as your main project.

---

**Questions?** Check the detailed guides:
- [MCP_QUICKSTART.md](MCP_QUICKSTART.md) - Get running fast
- [MCP_INTEGRATION_GUIDE.md](MCP_INTEGRATION_GUIDE.md) - Complete reference
- [MCP_ARCHITECTURE.md](MCP_ARCHITECTURE.md) - Technical details

**Happy searching! 🎉**

