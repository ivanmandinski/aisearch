"""
FastAPI application exposing the hybrid search endpoints for the WordPress plugin.

The implementation focuses on the `/search` endpoint, providing intent-aware
responses together with pagination and metadata consumed by the WordPress
admin dashboards.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import settings
from error_responses import (
    SearchError,
    ValidationError,
    create_error_response,
    create_success_response,
    service_unavailable,
    validate_search_params,
)
from health_checker import get_health_status, get_quick_health_status
from simple_hybrid_search import SimpleHybridSearch
from cerebras_llm import CerebrasLLM
from wordpress_client import WordPressContentFetcher


logger = logging.getLogger("hybrid_search_api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Hybrid search API for WordPress content.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)

search_system: Optional[SimpleHybridSearch] = None
llm_client: Optional[CerebrasLLM] = None
wp_client: Optional[WordPressContentFetcher] = None


BASE_DIR = Path(__file__).resolve().parent
WORDPRESS_SOURCE_OVERRIDE_FILE = BASE_DIR / "wordpress_source_override.json"


def _persist_wordpress_source_overrides() -> None:
    """Persist the active WordPress source configuration to disk."""
    data = {
        "base_url": settings.wordpress_api_url or "",
        "username": settings.wordpress_username or "",
        "password": settings.wordpress_password or "",
    }

    try:
        WORDPRESS_SOURCE_OVERRIDE_FILE.write_text(json.dumps(data, indent=2))
    except Exception as exc:
        logger.warning("Failed to persist WordPress source overrides: %s", exc)


def _load_wordpress_source_overrides() -> None:
    """Load any persisted WordPress source configuration."""
    if not WORDPRESS_SOURCE_OVERRIDE_FILE.exists():
        return

    try:
        data = json.loads(WORDPRESS_SOURCE_OVERRIDE_FILE.read_text())
    except Exception as exc:
        logger.warning("Failed to read WordPress source overrides: %s", exc)
        return

    base_url = (data.get("base_url") or "").strip()
    username = data.get("username") or ""
    password = data.get("password") or ""

    if base_url:
        settings.wordpress_api_url = base_url.rstrip("/")
    settings.wordpress_username = username
    settings.wordpress_password = password


async def update_wordpress_client(
    base_url: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    """Rebuild the global WordPress client when admin overrides change."""
    global wp_client

    normalized = base_url.strip().rstrip("/") if base_url else (settings.wordpress_api_url or "").rstrip("/")
    current_base = (settings.wordpress_api_url or "").rstrip("/")
    user = (username.strip() if isinstance(username, str) else settings.wordpress_username or "").strip()
    pwd = (password.strip() if isinstance(password, str) else settings.wordpress_password or "").strip()

    changed = False
    if base_url and normalized != current_base:
        changed = True
    if username is not None and user != (settings.wordpress_username or ""):
        changed = True
    if password is not None and pwd != (settings.wordpress_password or ""):
        changed = True

    if not changed:
        return

    settings.wordpress_api_url = normalized
    if username is not None:
        settings.wordpress_username = user
    if password is not None:
        settings.wordpress_password = pwd

    logger.info("Switching WordPress content source to %s", normalized or "(unset)")

    old_client = wp_client
    wp_client = WordPressContentFetcher(
        base_url=settings.wordpress_api_url or None,
        username=settings.wordpress_username or None,
        password=settings.wordpress_password or None,
    )
    _persist_wordpress_source_overrides()

    if old_client:
        try:
            await old_client.close()
        except Exception as exc:
            logger.warning("Failed to close previous WordPress client: %s", exc)


class SearchFilters(BaseModel):
    type: Optional[str] = Field(default=None, description="Filter by post type")
    date: Optional[str] = Field(default=None, description="Date filter: day|week|month|year")
    sort: Optional[str] = Field(default=None, description="Sort order: date-desc|date-asc|title-asc")


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    include_answer: bool = Field(default=False)
    filters: Optional[SearchFilters] = None
    ai_instructions: Optional[str] = None
    enable_ai_reranking: bool = Field(default=True, description="Whether to use AI reranking")
    wordpress_api_url: Optional[str] = Field(default=None, description="WordPress API URL")
    wordpress_username: Optional[str] = Field(default=None, description="WordPress username")
    wordpress_password: Optional[str] = Field(default=None, description="WordPress password")
    ai_reranking_instructions: Optional[str] = Field(default="", description="Custom AI reranking instructions")
    ai_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for AI score")
    post_type_priority: Optional[List[str]] = Field(default=None, description="Post types in priority order")
    behavioral_signals: Optional[Dict[str, Any]] = Field(default=None, description="Behavioral signals for ranking")
    rewrite_excerpts: bool = Field(default=False, description="Whether to use AI to rewrite excerpts")


class IndexSingleRequest(BaseModel):
    """Request model for single document indexing."""
    document: Dict[str, Any] = Field(..., description="Document to index")


class IndexBatchRequest(BaseModel):
    """Request model for batch document indexing."""
    documents: List[Dict[str, Any]] = Field(..., description="List of documents to index", min_length=1, max_length=100)


class IndexRequest(BaseModel):
    force_reindex: bool = Field(default=False)
    post_types: Optional[List[str]] = None
    wordpress_api_url: Optional[str] = Field(default=None)
    wordpress_username: Optional[str] = None
    wordpress_password: Optional[str] = None


def _normalize_ai_flag(value: Optional[bool]) -> bool:
    if not settings.enable_ai_rerank:
        return False
    if isinstance(value, bool):
        return value and settings.enable_ai_rerank
    return settings.enable_ai_rerank


def _parse_result_date(result: Dict[str, Any]) -> datetime:
    raw = result.get("date") or ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min


def _apply_filters(results: List[Dict[str, Any]], filters: Optional[SearchFilters]) -> List[Dict[str, Any]]:
    if not filters or not results:
        return results

    filtered = results

    if filters.type:
        filtered = [item for item in filtered if item.get("type") == filters.type]

    if filters.date:
        now = datetime.utcnow()
        window = {
            "day": timedelta(days=1),
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
            "year": timedelta(days=365),
        }.get(filters.date)
        if window:
            cutoff = now - window
            filtered = [item for item in filtered if _parse_result_date(item) >= cutoff]

    if filters.sort == "date-asc":
        filtered = sorted(filtered, key=_parse_result_date)
    elif filters.sort == "title-asc":
        filtered = sorted(filtered, key=lambda item: item.get("title", "").lower())
    elif filters.sort == "date-desc":
        filtered = sorted(filtered, key=_parse_result_date, reverse=True)

    return filtered


def _build_pagination(total: int, limit: int, offset: int, returned: int) -> Dict[str, Any]:
    next_offset = offset + returned
    has_more = next_offset < total and returned >= limit
    return {
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
        "next_offset": next_offset if has_more else None,
        "total_results": total,
    }


@app.on_event("startup")
async def on_startup() -> None:
    global search_system, llm_client, wp_client

    logger.info("Starting hybrid search service...")

    _load_wordpress_source_overrides()

    if search_system is None:
        try:
            search_system = SimpleHybridSearch()
            logger.info("Search system initialised successfully")
        except Exception as exc:
            logger.exception("Failed to initialise search system: %s", exc)
            search_system = None

    if llm_client is None:
        try:
            llm_client = CerebrasLLM()
            logger.info("Cerebras LLM client initialised")
        except Exception as exc:
            logger.warning("Cerebras LLM unavailable: %s", exc)
            llm_client = None

    if wp_client is None:
        try:
            wp_client = WordPressContentFetcher(
                base_url=settings.wordpress_api_url or None,
                username=settings.wordpress_username or None,
                password=settings.wordpress_password or None,
            )
            logger.info("WordPress content fetcher initialised")
        except Exception as exc:
            logger.warning("Failed to initialise WordPressContentFetcher: %s", exc)
            wp_client = None


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global search_system, wp_client
    try:
        if search_system:
            search_system.close()
        if wp_client:
            await wp_client.close()
    except Exception as exc:
        logger.warning("Shutdown cleanup encountered an error: %s", exc)


@app.post("/search")
async def search_endpoint(request: SearchRequest) -> Dict[str, Any]:
    if search_system is None:
        return service_unavailable("search", {"message": "Search system not initialised"})

    request_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    try:
        validate_search_params(request.query, request.limit, request.offset)
    except ValidationError as exc:
        return create_error_response(exc, request_id=request_id)

    enable_ai = _normalize_ai_flag(request.enable_ai_reranking)
    search_query = request.query.strip()

    if request.wordpress_api_url:
        await update_wordpress_client(
            base_url=request.wordpress_api_url,
            username=request.wordpress_username,
            password=request.wordpress_password,
        )

    query_analysis: Optional[Dict[str, Any]] = None
    if llm_client:
        try:
            query_analysis = await llm_client.process_query_async(search_query)
            query_context = query_analysis.get("query_context", {}) if query_analysis else {}
            if query_analysis and query_context:
                logger.info(
                    "🧠 Query context: intent=%s confidence=%.2f entities=%s",
                    query_context.get("intent"),
                    query_context.get("confidence", 0.0),
                    query_context.get("entities", {}),
                )
            rewritten = query_analysis.get("rewritten_query") if query_analysis else None
            if rewritten and rewritten.strip() and rewritten != search_query:
                search_query = rewritten.strip()
        except Exception as exc:
            logger.warning("Query analysis failed: %s", exc)
            query_analysis = None

    ai_instructions = request.ai_reranking_instructions or ""
    if request.ai_instructions:
        ai_instructions = (
            f"{ai_instructions}\n\n{request.ai_instructions}" if ai_instructions else request.ai_instructions
        )

    try:
        results, search_metadata = await search_system.search(
            query=search_query,
            limit=request.limit,
            offset=request.offset,
            enable_ai_reranking=enable_ai,
            ai_weight=request.ai_weight,
            ai_reranking_instructions=ai_instructions,
            post_type_priority=request.post_type_priority,
            behavioral_signals=request.behavioral_signals,
        )
    except SearchError as exc:
        return create_error_response(exc, request_id=request_id)
    except Exception as exc:
        logger.exception("Search failed: %s", exc)
        return create_error_response(
            SearchError("Search failed", details={"error": str(exc)}), request_id=request_id
        )

    if request.filters:
        results = _apply_filters(results, request.filters)

    # Rewrite excerpts using AI if enabled
    if request.rewrite_excerpts and llm_client and results:
        try:
            logger.info("Rewriting excerpts for %d results", len(results))
            # Rewrite excerpts in parallel for better performance
            rewrite_tasks = []
            for result in results:
                excerpt = result.get("excerpt", "")
                if excerpt and excerpt.strip():
                    title = result.get("title", "")
                    task = llm_client.rewrite_excerpt_async(excerpt, search_query, title)
                    rewrite_tasks.append((result, task))
            
            # Execute all rewrites in parallel
            if rewrite_tasks:
                rewritten_excerpts = await asyncio.gather(*[task for _, task in rewrite_tasks], return_exceptions=True)
                for (result, _), rewritten in zip(rewrite_tasks, rewritten_excerpts):
                    if not isinstance(rewritten, Exception) and rewritten:
                        result["excerpt"] = rewritten
                        result["excerpt_rewritten"] = True
                    else:
                        result["excerpt_rewritten"] = False
            logger.info("Excerpt rewriting completed")
        except Exception as exc:
            logger.warning("Failed to rewrite excerpts: %s", exc)
            # Continue with original excerpts if rewriting fails

    total_available = search_metadata.get("total_results", len(results))
    pagination = _build_pagination(total_available, request.limit, request.offset, len(results))

    # Generate AI answer if requested (only on first page)
    answer = None
    if request.include_answer and request.offset == 0:
        if llm_client and results:
            try:
                logger.info("Generating AI answer for query: %s", search_query)
                # Use top results for answer generation
                from constants import MAX_SEARCH_RESULTS_FOR_ANSWER
                top_results = results[:MAX_SEARCH_RESULTS_FOR_ANSWER]
                answer = llm_client.generate_answer(search_query, top_results, ai_instructions)
                logger.info("AI answer generated successfully (length: %d)", len(answer) if answer else 0)
            except Exception as exc:
                logger.error("Failed to generate AI answer: %s", exc)
                answer = None
        elif not llm_client:
            logger.warning("LLM client not available, cannot generate answer")
        elif not results:
            logger.info("No results to generate answer from")

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    metadata = {
        "query": request.query,
        "response_time_ms": round(elapsed * 1000, 2),
        "total_results": len(results),
        "query_analysis": query_analysis,
        "query_context": query_analysis.get("query_context") if query_analysis else None,
        "ai_reranking_used": search_metadata.get("ai_reranking_used", enable_ai),
        "request_id": request_id,
        "feature_flags": {
            "ai_rerank": settings.enable_ai_rerank,
            "ctr_boost": settings.enable_ctr_boost,
        },
        "behavioral_signals": request.behavioral_signals,
        "behavioral_applied": search_metadata.get("behavioral_applied"),
        "answer": answer,  # Include answer in metadata for frontend
        **search_metadata,
    }

    payload = {
        "results": results,
        "answer": answer,  # Also include at top level for compatibility
        "metadata": metadata,
        "pagination": pagination,
    }

    return create_success_response(payload, metadata={"request_id": request_id})


@app.post("/index")
async def index_endpoint(request: IndexRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    logger.info("Received indexing request (force=%s, post_types=%s)", request.force_reindex, request.post_types)

    if request.wordpress_api_url or request.wordpress_username or request.wordpress_password:
        await update_wordpress_client(
            base_url=request.wordpress_api_url,
            username=request.wordpress_username,
            password=request.wordpress_password,
        )

    if wp_client is None:
        return service_unavailable("index", {"message": "WordPress client unavailable"})

    if search_system is None:
        return service_unavailable("index", {"message": "Search system not initialised"})

    try:
        # Log post types being indexed
        if request.post_types:
            logger.info(f"🎯 Indexing selected post types: {request.post_types}")
        else:
            logger.info("📋 No post types specified - will index all public post types with REST API support")

        # Fetch content from WordPress
        logger.info("Starting content fetch from WordPress...")
        all_content = await wp_client.get_all_content(selected_types=request.post_types)
        
        if not all_content:
            logger.warning("No content fetched from WordPress")
            return create_success_response(
                {
                    "status": "completed",
                    "message": "No content to index",
                    "indexed_count": 0,
                    "post_types": request.post_types or [],
                }
            )

        # Log breakdown by post type
        type_counts = {}
        for item in all_content:
            item_type = item.get('type', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        
        logger.info(f"📊 Content fetched: {len(all_content)} total items")
        logger.info(f"📊 Breakdown by post type: {type_counts}")

        # Index the content
        logger.info(f"Starting indexing of {len(all_content)} documents...")
        success = await search_system.index_documents(all_content, clear_existing=request.force_reindex)
        
        if success:
            logger.info(f"✅ Successfully indexed {len(all_content)} documents")
            return create_success_response(
                {
                    "status": "completed",
                    "message": f"Successfully indexed {len(all_content)} documents",
                    "indexed_count": len(all_content),
                    "post_types": request.post_types or list(type_counts.keys()),
                    "post_type_breakdown": type_counts,
                }
            )
        else:
            logger.error("❌ Indexing failed")
            return create_error_response(
                SearchError("Indexing failed", details={"message": "Failed to index documents"}),
                request_id=str(uuid.uuid4()),
            )

    except Exception as exc:
        logger.exception("Indexing error: %s", exc)
        return create_error_response(
            SearchError("Indexing failed", details={"error": str(exc)}),
            request_id=str(uuid.uuid4()),
        )


@app.get("/health")
async def health_endpoint() -> JSONResponse:
    try:
        data = await get_health_status()
        return JSONResponse(content=data)
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc),
            },
        )


@app.get("/health/quick")
async def quick_health_endpoint() -> JSONResponse:
    try:
        data = await get_quick_health_status()
        return JSONResponse(content=data)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(exc),
            },
        )


@app.get("/stats")
async def stats_endpoint() -> Dict[str, Any]:
    """Get search and indexing statistics."""
    if search_system is None:
        return create_error_response(
            SearchError("Search system not initialised", details={"message": "Search system not available"}),
            request_id=str(uuid.uuid4()),
        )
    
    try:
        index_stats = search_system.get_stats()
        service_info = {
            "api_version": settings.api_version,
            "max_search_results": settings.max_search_results,
            "search_timeout": settings.search_timeout,
        }
        
        return create_success_response(
            {
                "index_stats": index_stats,
                "service_info": service_info,
            }
        )
    except Exception as exc:
        logger.exception("Failed to get stats: %s", exc)
        return create_error_response(
            SearchError("Failed to retrieve statistics", details={"error": str(exc)}),
            request_id=str(uuid.uuid4()),
        )


@app.post("/index-single")
async def index_single_endpoint(request: IndexSingleRequest) -> Dict[str, Any]:
    """Index a single document (for real-time updates)."""
    logger.info("Received single document indexing request")
    
    if search_system is None:
        return service_unavailable("index-single", {"message": "Search system not initialised"})
    
    try:
        document = request.document
        
        # Validate required fields
        if "id" not in document:
            return create_error_response(
                ValidationError("Document must have an 'id' field", field="document.id"),
                request_id=str(uuid.uuid4()),
            )
        
        # Index the single document (don't clear existing collection)
        success = await search_system.index_documents([document], clear_existing=False)
        
        if success:
            title = document.get("title", document.get("id", "Unknown"))
            logger.info(f"✅ Successfully indexed single document: {title}")
            return create_success_response(
                {
                    "status": "completed",
                    "message": f"Successfully indexed: {title}",
                    "document_id": document.get("id"),
                }
            )
        else:
            logger.error("❌ Single document indexing failed")
            return create_error_response(
                SearchError("Indexing failed", details={"message": "Failed to index document"}),
                request_id=str(uuid.uuid4()),
            )
    
    except Exception as exc:
        logger.exception("Single document indexing error: %s", exc)
        return create_error_response(
            SearchError("Indexing failed", details={"error": str(exc)}),
            request_id=str(uuid.uuid4()),
        )


@app.post("/index-batch")
async def index_batch_endpoint(request: IndexBatchRequest) -> Dict[str, Any]:
    """Index multiple documents in a single batch (more efficient than individual calls)."""
    logger.info(f"Received batch document indexing request for {len(request.documents)} documents")
    
    if search_system is None:
        return service_unavailable("index-batch", {"message": "Search system not initialised"})
    
    try:
        documents = request.documents
        
        # Validate required fields for all documents
        invalid_docs = []
        for i, doc in enumerate(documents):
            if "id" not in doc:
                invalid_docs.append(f"Document at index {i} missing 'id' field")
        
        if invalid_docs:
            return create_error_response(
                ValidationError(f"Invalid documents: {', '.join(invalid_docs)}", field="documents"),
                request_id=str(uuid.uuid4()),
            )
        
        # Index the batch of documents (don't clear existing collection)
        success = await search_system.index_documents(documents, clear_existing=False)
        
        if success:
            logger.info(f"✅ Successfully indexed batch of {len(documents)} documents")
            return create_success_response(
                {
                    "status": "completed",
                    "message": f"Successfully indexed {len(documents)} documents",
                    "indexed_count": len(documents),
                    "document_ids": [doc.get("id") for doc in documents],
                }
            )
        else:
            logger.error("❌ Batch document indexing failed")
            return create_error_response(
                SearchError("Indexing failed", details={"message": "Failed to index documents"}),
                request_id=str(uuid.uuid4()),
            )
    
    except Exception as exc:
        logger.exception("Batch document indexing error: %s", exc)
        return create_error_response(
            SearchError("Indexing failed", details={"error": str(exc)}),
            request_id=str(uuid.uuid4()),
        )


@app.delete("/delete-document/{document_id}")
async def delete_document_endpoint(document_id: str) -> Dict[str, Any]:
    """Delete a document from the search index."""
    logger.info(f"Received delete request for document: {document_id}")
    
    if search_system is None or search_system.qdrant_manager is None:
        return service_unavailable("delete-document", {"message": "Search system not initialised"})
    
    try:
        # Delete the document
        success = search_system.qdrant_manager.delete_document(document_id)
        
        if success:
            logger.info(f"✅ Successfully deleted document: {document_id}")
            return create_success_response(
                {
                    "status": "completed",
                    "message": f"Successfully deleted document: {document_id}",
                    "document_id": document_id,
                }
            )
        else:
            logger.error(f"❌ Failed to delete document: {document_id}")
            return create_error_response(
                SearchError("Deletion failed", details={"message": f"Failed to delete document: {document_id}"}),
                request_id=str(uuid.uuid4()),
            )
    
    except Exception as exc:
        logger.exception("Document deletion error: %s", exc)
        return create_error_response(
            SearchError("Deletion failed", details={"error": str(exc)}),
            request_id=str(uuid.uuid4()),
        )


@app.get("/")
async def root_endpoint() -> Dict[str, Any]:
    return {
        "message": "Hybrid Search API",
        "version": settings.api_version,
        "status": "running",
        "endpoints": {
            "search": "POST /search",
            "index": "POST /index",
            "index_single": "POST /index-single",
            "index_batch": "POST /index-batch",
            "delete_document": "DELETE /delete-document/{document_id}",
            "health": "GET /health",
            "health_quick": "GET /health/quick",
            "stats": "GET /stats",
        },
    }
