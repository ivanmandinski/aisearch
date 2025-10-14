# MCP Integration - Visual Guide

## 🎨 Complete System Overview

```
╔══════════════════════════════════════════════════════════════════════╗
║                         CLIENT APPLICATIONS                          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────────────────┐              ┌─────────────────────┐      ║
║  │   WordPress Site    │              │   Claude Desktop    │      ║
║  │                     │              │                     │      ║
║  │  🌐 Search Page     │              │  🤖 AI Assistant    │      ║
║  │  📊 Admin Panel     │              │  💬 Chat Interface  │      ║
║  │  📈 Analytics       │              │  🔧 MCP Tools       │      ║
║  └──────────┬──────────┘              └──────────┬──────────┘      ║
║             │                                    │                  ║
║             │ AJAX/HTTP                          │ MCP (stdio)      ║
║             │                                    │                  ║
╚═════════════╪════════════════════════════════════╪══════════════════╝
              │                                    │
              │                                    │
╔═════════════╪════════════════════════════════════╪══════════════════╗
║             │         API LAYER                  │                  ║
╠═════════════╪════════════════════════════════════╪══════════════════╣
║             ▼                                    ▼                  ║
║  ┌────────────────────┐              ┌────────────────────┐        ║
║  │   FastAPI Service  │              │    MCP Server      │        ║
║  │    (main.py)       │              │  (mcp_server.py)   │        ║
║  │                    │◄─────────────┤                    │        ║
║  │  POST /search      │   Shared     │  6 MCP Tools:      │        ║
║  │  POST /index       │ Components   │  • search_*        │        ║
║  │  GET  /stats       │              │  • index_*         │        ║
║  │  GET  /suggest     │              │  • get_*           │        ║
║  │  GET  /health      │              │  • expand_query    │        ║
║  └──────────┬─────────┘              └────────┬───────────┘        ║
║             │                                 │                     ║
║             └─────────────────┬───────────────┘                     ║
║                               │                                     ║
╚═══════════════════════════════╪═════════════════════════════════════╝
                                │
                                │
╔═══════════════════════════════╪═════════════════════════════════════╗
║                               │  CORE SEARCH ENGINE                 ║
╠═══════════════════════════════╪═════════════════════════════════════╣
║                               ▼                                     ║
║  ┌──────────────────────────────────────────────────────┐          ║
║  │       SimpleHybridSearch (search orchestrator)       │          ║
║  │                                                       │          ║
║  │  search() ──────► Hybrid Search Logic               │          ║
║  │  search_with_answer() ──► + AI Answer               │          ║
║  │  index_documents() ──► Indexing                     │          ║
║  │  get_stats() ──► Analytics                          │          ║
║  └───────┬──────────────┬────────────┬──────────────────┘          ║
║          │              │            │                              ║
║  ┌───────▼──────┐  ┌───▼────┐  ┌───▼──────┐  ┌──────────────┐   ║
║  │   Qdrant     │  │Cerebras│  │LlamaIndex│  │  WordPress   │   ║
║  │   Manager    │  │  LLM   │  │Orchestr. │  │    Client    │   ║
║  │              │  │        │  │          │  │              │   ║
║  │ • Vectors    │  │• Answer│  │• Chunking│  │• Fetch Posts │   ║
║  │ • Semantic   │  │• Rerank│  │• Index   │  │• Transform   │   ║
║  │ • Search     │  │• Expand│  │• Embed   │  │• Paginate    │   ║
║  └───────┬──────┘  └────────┘  └──────────┘  └──────┬───────┘   ║
║          │                                           │             ║
╚══════════╪═══════════════════════════════════════════╪═════════════╝
           │                                           │
           │                                           │
╔══════════╪═══════════════════════════════════════════╪═════════════╗
║          │              DATA LAYER                   │             ║
╠══════════╪═══════════════════════════════════════════╪═════════════╣
║          ▼                                           ▼             ║
║  ┌────────────────┐                    ┌────────────────────┐     ║
║  │ Qdrant Vector  │                    │  WordPress MySQL   │     ║
║  │   Database     │                    │     Database       │     ║
║  │                │                    │                    │     ║
║  │ • Collections  │                    │ • Posts/Pages      │     ║
║  │ • Embeddings   │                    │ • Custom Types     │     ║
║  │ • Metadata     │                    │ • Taxonomies       │     ║
║  └────────────────┘                    └────────────────────┘     ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 🔄 Data Flow: Search Request

### Via WordPress Plugin (HTTP)

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. User types "energy audit" in search box                       │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. JavaScript (hybrid-search.js)                                 │
│    • Captures input                                              │
│    • Debounces                                                   │
│    • Makes AJAX call                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. WordPress AJAX Handler                                        │
│    • Validates nonce                                             │
│    • Checks permissions                                          │
│    • Forwards to FastAPI                                         │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. FastAPI (POST /search)                                        │
│    • Receives request                                            │
│    • Validates parameters                                        │
│    • Calls SimpleHybridSearch.search()                           │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. SimpleHybridSearch                                            │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ a) Generate embedding (OpenAI)                          │  │
│    │    "energy audit" → [0.123, -0.456, ...]                │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ b) Semantic search (Qdrant)                             │  │
│    │    Find similar vectors                                 │  │
│    │    Results: [doc1, doc2, doc3...]                       │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ c) Keyword search (BM25)                                │  │
│    │    Traditional text matching                            │  │
│    │    Results: [doc4, doc2, doc5...]                       │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ d) Fuse results                                         │  │
│    │    Combine semantic + keyword                           │  │
│    │    Deduplicate                                          │  │
│    └─────────────────────────────────────────────────────────┘  │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ e) AI Reranking (Cerebras LLM)                          │  │
│    │    Score relevance with AI                              │  │
│    │    Reorder by combined score                            │  │
│    └─────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. Results Flow Back                                             │
│    FastAPI → WordPress → JavaScript → UI                         │
│                                                                  │
│    User sees:                                                    │
│    ✓ Ranked results                                             │
│    ✓ Highlighted matches                                        │
│    ✓ Scores                                                     │
│    ✓ Metadata                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Via Claude Desktop (MCP)

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. User asks Claude: "Search for energy audit services"         │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. Claude analyzes request                                       │
│    • Understands intent                                          │
│    • Selects tool: search_wordpress_content                      │
│    • Prepares arguments: {query: "energy audit services"}        │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. MCP Protocol Call                                             │
│    {                                                             │
│      "method": "tools/call",                                     │
│      "params": {                                                 │
│        "name": "search_wordpress_content",                       │
│        "arguments": {"query": "energy audit services"}           │
│      }                                                           │
│    }                                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. MCP Server (mcp_server.py)                                    │
│    • Receives tool call                                          │
│    • Validates arguments                                         │
│    • Calls _search_content()                                     │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. SimpleHybridSearch                                            │
│    (Same process as HTTP flow)                                   │
│    • Embedding → Semantic search → Keyword search               │
│    • Fusion → AI Reranking                                       │
└────────────────────────────┬─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ 6. Results Return via MCP                                        │
│    MCP Server → Claude → User                                    │
│                                                                  │
│    Claude presents:                                              │
│    "I found 8 results about energy audit services:              │
│     1. Energy Audit Services (Score: 0.92)                       │
│        URL: https://www.scsengineers.com/energy-audit/           │
│        ...                                                       │
│     2. ..."                                                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🎭 Side-by-Side Comparison

```
╔═══════════════════════════════╦═══════════════════════════════╗
║      WordPress Plugin         ║       Claude Desktop          ║
║         (HTTP API)            ║         (MCP API)             ║
╠═══════════════════════════════╬═══════════════════════════════╣
║                               ║                               ║
║  👤 User Interface            ║  💬 Chat Interface            ║
║  • Search box                 ║  • Natural language           ║
║  • Filter dropdowns           ║  • Conversational             ║
║  • Result cards               ║  • Follow-up questions        ║
║                               ║                               ║
║  🔌 Protocol: HTTP/AJAX       ║  🔌 Protocol: MCP (stdio)     ║
║                               ║                               ║
║  📊 Response Format           ║  📊 Response Format           ║
║  • JSON with metadata         ║  • JSON in MCP envelope       ║
║  • Pagination info            ║  • Tool call result           ║
║  • Timing stats               ║  • Timing stats               ║
║                               ║                               ║
║  🎯 Use Case                  ║  🎯 Use Case                  ║
║  • End-user search            ║  • AI-assisted research       ║
║  • Public website             ║  • Content analysis           ║
║  • Traditional UI             ║  • Smart Q&A                  ║
║                               ║                               ║
║  🔄 Request Example:          ║  🔄 Request Example:          ║
║  POST /search                 ║  "Find articles about X"      ║
║  {                            ║  (Claude handles tool call)   ║
║    "query": "energy",         ║                               ║
║    "limit": 10                ║                               ║
║  }                            ║                               ║
║                               ║                               ║
╠═══════════════════════════════╩═══════════════════════════════╣
║                    SAME SEARCH ENGINE                          ║
║          SimpleHybridSearch + Qdrant + Cerebras                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🧩 Component Integration Map

