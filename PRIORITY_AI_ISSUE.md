# 🐛 Current Issue: AI Reranking Overrides Post Type Priority

## Current Flow (BROKEN)

1. **Search**: TF-IDF + Vector search returns candidates
2. **Post Type Priority Applied**: `[post:0.9, page:0.9, post:0.85]` sorted by priority
3. **AI Reranking**: Receives prioritized list
4. **AI Sorts by hybrid_score**: Line 571 in `cerebras_llm.py`
   ```python
   reranked_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
   ```
5. **Result**: Priority is LOST! 🔴

## The Problem

Look at `cerebras_llm.py` line 571:

```python
# This sorts ONLY by hybrid_score, ignoring priority!
reranked_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
```

The AI reranking calculates:
```python
hybrid_score = (tfidf_score * tfidf_weight) + (ai_score * ai_weight)
```

But it doesn't include priority in the calculation!

## What Happens

**Before AI Reranking** (after priority applied):
```
1. post: score=0.9  (priority=0)
2. page: score=0.9   (priority=1)
3. post: score=0.85 (priority=0)
```

**After AI Reranking** (if AI gives page higher score):
```
1. page: hybrid_score=0.92 (AI liked it more!)
2. post: hybrid_score=0.91
3. post: hybrid_score=0.85
```

Priority is LOST! 🔴

## Solution Options

### Option 1: Apply Priority AFTER AI Reranking
Pros: AI gets full control, then we enforce priority
Cons: Might undo good AI decisions

### Option 2: Include Priority in Hybrid Score
Pros: Single unified scoring
Cons: Adds complexity to scoring logic

### Option 3: Apply Priority WITHIN Score Tiers
Pros: Best of both worlds
Cons: More complex sorting logic

## Recommended Fix

Apply priority WITHIN score tiers (Option 3):

```python
# Sort by hybrid_score first, then by priority within same score
reranked_results.sort(key=lambda x: (x.get('hybrid_score', 0), -get_priority(x)), reverse=True)
```

This means:
- Results with same hybrid_score will be ordered by priority
- Results with different scores are ordered by score (AI has control)
- Priority is enforced as a tie-breaker

## Current Status

✅ Post Type Priority is implemented  
✅ AI Reranking is working  
❌ They conflict with each other

I need to update the sorting logic to combine both properly!

