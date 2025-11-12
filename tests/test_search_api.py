"""
Integration tests for the FastAPI search endpoints.

These tests stub the search system to avoid requiring a full index and verify
that the API accepts behavioral signals and returns expected payload structure.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pytest
from fastapi.testclient import TestClient

import main


class DummySearchSystem:
    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        enable_ai_reranking: bool = True,
        ai_weight: float = 0.7,
        ai_reranking_instructions: str = "",
        post_type_priority: Optional[List[str]] = None,
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        results = [
            {
                "id": "doc-1",
                "title": f"Result for {query}",
                "url": "https://www.example.com/result",
                "excerpt": "Example excerpt",
                "type": "post",
                "score": 1.0,
                "meta": {"boost_debug": {"behavioral": 1.0}},
            }
        ]
        metadata = {
            "total_results": 1,
            "ai_reranking_used": enable_ai_reranking,
            "behavioral_applied": bool(behavioral_signals),
        }
        return results, metadata

    async def search_with_answer(
        self,
        query: str,
        limit: int = 5,
        offset: int = 0,
        custom_instructions: str = "",
        enable_ai_reranking: bool = True,
        behavioral_signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        results, metadata = await self.search(
            query=query,
            limit=limit,
            offset=offset,
            enable_ai_reranking=enable_ai_reranking,
            behavioral_signals=behavioral_signals,
        )
        return {
            "query": query,
            "answer": "Stub answer",
            "sources": results,
            "source_count": len(results),
            "total_results": metadata.get("total_results", len(results)),
        }


@pytest.fixture(autouse=True)
def stub_search_system(monkeypatch):
    original_search_system = main.search_system
    main.search_system = DummySearchSystem()
    yield
    main.search_system = original_search_system


def test_search_endpoint_accepts_behavioral_signals():
    client = TestClient(main.app)
    payload = {
        "query": "dummy query",
        "limit": 5,
        "offset": 0,
        "behavioral_signals": {
            "ctr": {
                "time_window_days": 30,
                "items": [
                    {"url": "https://www.example.com/result", "weight": 0.3, "clicks": 10}
                ],
            }
        },
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metadata"]["behavioral_applied"] is True
    assert data["results"][0]["meta"]["boost_debug"]["behavioral"] == 1.0


def test_search_endpoint_basic_response_structure():
    client = TestClient(main.app)
    response = client.post("/search", json={"query": "hello world"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "results" in data
    assert "metadata" in data
    assert data["metadata"]["total_results"] >= 0
import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_search_returns_results_and_metadata():
    payload = {"query": "energy audit services", "limit": 5, "offset": 0}
    response = client.post("/search", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert "data" in body

    data = body["data"]
    assert "results" in data
    assert isinstance(data["results"], list)
    assert "metadata" in data
    assert "pagination" in data

    metadata = data["metadata"]
    assert metadata["query"] == payload["query"]
    assert "query_analysis" in metadata
    assert "response_time_ms" in metadata
    assert metadata["request_id"]
    assert "feature_flags" in metadata
    assert isinstance(metadata["feature_flags"], dict)


def test_search_filters_by_type():
    payload = {
        "query": "waste management",
        "limit": 5,
        "offset": 0,
        "filters": {"type": "post"},
    }
    response = client.post("/search", json=payload)
    assert response.status_code == 200

    results = response.json()["data"]["results"]
    assert all(result.get("type") == "post" for result in results)


def test_health_endpoint():
    response = client.get("/health/quick")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload

