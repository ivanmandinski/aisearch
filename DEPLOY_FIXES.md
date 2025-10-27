# Deploy Qdrant Collection Fixes

## Status
✅ **Fixes are ready but NOT deployed to Railway yet**

## What Was Fixed

### 1. VectorParams Access Error (qdrant_manager.py)
- **Problem**: Trying to access `vectors["dense"].size` on a VectorParams object
- **Fix**: Use proper attribute access with fallback handling
- **Lines**: 228-278

### 2. Collection Not Created (simple_hybrid_search.py)  
- **Problem**: Creating new QdrantManager instances instead of using existing one
- **Fix**: Use `self.qdrant_manager.create_collection()` before indexing
- **Lines**: 303-316

### 3. Commits Ready
- `77d1efd` - Use existing qdrant_manager instance
- `408c3b6` - Complete VectorParams fix
- `f98ad39` - Initial VectorParams fix

## How to Deploy

Since Railway uses Git, you need to push these commits:

```bash
# Check your Railway deployment method
# If using Git integration:
git remote add origin YOUR_GITHUB_REPO_URL  # If not already set
git push origin main

# OR if Railway pulls from a specific branch:
git push origin main:YOUR_RAILWAY_BRANCH
```

## After Deployment

1. **Check API is up**: `curl https://aisearch-production-fab7.up.railway.app/health`
2. **Reindex**: Send POST to `/index` endpoint
3. **Verify**: Check `/stats` endpoint for `total_documents > 0`

## Expected Results After Deploy

```json
{
  "index_stats": {
    "collection_name": "scs_wp_hybrid",
    "total_documents": 2000+,    // ✅ Should be populated
    "indexed_vectors": 2000+,     // ✅ Should be populated
    "status": "green",
    "tfidf_fitted": true,
    "document_count": 2835
  }
}
```

## Current Status (Before Deploy)

```json
{
  "index_stats": {
    "collection_name": "scs_wp_hybrid",
    "total_documents": 0,        // ❌ No vectors in Qdrant
    "indexed_vectors": 0,        // ❌ No vectors in Qdrant
    "status": "green",           // ✅ Collection exists
    "tfidf_fitted": true,
    "document_count": 2835       // ✅ Documents in memory only
  }
}
```

## Next Steps

1. Push commits to Railway (via Git or manual upload)
2. Wait for Railway to deploy
3. Reindex content via WordPress admin or `/index` endpoint
4. Verify vector search is working

