"""
MCP Server for Hybrid Search System
Exposes hybrid search functionality via Model Context Protocol
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: pip install mcp")
    exit(1)

# Import your existing search components
from simple_hybrid_search import SimpleHybridSearch
from wordpress_client import WordPressContentFetcher
from cerebras_llm import CerebrasLLM
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridSearchMCPServer:
    """MCP Server wrapping the Hybrid Search System"""
    
    def __init__(self):
        self.server = Server("hybrid-search-mcp")
        self.search_system: Optional[SimpleHybridSearch] = None
        self.wp_client: Optional[WordPressContentFetcher] = None
        self.llm_client: Optional[CerebrasLLM] = None
        
        # Register MCP tools
        self._register_tools()
        
    async def initialize_services(self):
        """Initialize search system and related services"""
        try:
            logger.info("Initializing Hybrid Search System...")
            self.search_system = SimpleHybridSearch()
            
            logger.info("Initializing Cerebras LLM...")
            self.llm_client = CerebrasLLM()
            
            logger.info("Initializing WordPress Client...")
            self.wp_client = WordPressContentFetcher()
            
            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    def _register_tools(self):
        """Register MCP tools/endpoints"""
        
        # Tool 1: Search WordPress Content
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="search_wordpress_content",
                    description="Search WordPress content using hybrid search with AI reranking. "
                               "Combines semantic search (Qdrant) with traditional search and uses "
                               "Cerebras LLM for intelligent result ranking.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (1-50)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 50
                            },
                            "enable_ai_reranking": {
                                "type": "boolean",
                                "description": "Whether to use AI reranking",
                                "default": True
                            },
                            "ai_weight": {
                                "type": "number",
                                "description": "Weight for AI score (0.0-1.0)",
                                "default": 0.7,
                                "minimum": 0.0,
                                "maximum": 1.0
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="search_with_answer",
                    description="Search WordPress content and get an AI-generated answer based on the results. "
                               "Uses Cerebras LLM to synthesize an answer from the search results.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to consider",
                                "default": 10
                            },
                            "custom_instructions": {
                                "type": "string",
                                "description": "Custom instructions for answer generation",
                                "default": ""
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_search_stats",
                    description="Get statistics about the indexed WordPress content including "
                               "total documents, collection info, and search system status.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="index_wordpress_content",
                    description="Index or reindex WordPress content into the search system. "
                               "Fetches content from WordPress and stores it in Qdrant vector database.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "force_reindex": {
                                "type": "boolean",
                                "description": "Force reindexing even if index exists",
                                "default": False
                            },
                            "post_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific post types to index (e.g., ['post', 'page']). Leave empty for all.",
                                "default": []
                            }
                        }
                    }
                ),
                Tool(
                    name="get_document_by_id",
                    description="Retrieve a specific WordPress document by its ID from the search index.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "The document ID (WordPress post ID)"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                Tool(
                    name="expand_query",
                    description="Use AI to expand and improve a search query with related terms and variations.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The original search query"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            try:
                if not self.search_system:
                    await self.initialize_services()
                
                # Route to appropriate handler
                if name == "search_wordpress_content":
                    result = await self._search_content(arguments)
                elif name == "search_with_answer":
                    result = await self._search_with_answer(arguments)
                elif name == "get_search_stats":
                    result = await self._get_stats()
                elif name == "index_wordpress_content":
                    result = await self._index_content(arguments)
                elif name == "get_document_by_id":
                    result = await self._get_document(arguments)
                elif name == "expand_query":
                    result = await self._expand_query(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
                
            except Exception as e:
                logger.error(f"Tool call error [{name}]: {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "timestamp": datetime.utcnow().isoformat()
                    }, indent=2)
                )]
    
    async def _search_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform hybrid search"""
        query = args.get("query", "")
        limit = args.get("limit", 10)
        enable_ai_reranking = args.get("enable_ai_reranking", True)
        ai_weight = args.get("ai_weight", 0.7)
        
        start_time = datetime.utcnow()
        
        results, metadata = await self.search_system.search(
            query=query,
            limit=limit,
            enable_ai_reranking=enable_ai_reranking,
            ai_weight=ai_weight
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "total_results": len(results),
            "processing_time_seconds": processing_time,
            "metadata": metadata
        }
    
    async def _search_with_answer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search and generate AI answer"""
        query = args.get("query", "")
        limit = args.get("limit", 10)
        custom_instructions = args.get("custom_instructions", "")
        
        start_time = datetime.utcnow()
        
        result = await self.search_system.search_with_answer(
            query=query,
            limit=limit,
            custom_instructions=custom_instructions
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "success": True,
            "query": query,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "processing_time_seconds": processing_time
        }
    
    async def _get_stats(self) -> Dict[str, Any]:
        """Get search system statistics"""
        stats = self.search_system.get_stats()
        
        return {
            "success": True,
            "stats": stats,
            "system_info": {
                "qdrant_url": settings.qdrant_url,
                "collection_name": settings.qdrant_collection_name,
                "embed_model": settings.embed_model,
                "llm_model": settings.cerebras_model
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _index_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Index WordPress content"""
        force_reindex = args.get("force_reindex", False)
        post_types = args.get("post_types", None)
        
        start_time = datetime.utcnow()
        
        # Check if already indexed
        if not force_reindex:
            stats = self.search_system.get_stats()
            if stats.get('total_documents', 0) > 0:
                return {
                    "success": True,
                    "message": "Index already exists. Use force_reindex=true to reindex.",
                    "indexed_count": stats.get('total_documents', 0),
                    "processing_time_seconds": 0
                }
        
        # Fetch content from WordPress
        logger.info("Fetching content from WordPress...")
        documents = await self.wp_client.get_all_content(post_types)
        
        if not documents:
            return {
                "success": False,
                "message": "No content found in WordPress",
                "indexed_count": 0
            }
        
        # Index documents
        logger.info(f"Indexing {len(documents)} documents...")
        success = await self.search_system.index_documents(documents)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "success": success,
            "message": f"Successfully indexed {len(documents)} documents" if success else "Indexing failed",
            "indexed_count": len(documents) if success else 0,
            "processing_time_seconds": processing_time
        }
    
    async def _get_document(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get document by ID"""
        document_id = args.get("document_id", "")
        
        # Search for the specific document
        results, _ = await self.search_system.search(
            query=f"id:{document_id}",
            limit=1
        )
        
        if results and len(results) > 0:
            return {
                "success": True,
                "document": results[0]
            }
        else:
            return {
                "success": False,
                "message": f"Document not found: {document_id}"
            }
    
    async def _expand_query(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Expand query using AI"""
        query = args.get("query", "")
        
        if not self.llm_client:
            return {
                "success": False,
                "message": "LLM client not available"
            }
        
        try:
            expanded = self.llm_client.expand_query(query)
            return {
                "success": True,
                "original_query": query,
                "expanded_queries": expanded
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Query expansion failed: {str(e)}"
            }
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Hybrid Search MCP Server...")
        
        # Initialize services
        await self.initialize_services()
        
        # Run stdio server
        async with stdio_server() as (read_stream, write_stream):
            logger.info("MCP Server running on stdio...")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    server = HybridSearchMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())