```
┌─────────────────────────────────────────────────────────────────┐
│                      YOUR FILES                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EXISTING (Unchanged):                                          │
│  ✓ main.py                  ← FastAPI service                  │
│  ✓ simple_hybrid_search.py  ← Core search engine               │
│  ✓ qdrant_manager.py         ← Vector DB management            │
│  ✓ cerebras_llm.py           ← AI/LLM integration              │
│  ✓ wordpress_client.py       ← Content fetching                │
│  ✓ llamaindex_orchestrator.py ← Document processing            │
│  ✓ config.py                 ← Configuration                   │
│  ✓ wordpress-plugin/         ← WordPress files                 │
│                                                                 │
│  NEW (MCP Integration):                                         │
│  ★ mcp_server.py             ← MCP server ┐                    │
│  ★ test_mcp_client.py        ← Test suite ├─ Core MCP          │
│  ★ mcp_config.json           ← Config     ┘                    │
│  ★ MCP_*.md                  ← Documentation                   │
│  ★ scripts/*.sh              ← Helper scripts                  │
│                                                                 │
│  UPDATED:                                                       │
│  ⚡ requirements.txt          ← Added 'mcp' package            │
│  ⚡ hybrid-search.php         ← Version 2.8.8 → 2.9.0          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎬 Installation Flow Chart

```
START
  │
  ▼
