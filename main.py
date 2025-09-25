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
from wordpress_client import WordPressContentFetcher
from llamaindex_orchestrator import LlamaIndexOrchestrator
from cerebras_llm import CerebrasLLM

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
orchestrator = None
llm_client = None
wp_client = None


# Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    include_answer: bool = Field(default=False, description="Whether to include LLM-generated answer")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Search filters")


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    processing_time: float
    answer: Optional[str] = None
    query_analysis: Optional[Dict[str, Any]] = None


class IndexRequest(BaseModel):
    force_reindex: bool = Field(default=False, description="Force reindexing even if index exists")


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
    global orchestrator, llm_client, wp_client
    
    try:
        logger.info("Starting hybrid search service...")
        
        # Initialize services
        orchestrator = LlamaIndexOrchestrator()
        llm_client = CerebrasLLM()
        wp_client = WordPressContentFetcher()
        
        # Test connections
        if not llm_client.test_connection():
            logger.warning("Cerebras LLM connection test failed")
        
        logger.info("Hybrid search service started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    global orchestrator, wp_client
    
    try:
        if orchestrator:
            orchestrator.close()
        if wp_client:
            await wp_client.close()
        logger.info("Hybrid search service shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Hybrid Search API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services_status = {}
    
    try:
        # Check Qdrant connection
        if orchestrator:
            stats = orchestrator.get_index_stats()
            services_status["qdrant"] = "healthy" if stats.get('total_documents', 0) >= 0 else "unhealthy"
        else:
            services_status["qdrant"] = "not_initialized"
        
        # Check Cerebras LLM
        if llm_client and llm_client.test_connection():
            services_status["cerebras_llm"] = "healthy"
        else:
            services_status["cerebras_llm"] = "unhealthy"
        
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
        logger.error(f"Health check error: {e}")
        services_status = {"error": str(e)}
        overall_status = "unhealthy"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services_status
    )


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Perform hybrid search on indexed content."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Search service not initialized")
    
    start_time = datetime.utcnow()
    
    try:
        # Process query with LLM if available
        query_analysis = None
        if llm_client:
            query_analysis = await llm_client.process_query_async(request.query)
            search_query = query_analysis.get("rewritten_query", request.query)
        else:
            search_query = request.query
        
        # Perform search
        results = orchestrator.search(search_query, limit=request.limit)
        
        # Apply filters if provided
        if request.filters:
            results = _apply_filters(results, request.filters)
        
        # Generate answer if requested
        answer = None
        if request.include_answer and llm_client and results:
            answer = llm_client.generate_answer(request.query, results)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            processing_time=processing_time,
            answer=answer,
            query_analysis=query_analysis
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/index", response_model=IndexResponse)
async def index_content(request: IndexRequest, background_tasks: BackgroundTasks):
    """Index WordPress content."""
    if not orchestrator or not wp_client:
        raise HTTPException(status_code=503, detail="Indexing service not initialized")
    
    start_time = datetime.utcnow()
    
    try:
        # Check if index already exists
        stats = orchestrator.get_index_stats()
        if stats.get('total_documents', 0) > 0 and not request.force_reindex:
            return IndexResponse(
                success=True,
                message="Index already exists. Use force_reindex=true to reindex.",
                documents_indexed=stats.get('total_documents', 0),
                processing_time=(datetime.utcnow() - start_time).total_seconds()
            )
        
        # Fetch content from WordPress
        logger.info("Fetching content from WordPress...")
        documents = await wp_client.get_all_content()
        
        if not documents:
            raise HTTPException(status_code=404, detail="No content found in WordPress")
        
        # Index documents
        logger.info(f"Indexing {len(documents)} documents...")
        success = orchestrator.index_documents(documents)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to index documents")
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return IndexResponse(
            success=True,
            message=f"Successfully indexed {len(documents)} documents",
            documents_indexed=len(documents),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get indexing and search statistics."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        stats = orchestrator.get_index_stats()
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
    query: str = Query(..., description="Partial query for suggestions"),
    limit: int = Query(default=5, ge=1, le=10, description="Maximum suggestions")
):
    """Get query suggestions based on partial input."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM service not available")
    
    try:
        suggestions = llm_client.expand_query(query)
        return {
            "query": query,
            "suggestions": suggestions[:limit]
        }
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
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
