# Next Steps to Fix Railway Deployment

## Current Situation

✅ **Good News:**
- Collection exists in Qdrant (`status: green`)
- Vector size is correct (`vector_size: 384`)
- Code has collection auto-creation logic
- 1518 documents are in memory (`document_count: 1518`)

❌ **Problem:**
- Documents NOT indexing to Qdrant (`total_documents: 0`, `indexed_vectors: 0`)
- Index operation times out after 2 minutes
- Need to manually reindex

## Why Indexing Fails

The `/index` endpoint is timing out. This could be because:
1. **WordPress API URL** is wrong or restricted
2. **Qdrant upsert** is failing silently
3. **Embedding generation** is too slow
4. **Railway logs** show specific errors we need to check

## How to Fix

### Step 1: Check Railway Logs

Go to Railway dashboard → **Deployments** → **View Logs**

Look for:
- `ERROR: Error upserting documents: ...` (Qdrant write failure)
- `ERROR: Failed to generate embedding for ...` (Embedding generation failure)
- Any collection-related errors

### Step 2: Reindex via WordPress Admin

1. Go to your WordPress site admin
2. **Hybrid Search** → **Settings**
3. Click **"Full Reindex"** or **"Index All Content"**
4. Wait 10-15 minutes (for 1500+ documents with embeddings)
5. Check progress in logs

### Step 3: Check After Reindex

```bash
curl https://aisearch-production-fab7.up.railway.app/stats
```

Expected result:
```json
{
  "index_stats": {
    "total_documents": 1500+,    // ✅ Should be populated
    "indexed_vectors": 1500+,     // ✅ Should be populated
    "status": "green",
    "document_count": 1518
  }
}
```

### Step 4: If Still Failing - Check These

**A. WordPress API Access**
```bash
curl https://www.scsengineers.com/wp-json/wp/v2/posts?per_page=1
```
If this fails, WordPress API might be protected.

**B. Qdrant Connection**
Railway logs should show:
```
INFO: QdrantManager initialized successfully
INFO: Collection 'scs_wp_hybrid' already exists
```

If not, there's a connection issue.

**C. Embedding Service**
Check if `sentence-transformers` is installed:
```python
# In Railway, check logs for:
"INFO: Loading local embedding model (all-MiniLM-L6-v2)..."
```

## Quick Debug Commands

**Check if indexing is working:**
```bash
curl https://aisearch-production-fab7.up.railway.app/stats
```

**Test search (should work with TF-IDF even without vectors):**
```bash
curl -X POST https://aisearch-production-fab7.up.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'
```

**Check health:**
```bash
curl https://aisearch-production-fab7.up.railway.app/health
```

## What to Do Right Now

**Best path:**
1. Go to WordPress admin → Reindex button
2. Watch Railway logs for progress
3. Wait 10-15 minutes
4. Check `/stats` endpoint again

**Alternative:**
Check Railway logs first to see WHY indexing is timing out.

## Expected Timeline

- **50 documents:** ~1-2 minutes
- **500 documents:** ~5-7 minutes  
- **1500+ documents:** ~10-15 minutes (with embeddings)

If it takes longer, something is blocking (WordPress API rate limit, Qdrant connection, embedding generation).

