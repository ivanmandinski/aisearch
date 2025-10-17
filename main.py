"""
FastAPI service for hybrid search endpoints.
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime
import uvicorn

from config import settings

# Try to import components with error handling
try:
    from wordpress_client import WordPressContentFetcher
except ImportError as e:
    logging.error(f"Failed to import WordPressContentFetcher: {e}")
    WordPressContentFetcher = None

try:
    from simple_hybrid_search import SimpleHybridSearch
except ImportError as e:
    logging.error(f"Failed to import SimpleHybridSearch: {e}")
    SimpleHybridSearch = None

try:
    from cerebras_llm import CerebrasLLM
except ImportError as e:
    logging.error(f"Failed to import CerebrasLLM: {e}")
    CerebrasLLM = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Hybrid search API for WordPress content using Qdrant, LlamaIndex, and Cerebras LLM"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
search_system = None
llm_client = None
wp_client = None


# Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results per page")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    include_answer: bool = Field(default=False, description="Whether to include LLM-generated answer")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")
    ai_instructions: Optional[str] = Field(default=None, description="Custom AI instructions for answer generation")
    # AI Reranking parameters
    enable_ai_reranking: bool = Field(default=True, description="Whether to use AI reranking")
    ai_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for AI score (0-1)")
    ai_reranking_instructions: str = Field(default="", description="Custom instructions for AI reranking")


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time: float
    answer: Optional[str] = None
    query_analysis: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    force_reindex: bool = Field(default=False, description="Force reindexing even if index exists")
    post_types: Optional[List[str]] = Field(default=None, description="Specific post types to index (None = all)")


class IndexResponse(BaseModel):
    success: bool
    message: str
    documents_indexed: int
    processing_time: float


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str]


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global search_system, llm_client, wp_client
    
    try:
        logger.info("Starting hybrid search service...")
        
        # Initialize services with error handling for each
        if SimpleHybridSearch is not None:
            try:
                logger.info("Initializing search system...")
                search_system = SimpleHybridSearch()
                logger.info("Search system initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize search system: {e}", exc_info=True)
                # Don't raise - allow app to start without search system
        else:
            logger.error("SimpleHybridSearch class not available - search disabled")
        
        if CerebrasLLM is not None:
            try:
                logger.info("Initializing LLM client...")
                llm_client = CerebrasLLM()
                if not llm_client.test_connection():
                    logger.warning("Cerebras LLM connection test failed - continuing anyway")
                else:
                    logger.info("LLM client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)
                # Don't raise - allow app to start without LLM
        else:
            logger.warning("CerebrasLLM class not available - AI answers disabled")
        
        if WordPressContentFetcher is not None:
            try:
                logger.info("Initializing WordPress client...")
                wp_client = WordPressContentFetcher()
                logger.info("WordPress client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize WordPress client: {e}", exc_info=True)
                # Don't raise - allow app to start without WP client
        else:
            logger.warning("WordPressContentFetcher class not available - indexing disabled")
        
        logger.info("Hybrid search service startup completed")
        
    except Exception as e:
        logger.error(f"Unexpected error during startup: {e}")
        # Don't raise - allow app to start even with errors


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global search_system, wp_client
    
    try:
        if search_system:
            search_system.close()
        if wp_client:
            await wp_client.close()
        logger.info("Hybrid search service shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return JSONResponse(
        content={
            "message": "Hybrid Search API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "search": "POST /search",
                "index": "POST /index",
                "health": "GET /health"
            }
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    services_status = {}
    
    try:
        # Check Qdrant connection
        if search_system:
            try:
                stats = search_system.get_stats()
                services_status["qdrant"] = "healthy" if stats.get('total_documents', 0) >= 0 else "unhealthy"
            except Exception as e:
                services_status["qdrant"] = f"error: {str(e)}"
        else:
            services_status["qdrant"] = "not_initialized"
        
        # Check Cerebras LLM
        if llm_client:
            try:
                if llm_client.test_connection():
                    services_status["cerebras_llm"] = "healthy"
                else:
                    services_status["cerebras_llm"] = "connection_failed"
            except Exception as e:
                services_status["cerebras_llm"] = f"error: {str(e)}"
        else:
            services_status["cerebras_llm"] = "not_initialized"
        
        # Check WordPress connection
        if wp_client:
            services_status["wordpress"] = "initialized"
        else:
            services_status["wordpress"] = "not_initialized"
        
        overall_status = "healthy" if all(
            status in ["healthy", "initialized"] 
            for status in services_status.values()
        ) else "degraded"
        
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        services_status = {"error": str(e)}
        overall_status = "unhealthy"
    
    return JSONResponse(
        content={
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": services_status
        }
    )


@app.post("/search")
async def search(request: SearchRequest):
    """Perform hybrid search on indexed content."""
    start_time = datetime.utcnow()
    
    try:
        # Check if search system is initialized
        if not search_system:
            logger.error("Search system not initialized")
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": "Search service not initialized. Please check Railway logs for initialization errors.",
                    "results": [],
                    "metadata": {
                        "query": request.query,
                        "response_time": 0,
                        "status_code": 503
                    }
                }
            )
        
        # Process query with LLM if available (optional)
        query_analysis = None
        search_query = request.query
        
        if llm_client:
            try:
                query_analysis = await llm_client.process_query_async(request.query)
                search_query = query_analysis.get("rewritten_query", request.query)
            except Exception as e:
                logger.warning(f"Query analysis failed: {e} - using original query")
        
        # Perform search with AI reranking support
        search_metadata = {}
        zero_result_data = None
        
        # Log pagination parameters
        logger.info(f"Search request: query='{search_query}', limit={request.limit}, offset={request.offset}")
        
        if request.include_answer:
            try:
                result = await search_system.search_with_answer(
                    search_query, 
                    limit=request.limit,  # Only get the requested amount
                    offset=request.offset,  # Pass offset directly to search system
                    custom_instructions=request.ai_instructions
                )
                # Results are already paginated by the search system
                results = result.get('sources', [])
                answer = result.get('answer')
                total_results = result.get('total_results', len(results))
            except Exception as e:
                logger.error(f"Search with answer failed: {e}")
                # Fallback to basic search
                all_results, search_metadata = await search_system.search(
                    query=search_query,
                    limit=request.limit,
                    offset=request.offset,
                    enable_ai_reranking=request.enable_ai_reranking,
                    ai_weight=request.ai_weight,
                    ai_reranking_instructions=request.ai_reranking_instructions
                )
                results = all_results
                answer = None
                total_results = search_metadata.get('total_results', len(results))
        else:
            # Regular search with AI reranking
            all_results, search_metadata = await search_system.search(
                query=search_query,
                limit=request.limit,
                offset=request.offset,
                enable_ai_reranking=request.enable_ai_reranking,
                ai_weight=request.ai_weight,
                ai_reranking_instructions=request.ai_reranking_instructions
            )
            # Results are already paginated by the search system
            results = all_results
            answer = None
            total_results = search_metadata.get('total_results', len(results))
        
        # Apply filters if provided
        if request.filters:
            results = _apply_filters(results, request.filters)
        
        # Handle zero results
        if not results or len(results) == 0:
            logger.warning(f"Zero results for query: {request.query}")
            try:
                from zero_result_handler import ZeroResultHandler
                handler = ZeroResultHandler(llm_client=llm_client, search_system=search_system)
                zero_result_data = await handler.handle_zero_results(request.query, request.filters)
                
                # Track zero result for analytics
                handler.track_zero_result(request.query)
                
            except Exception as e:
                logger.error(f"Error handling zero results: {e}")
                zero_result_data = {
                    'message': 'No results found. Try different keywords.',
                    'suggestions': []
                }
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Calculate pagination metadata
        has_more = (request.offset + request.limit) < total_results
        
        logger.info(f"Pagination: offset={request.offset}, limit={request.limit}, total={total_results}, has_more={has_more}")
        
        # Return JSON response directly (avoid Pydantic serialization issues)
        response_content = {
            "success": True,
            "results": results,
            "pagination": {
                "offset": request.offset,
                "limit": request.limit,
                "has_more": has_more,
                "next_offset": request.offset + request.limit,
                "total_results": total_results
            },
            "metadata": {
                "query": request.query,
                "total_results": total_results,
                "returned_results": len(results),
                "response_time": processing_time * 1000,  # Convert to milliseconds
                "has_answer": answer is not None,
                "answer": answer or "",
                "query_analysis": query_analysis,
                **search_metadata  # Include AI reranking metadata
            }
        }
        
        # Add zero-result handling data if applicable
        if zero_result_data:
            response_content["zero_result_handling"] = zero_result_data
        
        return JSONResponse(content=response_content)
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Search failed: {str(e)}",
                "results": [],
                "metadata": {
                    "query": request.query,
                    "response_time": processing_time * 1000,  # Convert to milliseconds
                    "status_code": 500
                }
            }
        )


@app.post("/index")
async def index_content(request: IndexRequest, background_tasks: BackgroundTasks = None):
    """Index WordPress content."""
    start_time = datetime.utcnow()
    
    try:
        # Check if services are initialized
        if not search_system:
            logger.error("Search system not initialized")
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": "Search service not initialized. Check Railway logs.",
                    "indexed_count": 0,
                    "total_count": 0,
                    "processing_time": 0
                }
            )
        
        if not wp_client:
            logger.error("WordPress client not initialized")
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": "WordPress service not initialized. Check Railway logs.",
                    "indexed_count": 0,
                    "total_count": 0,
                    "processing_time": 0
                }
            )
        
        # Check if index already exists
        try:
            stats = search_system.get_stats()
            if stats.get('total_documents', 0) > 0 and not request.force_reindex:
                processing_time = (datetime.utcnow() - start_time).total_seconds()
                return JSONResponse(
                    content={
                        "success": True,
                        "message": "Index already exists. Use force_reindex=true to reindex.",
                        "indexed_count": stats.get('total_documents', 0),
                        "total_count": stats.get('total_documents', 0),
                        "processing_time": processing_time
                    }
                )
        except Exception as e:
            logger.warning(f"Could not get stats: {e}")
        
        # Fetch content from WordPress
        logger.info("Fetching content from WordPress...")
        if request.post_types:
            logger.info(f"Fetching only selected post types: {request.post_types}")
        else:
            logger.info("Fetching all available post types")
            
        try:
            documents = await wp_client.get_all_content(request.post_types)
            logger.info(f"Fetched {len(documents) if documents else 0} documents from WordPress")
        except Exception as e:
            logger.error(f"Failed to fetch WordPress content: {e}", exc_info=True)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Failed to fetch WordPress content: {str(e)}",
                    "indexed_count": 0,
                    "total_count": 0,
                    "processing_time": processing_time
                }
            )
        
        if not documents:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No content found in WordPress",
                    "indexed_count": 0,
                    "total_count": 0,
                    "processing_time": processing_time
                }
            )
        
        # Index documents
        logger.info(f"Indexing {len(documents)} documents...")
        try:
            success = await search_system.index_documents(documents)
        except Exception as e:
            logger.error(f"Failed to index documents: {e}", exc_info=True)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Failed to index documents: {str(e)}",
                    "indexed_count": 0,
                    "total_count": len(documents),
                    "processing_time": processing_time
                }
            )
        
        if not success:
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Failed to index documents",
                    "indexed_count": 0,
                    "total_count": len(documents),
                    "processing_time": processing_time
                }
            )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Successfully indexed {len(documents)} documents",
                "indexed_count": len(documents),
                "total_count": len(documents),
                "processing_time": processing_time
            }
        )
        
    except Exception as e:
        logger.error(f"Indexing error: {e}", exc_info=True)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Indexing failed: {str(e)}",
                "indexed_count": 0,
                "total_count": 0,
                "processing_time": processing_time
            }
        )


@app.post("/index-single")
async def index_single_document(request: dict):
    """Index a single document (for auto-indexing)."""
    if not search_system:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Search service not initialized"
            }
        )
    
    try:
        document = request.get('document')
        if not document:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "No document provided"
                }
            )
        
        logger.info(f"Auto-indexing single document: {document.get('title', 'Unknown')}")
        
        # Index the single document
        success = await search_system.index_documents([document])
        
        if success:
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Successfully indexed: {document.get('title', 'document')}"
                }
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Failed to index document"
                }
            )
            
    except Exception as e:
        logger.error(f"Single document index error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Indexing failed: {str(e)}"
            }
        )


@app.delete("/delete-document/{document_id}")
async def delete_document(document_id: str):
    """Delete a single document from the index."""
    if not search_system:
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "Search service not initialized"
            }
        )
    
    try:
        logger.info(f"Deleting document from index: {document_id}")
        
        # Delete from Qdrant if available
        if search_system.qdrant_manager:
            search_system.qdrant_manager.delete_points([document_id])
        
        # Remove from local cache
        search_system.documents = [d for d in search_system.documents if d.get('id') != document_id]
        
        return JSONResponse(
            content={
                "success": True,
                "message": f"Successfully deleted document: {document_id}"
            }
        )
            
    except Exception as e:
        logger.error(f"Document deletion error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Deletion failed: {str(e)}"
            }
        )


@app.delete("/collection")
async def delete_collection():
    """Delete the search collection."""
    if not search_system:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        success = search_system.qdrant_manager.delete_collection()
        if success:
            return {"message": "Collection deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete collection")
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")

@app.get("/test-wp-fetch")
async def test_wp_fetch():
    """Test WordPress content fetching."""
    if not wp_client:
        raise HTTPException(status_code=503, detail="WordPress client not initialized")
    
    try:
        # Test fetching a small amount of content
        logger.info("Testing WordPress content fetch...")
        documents = await wp_client.get_all_content()
        
        return {
            "message": "WordPress fetch test completed",
            "document_count": len(documents),
            "sample_documents": documents[:3] if documents else []
        }
        
    except Exception as e:
        logger.error(f"WordPress fetch test error: {e}")
        raise HTTPException(status_code=500, detail=f"WordPress fetch test failed: {str(e)}")

@app.post("/test-index")
async def test_index():
    """Test indexing with minimal data."""
    if not search_system:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Create minimal test documents
        test_docs = [
            {
                "id": "test1",
                "title": "Energy Audit Services",
                "slug": "energy-audit",
                "type": "post",
                "url": "https://www.scsengineers.com/energy-audit/",
                "date": "2024-01-01",
                "modified": "2024-01-01",
                "author": "SCS Engineers",
                "categories": [],
                "tags": [],
                "excerpt": "Professional energy audit services for industrial facilities.",
                "content": "SCS Engineers provides comprehensive energy audit services to help industrial facilities reduce energy costs and improve efficiency. Our certified energy auditors use advanced tools and techniques to identify energy-saving opportunities.",
                "word_count": 25
            },
            {
                "id": "test2", 
                "title": "Environmental Consulting",
                "slug": "environmental-consulting",
                "type": "post",
                "url": "https://www.scsengineers.com/environmental-consulting/",
                "date": "2024-01-02",
                "modified": "2024-01-02",
                "author": "SCS Engineers",
                "categories": [],
                "tags": [],
                "excerpt": "Expert environmental consulting services.",
                "content": "SCS Engineers offers environmental consulting services including environmental impact assessments, remediation planning, and regulatory compliance assistance.",
                "word_count": 20
            }
        ]
        
        # Index test documents
        success = await search_system.index_documents(test_docs)
        
        if success:
            return {"message": "Test indexing successful", "documents": len(test_docs)}
        else:
            raise HTTPException(status_code=500, detail="Test indexing failed")
            
    except Exception as e:
        logger.error(f"Test indexing error: {e}")
        raise HTTPException(status_code=500, detail=f"Test indexing failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get indexing and search statistics."""
    if not search_system:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        stats = search_system.get_stats()
        return {
            "index_stats": stats,
            "service_info": {
                "api_version": settings.api_version,
                "max_search_results": settings.max_search_results,
                "search_timeout": settings.search_timeout
            }
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/suggest")
async def get_suggestions(
    query: str = Query(..., description="Partial query for suggestions", min_length=2),
    limit: int = Query(default=5, ge=1, le=10, description="Maximum suggestions")
):
    """Get query suggestions based on partial input."""
    try:
        # Import suggestion engine
        from suggestions import SuggestionEngine
        
        # Initialize suggestion engine with LLM client
        suggestion_engine = SuggestionEngine(llm_client=llm_client)
        
        # Get suggestions
        suggestions = await suggestion_engine.get_suggestions(
            partial_query=query,
            limit=limit,
            include_popular=True
        )
        
        return {
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions)
        }
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        # Fallback to simple expansion if available
        if llm_client:
            try:
                fallback = llm_client.expand_query(query)
                return {
                    "query": query,
                    "suggestions": fallback[:limit],
                    "count": len(fallback[:limit]),
                    "fallback": True
                }
            except:
                pass
        
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


# Helper functions
def _apply_filters(results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply filters to search results."""
    filtered_results = []
    
    for result in results:
        include = True
        
        # Filter by content type
        if "type" in filters and result.get("type") != filters["type"]:
            include = False
        
        # Filter by author
        if "author" in filters and result.get("author") != filters["author"]:
            include = False
        
        # Filter by categories
        if "categories" in filters:
            result_categories = [cat["slug"] for cat in result.get("categories", [])]
            filter_categories = filters["categories"]
            if isinstance(filter_categories, str):
                filter_categories = [filter_categories]
            
            if not any(cat in result_categories for cat in filter_categories):
                include = False
        
        # Filter by tags
        if "tags" in filters:
            result_tags = [tag["slug"] for tag in result.get("tags", [])]
            filter_tags = filters["tags"]
            if isinstance(filter_tags, str):
                filter_tags = [filter_tags]
            
            if not any(tag in result_tags for tag in filter_tags):
                include = False
        
        if include:
            filtered_results.append(result)
    
    return filtered_results


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info"
    )
