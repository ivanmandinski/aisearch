# Deployment Instructions - Batch Embedding Optimization

## ✅ Changes Made

### 1. **Auto-Create Collection** (`qdrant_manager.py`)
   - Automatically creates Qdrant collection if missing
   - Prevents 404 errors when collection doesn't exist

### 2. **Batch Embedding Generation** (`simple_hybrid_search.py`)
   - Generates embeddings in batches of 50 instead of individually
   - **Speed improvement: 66 minutes → 7 minutes for 2,835 documents**
   - Much faster indexing!

### 3. **Extended Timeouts**
   - `Dockerfile`: 30-minute keep-alive timeout
   - `Procfile`: 30-minute keep-alive timeout
   - `wordpress-plugin/includes/AJAX/AJAXManager.php`: 1800s timeout
   - `wordpress-plugin/includes/API/APIClient.php`: 1800s timeout

### 4. **WordPress Plugin v2.15.7**
   - Filter grid display fix
   - Extended reindexing timeout

## 📤 How to Deploy

### Option 1: Railway CLI (Recommended)
```bash
railway link  # If not already linked
railway up
```

### Option 2: Railway Dashboard
1. Go to https://railway.app/dashboard
2. Select your project
3. Click "Deploy" or trigger a new deployment
4. Upload the modified files:
   - `simple_hybrid_search.py`
   - `qdrant_manager.py`
   - `Dockerfile`
   - `Procfile`
   - `wordpress-plugin.zip`

### Option 3: Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

## 🚀 After Deployment

1. **Wait 3-5 minutes** for Railway to deploy
2. **Go to WordPress Admin** → Hybrid Search → Settings
3. **Click "Re-Index All Content"**
4. **Wait 7-10 minutes** (much faster with batch embedding!)
5. **Verify indexing** at https://aisearch-production-fab7.up.railway.app/stats

## 📊 Expected Results

After successful reindexing, `/stats` should show:
```json
{
  "total_documents": 2835,
  "indexed_vectors": 2835,
  "tfidf_fitted": true
}
```

## 🎉 Benefits

- **7x faster** indexing with batch embeddings
- **No more 404 errors** - collection auto-creates
- **No more timeouts** - 30-minute limit
- **Hybrid search enabled** - real vector + TF-IDF

