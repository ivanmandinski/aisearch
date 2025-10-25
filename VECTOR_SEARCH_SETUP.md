# Vector Search Setup Guide

**Date:** October 24, 2025  
**Version:** 2.15.2

---

## 🎯 **Current Status**

Your search system has:
- ✅ **TF-IDF Search Working** - 2835 documents indexed
- ✅ **Cerebras LLM Working** - AI reranking enabled
- ❌ **Vector Search NOT Working** - Using zero vectors

---

## 🔍 **Why Vector Search Isn't Working**

### The Problem:
```python
# Line 214 in simple_hybrid_search.py (OLD)
embedding = [0.0] * 384  # ❌ All zeros = meaningless!
```

**Zero vectors** have no semantic meaning, so:
- Qdrant has 0 indexed vectors
- Similarity search returns nothing
- Only TF-IDF (keyword matching) works

---

## ✅ **Solution: Enable Local Embeddings (FREE!)**

I've already updated your code to support **local embeddings**! Just install the package:

### **Step 1: Install sentence-transformers**

```bash
pip install sentence-transformers torch
```

**Or if you're using Docker/Railway:**

Just deploy the updated `requirements.txt` - it now includes:
```
sentence-transformers>=2.2.2
torch>=2.0.0
```

### **Step 2: Reindex Your Content**

After installing, reindex to generate real embeddings:

**Via WordPress Admin:**
1. Go to **Hybrid Search** → **Dashboard**
2. Click **"Reindex Content"**
3. Wait for completion (may take 5-10 minutes for 2835 docs)

**Via API:**
```bash
curl -X POST http://your-api-url.com/index \
  -H "Content-Type: application/json" \
  -d '{"force_reindex": true}'
```

### **Step 3: Verify It's Working**

Check stats again:
```bash
curl http://your-api-url.com/stats
```

**Expected output:**
```json
{
  "total_documents": 2835,      // ✅ Should match
  "indexed_vectors": 2835,      // ✅ Should now have vectors!
  "tfidf_fitted": true,
  "document_count": 2835
}
```

---

## 🚀 **How It Works Now**

### **Automatic Fallback System:**

```python
# 1. Try local embeddings first (FREE!)
if sentence_transformers_available:
    embedding = local_model.encode(text)  # ✅ FREE, FAST, PRIVATE

# 2. Fall back to OpenAI if local fails
elif openai_api_key_configured:
    embedding = openai.embed(text)  # 💰 Costs money

# 3. Fall back to zero vectors if nothing available
else:
    embedding = [0, 0, 0, ...]  # ❌ No vector search
```

### **Your Final Stack:**

| Component | Provider | Cost | Purpose |
|-----------|----------|------|---------|
| **Embeddings** | `sentence-transformers` (local) | FREE | Vector similarity |
| **TF-IDF** | scikit-learn (local) | FREE | Keyword matching |
| **AI Reranking** | Cerebras API | ~$0.15/1K | Intelligent ranking |
| **Answer Gen** | Cerebras API | ~$0.15/1K | AI summaries |
| **Vector DB** | Qdrant Cloud | FREE tier | Storage |

**Total Cost:** ~$0.30 per 1000 searches (just Cerebras LLM!)

---

## 🆚 **Embedding Options Comparison**

### **Option 1: sentence-transformers (Recommended)** ⭐

**Pros:**
- ✅ **FREE** - No API costs
- ✅ **Fast** - No network latency (~50ms/doc)
- ✅ **Private** - Data never leaves your server
- ✅ **384 dimensions** - Perfect for your setup
- ✅ **High quality** - all-MiniLM-L6-v2 is excellent

**Cons:**
- ⚠️ Requires PyTorch (~1GB download)
- ⚠️ Uses CPU/GPU (minimal impact)

**Best for:** Production use, privacy-conscious, cost-effective

---

### **Option 2: OpenAI Embeddings**

**Pros:**
- ✅ Very high quality
- ✅ No local compute needed
- ✅ Latest models

**Cons:**
- ❌ **Costs money** (~$0.10 per 1M tokens)
- ❌ Network latency (~200ms/doc)
- ❌ 1536 dimensions (need to truncate to 384)
- ❌ Data sent to OpenAI

**Best for:** If you already pay for OpenAI

---

### **Option 3: Cerebras** ❌

**Status:** NOT AVAILABLE

Cerebras doesn't offer embedding models, only:
- Chat models (llama-3.3-70b, etc.)
- Text generation
- Reranking via prompting

