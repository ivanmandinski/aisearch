"""
Offline evaluation harness for the hybrid search pipeline.

Usage:
    python tests/evaluation/run_offline_evaluation.py

This script loads a small set of queries from ``sample_queries.json`` and runs
them through the in-process ``SimpleHybridSearch`` instance.  The default data
uses the built-in sample documents that ship with the backend so the evaluation
can run without access to production content or an AI reranker.

You can extend ``sample_queries.json`` with your own queries, expected URLs, or
keyword checks to produce richer metrics (NDCG / Recall / etc.).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from statistics import mean
from typing import Dict, List, Tuple

from simple_hybrid_search import SimpleHybridSearch


DATASET_PATH = Path(__file__).parent / "sample_queries.json"
DEFAULT_LIMIT = 10


def _compute_mrr(ranks: List[int]) -> float:
    """Compute Mean Reciprocal Rank for the provided ranks."""
    if not ranks:
        return 0.0
    best_rank = min(ranks)
    return 1.0 / best_rank if best_rank > 0 else 0.0


def _contains_keywords(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return all(keyword.lower() in lowered for keyword in keywords)


async def evaluate_case(
    search_system: SimpleHybridSearch, case: Dict[str, any], limit: int = DEFAULT_LIMIT
) -> Tuple[Dict[str, any], Dict[str, any]]:
    """
    Execute a single query against the search system and gather evaluation metrics.
    """
    query = case["query"]
    expected_urls = case.get("expected_urls", [])
    expected_keywords = case.get("expected_keywords", [])

    results, metadata = await search_system.search(
        query=query,
        limit=limit,
        offset=0,
        enable_ai_reranking=False,  # offline evaluation defaults to TF-IDF/vector only
        ai_weight=0.7,
    )

    # Determine hit ranks for expected URLs
    ranks: List[int] = []
    for expected_url in expected_urls:
        for idx, result in enumerate(results, start=1):
            if result.get("url") == expected_url:
                ranks.append(idx)
                break

    mrr = _compute_mrr(ranks)

    top_result = results[0] if results else {}
    keyword_hit = False
    if expected_keywords and top_result:
        text_blob = " ".join(
            [
                top_result.get("title", ""),
                top_result.get("excerpt", ""),
                top_result.get("content", ""),
            ]
        )
        keyword_hit = _contains_keywords(text_blob, expected_keywords)

    evaluation = {
        "query": query,
        "result_count": len(results),
        "mrr": mrr,
        "expected_hits": len(ranks),
        "keyword_hit": keyword_hit,
        "notes": case.get("notes", ""),
    }

    return evaluation, metadata


async def run_evaluation() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset file not found at {DATASET_PATH}. "
            "Create it or adjust DATASET_PATH before running evaluation."
        )

    with DATASET_PATH.open("r", encoding="utf-8") as fh:
        dataset = json.load(fh)

    if not dataset:
        print("No evaluation cases defined. Update sample_queries.json and rerun.")
        return

    search_system = SimpleHybridSearch()

    evaluations: List[Dict[str, any]] = []
    for case in dataset:
        evaluation, _metadata = await evaluate_case(search_system, case)
        evaluations.append(evaluation)
        print(
            f"[{evaluation['query']}] "
            f"MRR={evaluation['mrr']:.3f} "
            f"hits={evaluation['expected_hits']} "
            f"keyword_hit={'yes' if evaluation['keyword_hit'] else 'no'}"
        )

    overall_mrr = mean(ev["mrr"] for ev in evaluations) if evaluations else 0.0
    print("\n=== Aggregate Metrics ===")
    print(f"Queries evaluated: {len(evaluations)}")
    print(f"Mean Reciprocal Rank: {overall_mrr:.3f}")
    keyword_success_rate = (
        mean(1.0 if ev["keyword_hit"] else 0.0 for ev in evaluations) if evaluations else 0.0
    )
    print(f"Keyword coverage (top result): {keyword_success_rate:.3f}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())

