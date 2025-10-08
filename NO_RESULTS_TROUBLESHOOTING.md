# WordPress Plugin "No Results Found" - Troubleshooting Guide

## 🔍 **Root Cause Analysis**

The "No results found" issue is caused by an **empty search index**. The API is working, but no content has been indexed yet.

### **Current Status:**
- ✅ API is healthy and responding
- ✅ WordPress REST API is accessible
- ❌ Search index is empty (0 documents)
- ❌ Indexing is failing due to missing OpenAI API key

## 🚨 **Critical Issue: Missing OpenAI API Key**

The indexing process requires an OpenAI API key for generating embeddings, but it's not configured.

### **Error Details:**
```json
{
  "error": "Indexing failed: ",
  "status_code": 500,
  "timestamp": "2025-09-29T11:43:03.977844"
}
```

## 🔧 **Solution Steps**

### **Step 1: Get OpenAI API Key**
1. Go to [OpenAI Platform](https://platform.openai.com/account/api-keys)
2. Create a new API key
3. Copy the key (starts with `sk-`)

### **Step 2: Update Railway Environment Variables**
1. Go to your Railway project dashboard
2. Navigate to **Variables** tab
3. Add new environment variable:
   - **Name**: `OPENAI_API_KEY`
   - **Value**: `sk-your-actual-openai-api-key-here`

### **Step 3: Redeploy the Application**
1. Railway will automatically redeploy when you add the environment variable
2. Wait for deployment to complete

### **Step 4: Index Content**
```bash
# Test the indexing endpoint
curl -X POST https://test-production-8297.up.railway.app/index \
  -H "Content-Type: application/json" \
  -d '{"force_reindex": true}'
```

### **Step 5: Verify Indexing**
```bash
# Check if content was indexed
curl -s https://test-production-8297.up.railway.app/stats | jq .
```

Expected result:
```json
{
  "index_stats": {
    "total_documents": 100,  // Should be > 0
    "indexed_vectors": 100,
    "status": "green"
  }
}
```

### **Step 6: Test Search**
```bash
# Test search functionality
curl -X POST https://test-production-8297.up.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "energy", "limit": 5}'
```

## 🧪 **Alternative Testing Methods**

### **Method 1: Direct API Test**
```bash
# Test search with AI answer
curl -X POST https://test-production-8297.up.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "energy audit", "limit": 3, "include_answer": true}'
```

### **Method 2: WordPress Plugin Test**
1. Update plugin files on your WordPress site
2. Configure plugin settings:
   - API URL: `https://test-production-8297.up.railway.app`
   - Test API connection
3. Try searching on your WordPress site

## 🔍 **Debugging Commands**

### **Check API Health**
```bash
curl -s https://test-production-8297.up.railway.app/health | jq .
```

### **Check Index Status**
```bash
curl -s https://test-production-8297.up.railway.app/stats | jq .
```

### **Test WordPress Content Fetch**
```bash
# Test if WordPress content can be fetched
curl -s "https://www.scsengineers.com/wp-json/wp/v2/posts?per_page=1" | jq '.[0].title'
```

## 📋 **Expected Results After Fix**

### **1. Indexing Success**
```json
{
  "success": true,
  "message": "Successfully indexed 150 documents",
  "documents_indexed": 150,
  "processing_time": 45.2
}
```

### **2. Search Results**
```json
{
  "query": "energy audit",
  "results": [
    {
      "id": "514555",
      "title": "Managing Rising Energy Costs Using an Energy Audit",
      "url": "https://www.scsengineers.com/managing-rising-energy-costs-using-an-energy-audit/",
      "score": 0.85,
      "relevance": "high"
    }
  ],
  "total_results": 1,
  "processing_time": 0.5
}
```

### **3. WordPress Plugin**
- ✅ Search results display correctly
- ✅ No "No results found" message
- ✅ Relevance scores shown
- ✅ Links work properly

## 🚀 **Quick Fix Summary**

1. **Get OpenAI API key** from platform.openai.com
2. **Add to Railway**: `OPENAI_API_KEY=sk-your-key`
3. **Wait for redeploy** (automatic)
4. **Index content**: `POST /index` with `force_reindex=true`
5. **Test search**: Try queries like "energy", "audit", "engineering"

## 📞 **If Issues Persist**

1. Check Railway deployment logs
2. Verify OpenAI API key is valid
3. Test embedding generation manually
4. Check Qdrant connection
5. Verify WordPress content is accessible

The core issue is the missing OpenAI API key for embeddings. Once added, the system should work perfectly!


