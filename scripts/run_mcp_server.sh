#!/bin/bash
# Script to run the MCP server with proper environment setup

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check dependencies
echo "🔍 Checking dependencies..."
python -c "import mcp" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ MCP SDK not installed. Installing..."
    pip install mcp
fi

# Check if Qdrant is running
echo "🔍 Checking Qdrant connection..."
curl -s ${QDRANT_URL:-http://localhost:6333}/collections >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Cannot connect to Qdrant at ${QDRANT_URL:-http://localhost:6333}"
    echo "   Make sure Qdrant is running:"
    echo "   docker run -p 6333:6333 qdrant/qdrant"
fi

# Run the MCP server
echo "🚀 Starting MCP Hybrid Search Server..."
python mcp_server.py

