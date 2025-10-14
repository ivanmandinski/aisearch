#!/bin/bash
# Quick test script to verify MCP setup

echo "🧪 Testing MCP Hybrid Search Setup"
echo "=================================="

# Check Python
echo -n "✓ Python: "
python --version

# Check MCP SDK
echo -n "✓ MCP SDK: "
python -c "import mcp; print(f'installed (v{mcp.__version__ if hasattr(mcp, \"__version__\") else \"unknown\"})')" 2>/dev/null || echo "❌ NOT INSTALLED"

# Check other dependencies
echo -n "✓ FastAPI: "
python -c "import fastapi; print(f'installed (v{fastapi.__version__})')" 2>/dev/null || echo "❌ NOT INSTALLED"

echo -n "✓ Qdrant Client: "
python -c "import qdrant_client; print(f'installed')" 2>/dev/null || echo "❌ NOT INSTALLED"

echo -n "✓ LlamaIndex: "
python -c "import llama_index; print(f'installed')" 2>/dev/null || echo "❌ NOT INSTALLED"

# Check Qdrant connection
echo -n "✓ Qdrant Server: "
QDRANT_URL=${QDRANT_URL:-http://localhost:6333}
curl -s ${QDRANT_URL}/collections >/dev/null 2>&1 && echo "running at ${QDRANT_URL}" || echo "❌ NOT REACHABLE"

# Check environment variables
echo ""
echo "Environment Variables:"
echo "  QDRANT_URL: ${QDRANT_URL:-not set}"
echo "  WORDPRESS_URL: ${WORDPRESS_URL:-not set}"
echo "  CEREBRAS_API_KEY: ${CEREBRAS_API_KEY:+***set***}"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:+***set***}"

echo ""
echo "=================================="

# Run quick test
if [ "$1" == "--test" ]; then
    echo ""
    echo "Running quick functional test..."
    python test_mcp_client.py
fi

