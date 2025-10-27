# How to Deploy Qdrant Fixes to Railway

## The Problem
Railway is running old code. Your local fixes are NOT deployed yet.

## Quick Fix: Option 1 - Upload Files Manually

I've created `qdrant-fixes.tar.gz` with the fixed files. 

**Steps:**
1. Go to Railway dashboard: https://railway.app/
2. Open your project: `aisearch-production-fab7`
3. Go to **Settings** > **Service**
4. Scroll to **"Deploy from GitHub"** or find **"Upload Files"**
5. Upload `qdrant-fixes.tar.gz`
6. Extract files and replace:
   - `qdrant_manager.py` 
   - `simple_hybrid_search.py`
7. Railway will auto-redeploy
8. Wait 2-3 minutes, then reindex

## Quick Fix: Option 2 - Add Git Remote and Push

If Railway has GitHub integration:

```bash
# Find your Railway GitHub repo URL
# It's probably something like: git@github.com:USERNAME/REPO.git

# Add remote
git remote add railway <YOUR_GITHUB_REPO_URL>

# Push all commits
git push railway main

# Wait for Railway to auto-deploy
```

## Quick Fix: Option 3 - Copy-Paste Code Changes

If upload doesn't work, manually edit in Railway dashboard:

### Fix 1: qdrant_manager.py (lines 223-285)
Replace the `get_collection_info` method with:
```python
def get_collection_info(self) -> Dict[str, Any]:
    """Get information about the collection."""
    try:
        collection_info = self.client.get_collection(self.collection_name)
        # Access vectors config properly - it's either a dict or a VectorParams object
        try:
            if hasattr(collection_info.config.params.vectors, 'size'):
                # It's a VectorParams object
                vector_size = collection_info.config.params.vectors.size
            elif isinstance(collection_info.config.params.vectors, dict):
                # It's a dict with "dense" key
                vector_size = collection_info.config.params.vectors.get("dense", {}).get("size", 0)
            else:
                vector_size = 0
        except:
            vector_size = 0
        
        return {
            "name": self.collection_name,
            "vector_size": vector_size,
            "vectors_count": collection_info.vectors_count,
            "indexed_vectors_count": collection_info.indexed_vectors_count,
            "points_count": collection_info.points_count,
            "segments_count": collection_info.segments_count,
            "status": collection_info.status
        }
    except Exception as e:
        logger.error(f"Error getting collection info: {e}")
        # Auto-create collection if missing
        logger.info(f"Collection '{self.collection_name}' doesn't exist, attempting to create it...")
        try:
            if self.create_collection():
                logger.info(f"✅ Successfully created collection '{self.collection_name}'")
                # Try getting info again
                try:
                    collection_info = self.client.get_collection(self.collection_name)
                    # Use same logic as above for vector_size
                    try:
                        if hasattr(collection_info.config.params.vectors, 'size'):
                            vector_size = collection_info.config.params.vectors.size
                        elif isinstance(collection_info.config.params.vectors, dict):
                            vector_size = collection_info.config.params.vectors.get("dense", {}).get("size", 0)
                        else:
                            vector_size = 0
                    except:
                        vector_size = 0
                    
                    return {
                        "name": self.collection_name,
                        "vector_size": vector_size,
                        "vectors_count": collection_info.vectors_count,
                        "indexed_vectors_count": collection_info.indexed_vectors_count,
                        "points_count": collection_info.points_count,
                        "segments_count": collection_info.segments_count,
                        "status": collection_info.status
                    }
                except Exception as retry_e:
                    logger.error(f"Error getting collection info after creation: {retry_e}")
                    return {}
            else:
                logger.error(f"Failed to create collection '{self.collection_name}'")
                return {}
        except Exception as create_e:
            logger.error(f"Error during auto-creation: {create_e}")
            return {}
```

### Fix 2: simple_hybrid_search.py (around line 303-316)
Replace the Qdrant indexing section with:
```python
# Store in Qdrant for hybrid search (if available)
try:
    if self.qdrant_manager:
        # Create collection first if it doesn't exist
        logger.info("Ensuring Qdrant collection exists...")
        self.qdrant_manager.create_collection()
        
        # Upsert documents to Qdrant (converts to proper format internally)
        self.qdrant_manager.upsert_documents(processed_docs)
        logger.info(f"Successfully indexed {len(processed_docs)} documents in Qdrant")
    else:
        logger.warning("Qdrant not available - skipping vector storage")
except Exception as e:
    logger.warning(f"Could not index to Qdrant (using TF-IDF only): {e}")
```

## After Deploying

1. Check API health: `curl https://aisearch-production-fab7.up.railway.app/health`
2. Trigger reindex via WordPress admin or:
   ```bash
   curl -X POST https://aisearch-production-fab7.up.railway.app/index \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.scsengineers.com", "post_types": ["post", "page"]}'
   ```
3. Check stats: `curl https://aisearch-production-fab7.up.railway.app/stats`
4. You should see `total_documents > 0` and `indexed_vectors > 0`