┌────────────────────────┐
│ Install MCP SDK        │
│ $ pip install mcp      │
└───────────┬────────────┘
            ▼
┌────────────────────────┐
│ Test Installation      │
│ $ python test_mcp_     │
│   client.py            │
└───────────┬────────────┘
            │
            ├─── Success? ───┐
            │                │
           YES              NO
            │                │
            ▼                ▼
┌────────────────────┐  ┌──────────────┐
│ Configure Claude   │  │ Fix Issues   │
│ Desktop            │  │ Check logs   │
│ (mcp_config.json)  │  │ Verify deps  │
└─────────┬──────────┘  └──────┬───────┘
          │                    │
          │                    │
          └────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │ Restart Claude │
          │ Desktop        │
          └────────┬───────┘
                   │
                   ▼
          ┌────────────────┐
          │ Try Search!    │
          │ "Search for X" │
          └────────┬───────┘
                   │
                   ├─── Works? ───┐
                   │              │
                  YES            NO
                   │              │
                   ▼              ▼
              ┌─────────┐    ┌────────────┐
              │ SUCCESS!│    │ Check logs │
              │    🎉   │    │ See guide  │
              └─────────┘    └────────────┘
```

---

## 📦 File Organization

```
aisearch-main/
│
├── 🔵 Backend Python Files
│   ├── main.py                      # FastAPI HTTP service
│   ├── mcp_server.py                # MCP server (NEW!)
│   ├── simple_hybrid_search.py      # Core search engine
│   ├── qdrant_manager.py            # Vector DB
│   ├── cerebras_llm.py              # AI/LLM
│   ├── wordpress_client.py          # WP content
│   ├── llamaindex_orchestrator.py   # Doc processing
│   └── config.py                    # Settings
│
├── 🟢 Configuration Files
│   ├── requirements.txt             # Python deps (updated)
│   ├── mcp_config.json              # MCP config (NEW!)
│   ├── env.mcp.example              # Env vars ref (NEW!)
│   ├── docker-compose.yml           # Docker setup
│   └── Dockerfile                   # Container def
│
├── 🟡 WordPress Plugin
│   └── wordpress-plugin/
│       ├── hybrid-search.php        # Main plugin (v2.9.0)
│       ├── assets/
│       │   ├── css/                 # Styles
│       │   └── js/                  # Scripts
│       └── includes/                # PHP classes
│
├── 🟠 Testing & Scripts
│   ├── test_mcp_client.py           # MCP tests (NEW!)
│   └── scripts/                     # (NEW!)
│       ├── run_mcp_server.sh        # Run MCP
│       └── test_mcp_setup.sh        # Verify setup
│
├── 🔴 Documentation
│   ├── MCP_README.md                # Quick start (NEW!)
│   ├── MCP_QUICKSTART.md            # 5-min guide (NEW!)
│   ├── MCP_INTEGRATION_GUIDE.md     # Full guide (NEW!)
│   ├── MCP_ARCHITECTURE.md          # Technical (NEW!)
│   ├── MCP_INTEGRATION_SUMMARY.md   # Summary (NEW!)
│   ├── INTEGRATION_VISUAL_GUIDE.md  # This file (NEW!)
│   └── VERSION_2.9.0_CHANGELOG.txt  # Release notes (NEW!)
│
└── 🟣 Other Files
    ├── *.txt                        # Various docs
    └── *.md                         # Markdown files
```

---

## 🎯 Quick Reference

### Start MCP Server (Manual)
```bash
python mcp_server.py
```

### Test MCP Integration
```bash
python test_mcp_client.py
```

### Start FastAPI Service
```bash
python main.py
```

### Check Setup
```bash
./scripts/test_mcp_setup.sh --test
```

### Claude Desktop Config Location
```
macOS:   ~/Library/Application Support/Claude/claude_desktop_config.json
Windows: %APPDATA%\Claude\claude_desktop_config.json
```

---

## 💡 Key Insights

1. **MCP Server = New Interface, Same Engine**
   - Exposes existing search via MCP protocol
   - No duplicate code
   - Consistent results

2. **WordPress Plugin Unchanged**
   - Continues using FastAPI HTTP endpoints
   - No breaking changes
   - Existing features intact

3. **Both Can Run Together**
   - FastAPI serves WordPress
   - MCP serves AI assistants
   - Share same search engine

4. **Optional Integration**
   - MCP is completely optional
   - Remove MCP files = everything still works
   - Easy to adopt incrementally

---

*Visual guide created for Hybrid Search v2.9.0 MCP Integration*

