"""
Offline evaluation harness for hybrid search ranking quality.

This script reads a set of labeled queries and relevant URLs, executes searches
against a running Hybrid Search API, and reports ranking metrics (MRR, NDCG).

Usage:
    HYBRID_SEARCH_EVAL_API=http://localhost:8000/search \
    python tests/evaluation/run_eval.py
"""
from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path
from typing import Dict, List

import httpx

DATASET_PATH = Path(__file__).with_name("sample_dataset.json")
API_URL = os.environ.get("HYBRID_SEARCH_EVAL_API", "http://localhost:8000/search")
TOP_K = int(os.environ.get("HYBRID_SEARCH_EVAL_TOP_K", 10))


def dcg(relevances: List[int]) -> float:
    return sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))


def ndcg(relevant_ranks: List[int], k: int) -> float:
    if not relevant_ranks:
        return 0.0
    relevances = [1 if (idx + 1) in relevant_ranks else 0 for idx in range(k)]
    ideal = sum(1 / math.log2(idx + 2) for idx in range(min(len(relevant_ranks), k)))
    return dcg(relevances) / ideal if ideal > 0 else 0.0


def mrr(relevant_ranks: List[int]) -> float:
    if not relevant_ranks:
        return 0.0
    return 1.0 / min(relevant_ranks)


async def evaluate_query(client: httpx.AsyncClient, query: str, relevant_urls: List[str]) -> Dict[str, float]:
    payload = {"query": query, "limit": TOP_K, "offset": 0, "include_answer": False}
    response = await client.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    results = data.get("data", {}).get("results", [])

    normalized_relevant = {normalize_url(url) for url in relevant_urls}
    ranks: List[int] = []
    for idx, item in enumerate(results, start=1):
        url = normalize_url(item.get("url", ""))
        if url in normalized_relevant:
            ranks.append(idx)

    metrics = {
        "mrr": mrr(ranks),
        "ndcg": ndcg(ranks, TOP_K),
        "hits": len(ranks),
        "total_relevant": len(normalized_relevant),
    }
    return metrics


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip().lower()
    if url.endswith("/"):
        url = url[:-1]
    return url


async def run_evaluation() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    dataset = json.loads(DATASET_PATH.read_text())
    async with httpx.AsyncClient() as client:
        aggregate = {"mrr": 0.0, "ndcg": 0.0, "queries": 0, "hits": 0, "relevant": 0}
        for entry in dataset:
            query = entry["query"]
            relevant_urls = entry.get("relevant_urls", [])
            metrics = await evaluate_query(client, query, relevant_urls)
            aggregate["queries"] += 1
            aggregate["mrr"] += metrics["mrr"]
            aggregate["ndcg"] += metrics["ndcg"]
            aggregate["hits"] += metrics["hits"]
            aggregate["relevant"] += metrics["total_relevant"]
            print(
                f"{query!r}: MRR={metrics['mrr']:.3f} NDCG@{TOP_K}={metrics['ndcg']:.3f} "
                f"hits={metrics['hits']}/{metrics['total_relevant']}"
            )

        if aggregate["queries"]:
            print("-" * 60)
            print(
                f"Average MRR = {aggregate['mrr'] / aggregate['queries']:.3f} | "
                f"Average NDCG@{TOP_K} = {aggregate['ndcg'] / aggregate['queries']:.3f} | "
                f"Coverage = {aggregate['hits']} / {aggregate['relevant']} relevant URLs surfaced"
            )
        else:
            print("Dataset empty - nothing to evaluate.")


if __name__ == "__main__":
    asyncio.run(run_evaluation())

