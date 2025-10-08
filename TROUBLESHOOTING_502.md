# Troubleshooting 502 Error - "Application failed to respond"

## 🐛 Current Issue

Getting 502 error with message: "Application failed to respond" after 15 seconds.

```json
{
  "success": false,
  "error": "Application failed to respond",
  "metadata": {
    "query": "scs",
    "response_time": 15309.92,
    "status_code": 502
  }
}
```

## 🔍 What's Happening

The Railway API is starting but failing to respond to requests. This usually means:
1. ✅ Application deployed successfully
2. ✅ Application is running
3. ❌ Application crashes when handling requests
4. ❌ Or initialization is failing

## 🛠️ What I Fixed

### 1. Added Better Error Handling in `main.py`

**Before**: App would crash if any service failed to initialize
**After**: App starts even if some services fail, with detailed logging

### 2. Made Service Initialization Resilient

Each service (SearchSystem, LLM, WordPress) now initializes independently:
- If one fails, others can still work
- Detailed error logs for each service
- App stays running even with failures

### 3. Improved Search Endpoint Error Handling

- Better error messages
- Graceful fallbacks if LLM fails
- Returns proper JSON error responses

## 📋 How to Check Railway Logs

1. Go to your Railway project dashboard
2. Click on your deployment
3. Click "View Logs" or "Deployments" tab
4. Look for these key messages:

### ✅ Success Messages to Look For:
```
Starting hybrid search service...
Initializing search system...
Search system initialized successfully
Initializing LLM client...
LLM client initialized successfully
Initializing WordPress client...
WordPress client initialized successfully
Hybrid search service startup completed
Application startup complete
```

### ❌ Error Messages to Look For:
```
Failed to initialize search system: [error details]
Failed to initialize LLM client: [error details]
Failed to initialize WordPress client: [error details]
Search system not initialized
Qdrant connection failed
API key invalid
```

## 🔧 Common Issues and Solutions

### Issue 1: Qdrant Connection Failed

**Symptoms**: "Failed to initialize search system"

**Solutions**:
1. Check `QDRANT_URL` environment variable in Railway
2. Check `QDRANT_API_KEY` is correct
3. Verify Qdrant instance is running
4. Test connection: `curl https://your-qdrant-url/collections`

### Issue 2: Cerebras API Key Invalid

**Symptoms**: "LLM connection test failed" or "API key invalid"

**Solutions**:
1. Check `CEREBRAS_API_KEY` in Railway settings
2. Verify key is valid: Test at https://api.cerebras.ai
3. Check `CEREBRAS_API_BASE` is `https://api.cerebras.ai/v1`

### Issue 3: Missing Environment Variables

**Symptoms**: Various initialization errors

**Required Environment Variables**:
```
QDRANT_URL=https://your-qdrant-url
QDRANT_API_KEY=your-key
QDRANT_COLLECTION_NAME=scs_wp_hybrid
CEREBRAS_API_BASE=https://api.cerebras.ai/v1
CEREBRAS_API_KEY=your-key
CEREBRAS_MODEL=llama-3.3-70b
OPENAI_API_KEY=your-key
```

### Issue 4: Index Not Created

**Symptoms**: "Search system initialized" but no results

**Solution**: Run the index endpoint first:
```bash
curl -X POST https://your-app.railway.app/index \
  -H "Content-Type: application/json" \
  -d '{"force_reindex": true}'
```

## 🧪 Testing Steps

### 1. Test Health Endpoint

```bash
curl https://your-app.railway.app/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-08T...",
  "services": {
    "qdrant": "healthy",
    "cerebras_llm": "healthy",
    "wordpress": "initialized"
  }
}
```

### 2. Test Root Endpoint

```bash
curl https://your-app.railway.app/
```

**Expected Response**:
```json
{
  "message": "Hybrid Search API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

### 3. Test Search Endpoint

```bash
curl -X POST https://your-app.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'
```

## 🚀 Deploy the Fixes

```bash
cd /Users/ivanm/Desktop/search
git add main.py cerebras_llm.py requirements.txt
git commit -m "Fix 502 error - improve error handling and service initialization"
git push origin main
```

## 📊 After Deployment

1. **Wait 2-3 minutes** for Railway to rebuild and deploy
2. **Check Logs** immediately after deployment
3. **Test /health** endpoint first
4. **Test /search** endpoint
5. **Check WordPress** search functionality

## 🔍 If Still Getting 502

### Check These in Railway Logs:

1. **Startup Logs**: Did all services initialize?
2. **Request Logs**: What happens when search is called?
3. **Error Logs**: Any Python tracebacks?
4. **Memory/CPU**: Is the app running out of resources?

### Next Debugging Steps:

1. Add more logging to `simple_hybrid_search.py`
2. Check if Qdrant collection exists
3. Verify network connectivity between Railway and Qdrant
4. Test with simpler search query
5. Check Railway memory limits

## 📝 Files Updated

- ✅ `main.py` - Better error handling and startup resilience
- ✅ `cerebras_llm.py` - Fixed AI instructions logic  
- ✅ `requirements.txt` - Compatible dependency versions

---

**Next Step**: Deploy these changes and check Railway logs for detailed error messages!

