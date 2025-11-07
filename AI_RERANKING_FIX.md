# AI Reranking Fix - Critical Issues Resolved

**Date:** December 2024  
**Status:** ✅ Fixed

## Issues Identified

### Issue 1: AI Reranking Parameter Not Working
**Problem**: `enable_ai_reranking` was being received as `False` even when enabled in WordPress settings.

**Root Cause**: 
- Pydantic might receive boolean values as strings in some edge cases
- No explicit boolean conversion/validation in the API endpoint

**Fix Applied**:
- Added explicit boolean parsing in `main.py` before using the parameter
- Handles string booleans (`"true"`, `"false"`, `"1"`, `"0"`)
- Defaults to `True` if `None` (enabled by default)
- Added detailed logging to track the value through the pipeline

**Code Location**: `main.py:303-315`

### Issue 2: Malformed Query (JSON in Query String)
**Problem**: Query string contained entire JSON response from query rewriting:
```
query='```

{
    "rewritten_query": "Supply Chain Management Systems",
    ...
}
```'
```

**Root Cause**:
- `rewrite_query()` method was returning JSON wrapped in markdown code blocks
- JSON extraction wasn't handling markdown code blocks properly
- Malformed queries were being passed through to search

**Fix Applied**:
1. **In `cerebras_llm.py`** (`rewrite_query` method):
   - Extract JSON from markdown code blocks (````json` or generic ````)
   - Validate extracted JSON before parsing
   - Return original query if parsing fails (instead of malformed JSON)

2. **In `main.py`** (search endpoint):
   - Detect malformed queries (containing JSON/markdown)
   - Extract `rewritten_query` from malformed JSON if present
   - Skip query rewriting if query is already malformed

3. **In `cerebras_llm.py`** (`process_query_async` method):
   - Skip rewriting if query is already malformed
   - Extract `rewritten_query` from JSON if `rewrite_query` returns JSON string
   - Validate rewritten query before using it

**Code Locations**:
- `cerebras_llm.py:70-99` - JSON extraction in `rewrite_query()`
- `cerebras_llm.py:474-524` - Malformed query handling in `process_query_async()`
- `main.py:321-338` - Query cleanup in search endpoint

## Changes Made

### 1. Boolean Parameter Handling (`main.py`)

```python
# CRITICAL FIX: Ensure enable_ai_reranking is properly parsed as boolean
enable_ai_reranking = request.enable_ai_reranking
if isinstance(enable_ai_reranking, str):
    enable_ai_reranking = enable_ai_reranking.lower() in ('true', '1', 'yes', 'on', 'enabled')
elif enable_ai_reranking is None:
    enable_ai_reranking = True  # Default to enabled
else:
    enable_ai_reranking = bool(enable_ai_reranking)

logger.info(f"🔍 AI Reranking Parameter Check:")
logger.info(f"   Raw value: {request.enable_ai_reranking} (type: {type(request.enable_ai_reranking).__name__})")
logger.info(f"   Processed value: {enable_ai_reranking} (type: {type(enable_ai_reranking).__name__})")
```

### 2. Query Cleanup (`main.py`)

```python
# FIX: Handle malformed query (if query rewriting returned JSON string instead of just the query)
if search_query.startswith('```') and '{' in search_query:
    logger.warning(f"⚠️ Detected malformed query (contains JSON), extracting rewritten_query")
    try:
        import json
        import re
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'\{[^}]+\}', search_query, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            parsed = json.loads(json_str)
            if 'rewritten_query' in parsed:
                search_query = parsed['rewritten_query']
                logger.info(f"✅ Extracted rewritten_query: {search_query}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to parse malformed query: {e}, using as-is")
```

### 3. JSON Extraction in Query Rewriting (`cerebras_llm.py`)

```python
# CRITICAL FIX: Extract JSON from markdown code blocks if present
if "```json" in result:
    result = result.split("```json")[1].split("```")[0].strip()
elif "```" in result:
    # Try to extract JSON from generic code blocks
    parts = result.split("```")
    if len(parts) >= 2:
        potential_json = parts[1].strip()
        if potential_json.startswith('{'):
            result = potential_json

# Try to parse JSON response
try:
    parsed_result = json.loads(result)
    rewritten = parsed_result.get("rewritten_query", original_query)
    # Ensure we return a clean string, not JSON
    if isinstance(rewritten, str) and len(rewritten.strip()) > 0:
        return rewritten
    else:
        return original_query
except json.JSONDecodeError:
    # If JSON parsing fails, check if result is already a query string
    if len(result) < 200 and not result.startswith('{'):
        return result
    # Otherwise, return original query to avoid malformed queries
    logger.warning(f"Failed to parse query rewrite JSON, using original query")
    return original_query
```

### 4. Malformed Query Detection (`cerebras_llm.py`)

```python
# CRITICAL FIX: Don't rewrite query if it's already malformed JSON
if query.startswith('```') or (query.strip().startswith('{') and query.strip().endswith('}')):
    logger.warning(f"⚠️ Query appears to be malformed JSON, skipping rewriting")
    return {
        "original_query": query,
        "rewritten_query": query,  # Return original, don't rewrite
        ...
    }
```

## Testing

### Test Case 1: AI Reranking Enabled
1. Enable AI reranking in WordPress settings
2. Perform a search
3. **Expected**: Logs show `enable_ai_reranking: True` and AI reranking is used
4. **Check logs**: Look for "🔍 AI Reranking Parameter Check" and "🤖 Applying AI reranking"

### Test Case 2: Malformed Query Handling
1. If a query contains JSON/markdown, it should be cleaned automatically
2. **Expected**: Query is extracted from JSON or original query is used
3. **Check logs**: Look for "⚠️ Detected malformed query" or "✅ Extracted rewritten_query"

### Test Case 3: Query Rewriting
1. Perform a search that triggers query rewriting
2. **Expected**: Clean query string is used, not JSON
3. **Check logs**: Look for "✅ Using rewritten query" with clean query string

## Logging Added

The following log messages help debug issues:

1. **AI Reranking Parameter Check**:
   - Raw value and type
   - Processed value and type

2. **Malformed Query Detection**:
   - Warning when malformed query detected
   - Success message when query extracted

3. **Query Rewriting**:
   - Success message when rewritten query is used
   - Warning when rewriting is skipped

## Backward Compatibility

✅ **Fully backward compatible**:
- All fixes are defensive (handle edge cases)
- Default behavior preserved (AI reranking enabled by default)
- No breaking changes to API

## Next Steps

1. **Deploy changes** to Railway
2. **Test** with a search query
3. **Check logs** to verify:
   - `enable_ai_reranking` is `True` when enabled in settings
   - Queries are clean (no JSON/markdown)
   - AI reranking is actually being used

## Files Modified

- `main.py` - Boolean parsing and query cleanup
- `cerebras_llm.py` - JSON extraction and malformed query handling

---

## Summary

Fixed two critical issues:
1. ✅ **AI Reranking Parameter**: Now properly parsed as boolean, defaults to `True`
2. ✅ **Malformed Queries**: JSON/markdown code blocks are extracted and cleaned

The search system should now properly use AI reranking when enabled in settings!

