"""
Test client for MCP Hybrid Search Server
Demonstrates how to use the MCP server programmatically
"""
import asyncio
import json
from typing import Any, Dict

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: pip install mcp")
    exit(1)


async def test_search():
    """Test the hybrid search MCP server"""
    
    # Configure server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None  # Will use environment variables from .env
    )
    
    print("🚀 Starting MCP Hybrid Search client...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                print("✅ Session initialized")
                
                # List available tools
                print("\n📋 Listing available tools...")
                tools_response = await session.list_tools()
                tools = tools_response.tools
                
                print(f"\n🔧 Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Test 1: Get search statistics
                print("\n" + "="*60)
                print("TEST 1: Getting search statistics")
                print("="*60)
                
                stats_result = await session.call_tool("get_search_stats", {})
                print(json.dumps(stats_result.content[0].text, indent=2))
                
                # Test 2: Search for content
                print("\n" + "="*60)
                print("TEST 2: Searching for 'energy audit'")
                print("="*60)
                
                search_result = await session.call_tool(
                    "search_wordpress_content",
                    {
                        "query": "energy audit services",
                        "limit": 5,
                        "enable_ai_reranking": True,
                        "ai_weight": 0.7
                    }
                )
                
                search_data = json.loads(search_result.content[0].text)
                print(f"\n✅ Found {search_data.get('total_results', 0)} results")
                print(f"⏱️  Processing time: {search_data.get('processing_time_seconds', 0):.3f}s")
                
                if search_data.get('results'):
                    print("\n📄 Top 3 Results:")
                    for i, result in enumerate(search_data['results'][:3], 1):
                        print(f"\n  {i}. {result.get('title', 'Untitled')}")
                        print(f"     Score: {result.get('score', 0):.4f}")
                        print(f"     URL: {result.get('url', 'N/A')}")
                        print(f"     Excerpt: {result.get('excerpt', '')[:100]}...")
                
                # Test 3: Search with AI answer
                print("\n" + "="*60)
                print("TEST 3: Searching with AI-generated answer")
                print("="*60)
                
                answer_result = await session.call_tool(
                    "search_with_answer",
                    {
                        "query": "What environmental services does SCS Engineers provide?",
                        "limit": 5,
                        "custom_instructions": "Provide a concise summary of their main services"
                    }
                )
                
                answer_data = json.loads(answer_result.content[0].text)
                print(f"\n🤖 AI Answer:")
                print(f"{answer_data.get('answer', 'No answer generated')}")
                print(f"\n📚 Based on {len(answer_data.get('sources', []))} sources")
                
                # Test 4: Expand query
                print("\n" + "="*60)
                print("TEST 4: Query expansion")
                print("="*60)
                
                expand_result = await session.call_tool(
                    "expand_query",
                    {
                        "query": "environmental consulting"
                    }
                )
                
                expand_data = json.loads(expand_result.content[0].text)
                print(f"\n🔍 Original query: {expand_data.get('original_query', '')}")
                print(f"🌟 Expanded queries:")
                for expanded in expand_data.get('expanded_queries', [])[:5]:
                    print(f"  - {expanded}")
                
                print("\n" + "="*60)
                print("✅ All tests completed successfully!")
                print("="*60)
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_indexing():
    """Test indexing functionality"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None
    )
    
    print("🚀 Testing WordPress content indexing...")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Index content
                print("\n📥 Indexing WordPress content...")
                index_result = await session.call_tool(
                    "index_wordpress_content",
                    {
                        "force_reindex": False,
                        "post_types": []  # Index all types
                    }
                )
                
                index_data = json.loads(index_result.content[0].text)
                print(json.dumps(index_data, indent=2))
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def interactive_search():
    """Interactive search mode"""
    
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
        env=None
    )
    
    print("🔍 Interactive MCP Search")
    print("="*60)
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                while True:
                    query = input("\n🔍 Enter search query (or 'quit' to exit): ").strip()
                    
                    if query.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    if not query:
                        continue
                    
                    # Perform search
                    result = await session.call_tool(
                        "search_wordpress_content",
                        {
                            "query": query,
                            "limit": 5,
                            "enable_ai_reranking": True
                        }
                    )
                    
                    data = json.loads(result.content[0].text)
                    
                    print(f"\n✅ Found {data.get('total_results', 0)} results:")
                    for i, item in enumerate(data.get('results', []), 1):
                        print(f"\n{i}. {item.get('title', 'Untitled')}")
                        print(f"   Score: {item.get('score', 0):.4f}")
                        print(f"   {item.get('url', '')}")
                
                print("\n👋 Goodbye!")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "index":
            asyncio.run(test_indexing())
        elif mode == "interactive":
            asyncio.run(interactive_search())
        else:
            print("Usage:")
            print("  python test_mcp_client.py          # Run all tests")
            print("  python test_mcp_client.py index    # Test indexing")
            print("  python test_mcp_client.py interactive  # Interactive mode")
    else:
        asyncio.run(test_search())