---

## 🎯 **Recommended Setup**

### **For You (Cost-Effective):**

```bash
# Install local embeddings (one-time setup)
pip install sentence-transformers torch

# Your stack:
# - sentence-transformers: FREE vector embeddings
# - Cerebras: AI reranking + answers (~$0.30/1K searches)
# - Total: Very affordable!
```

### **Model Breakdown:**

| Task | Model | Where | Cost |
|------|-------|-------|------|
| Vector Embeddings | all-MiniLM-L6-v2 | Local | FREE |
| Keyword Search | TF-IDF | Local | FREE |
| AI Reranking | llama-3.3-70b | Cerebras | ~$0.15/1K |
| Answer Generation | llama-3.3-70b | Cerebras | ~$0.15/1K |

---

## 📦 **Installation Commands**

### **Local Development:**
```bash
cd /Users/ivanm/Desktop/aisearch-main
pip install sentence-transformers torch
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### **Docker/Production:**
Your `requirements.txt` is already updated! Just rebuild:
```bash
docker-compose build
# or
railway up
```

### **First-Time Model Download:**
The first time you run indexing, it will download the model (~80MB):
```
Downloading all-MiniLM-L6-v2... ━━━━━━━━━━━━━━ 100% 80MB
✅ Local embedding model loaded successfully!
```

This happens once, then it's cached locally.

---

## 🧪 **Testing Vector Search**

### **After Installing & Reindexing:**

**Test 1: Semantic Search**
```bash
# Search for "environmental consulting"
# Should match "sustainability services", "eco-friendly", etc.
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "environmental consulting", "limit": 5}'
```

**Test 2: Verify Embeddings**
```bash
# Check that vectors are indexed
curl http://localhost:8000/stats
# Should show: "indexed_vectors": 2835 ✅
```

**Test 3: Compare TF-IDF vs Vector**
```bash
# Keyword match (TF-IDF)
curl -X POST http://localhost:8000/search \
  -d '{"query": "exact phrase from content"}'

# Semantic match (Vector)
curl -X POST http://localhost:8000/search \
  -d '{"query": "similar meaning different words"}'
```

---

## ⚡ **Performance Expectations**

### **Indexing (One-Time):**
- **2835 documents** × **50ms/doc** = ~**2-3 minutes**
- Model download: ~1 minute (first time only)
- Total first-time setup: ~**4-5 minutes**

### **Searching (Every Query):**
- TF-IDF: ~10-20ms
- Vector search: ~30-50ms
- AI reranking (Cerebras): ~500-1000ms
- **Total:** ~550-1070ms per search

---

## 🎁 **What You'll Get**

### **Before (Current - TF-IDF Only):**
```
Query: "eco friendly solutions"
Results: Only matches exact words "eco", "friendly", "solutions"
```

### **After (With Vector Search):**
```
Query: "eco friendly solutions"
Results: 
  ✅ "Environmental Sustainability Services" (semantic match!)
  ✅ "Green Energy Consulting" (similar concept!)
  ✅ "Eco-Friendly Solutions" (exact match)
  ✅ "Sustainable Development" (related topic!)
```

**Much better results** with semantic understanding! 🎯

---

## 🔧 **Quick Start**

```bash
# 1. Install package
pip install sentence-transformers

# 2. Restart your API
# (It will auto-download the model on first use)

# 3. Reindex via WordPress
# Hybrid Search → Dashboard → Reindex Content

# 4. Done! Vector search is now enabled ✅
```

---

## ❓ **FAQ**

**Q: Will this slow down my search?**  
A: Slightly (~30-50ms extra), but you get **much better results**.

**Q: How much disk space does it need?**  
A: ~80MB for the model (one-time download).

**Q: Can I use GPU?**  
A: Yes! If GPU is available, it will automatically use it (faster).

**Q: Does it work with Cerebras?**  
A: Yes! Local embeddings + Cerebras LLM = perfect combo!

**Q: What if I don't want to install sentence-transformers?**  
A: Your search will work but only with TF-IDF (keyword matching). Good enough for many use cases!

---

## 🎯 **Bottom Line**

**Use sentence-transformers locally!** It's:
- ✅ Free
- ✅ Fast enough
- ✅ Private
- ✅ Perfect for your 384-dimension setup
- ✅ Works great with Cerebras for AI features

**Cerebras is not for embeddings** - it's for LLM intelligence, which you're already using perfectly for reranking and answers!

---

Want me to help you install it and test it? 🚀

