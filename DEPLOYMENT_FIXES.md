# Critical Deployment Fixes for Railway

## 🚨 Issue Summary

**Problem**: Getting 502 "Application failed to respond" error  
**Root Cause**: Import error in `qdrant_manager.py` - trying to import non-existent `Query` class  
**Impact**: App crashes before it can even start

## ✅ All Fixes Applied

### 1. **qdrant_manager.py** - CRITICAL FIX
**Problem**: `ImportError: cannot import name 'Query'`
```python
# Before (BROKEN):
from qdrant_client.models import Query  # ← Doesn't exist in qdrant-client 1.7.0!

# After (FIXED):
# Removed Query from imports - it wasn't being used anyway
```

### 2. **simple_hybrid_search.py** - Import Safety
**Problem**: Crash if QdrantManager or CerebrasLLM import fails
```python
# Before (BROKEN):
from qdrant_manager import QdrantManager  # ← If this fails, app crashes

# After (FIXED):
try:
    from qdrant_manager import QdrantManager
    QDRANT_AVAILABLE = True
except ImportError as e:
    logging.error(f"Failed to import QdrantManager: {e}")
    QdrantManager = None
    QDRANT_AVAILABLE = False
```

### 3. **main.py** - Graceful Startup
**Problem**: App crashes if any service fails to initialize
```python
# Before (BROKEN):
search_system = SimpleHybridSearch()  # ← If this fails, app dies

# After (FIXED):
if SimpleHybridSearch is not None:
    try:
        search_system = SimpleHybridSearch()
    except Exception as e:
        logger.error(f"Failed: {e}")
        # App continues running!
```

### 4. **cerebras_llm.py** - AI Instructions
**Problem**: Custom AI instructions were ignored
```python
# Before (BROKEN):
Custom Instructions: give 5 words
+ Default: write 2-3 paragraphs  # ← Overrides custom instructions

# After (FIXED):
if custom_instr:
    # ONLY use custom instructions, no defaults to override them
```

### 5. **requirements.txt** - Compatible Versions
**Problem**: Trying to install non-existent package versions
```txt
Before (BROKEN):
llama-index-core==0.9.14  # ← Doesn't exist!

After (FIXED):
llama-index==0.10.43  # ← Compatible version
llama-index-core==0.10.43
```

## 🚀 Deploy All Fixes

```bash
cd /Users/ivanm/Desktop/search

# Add all fixed files
git add qdrant_manager.py \
        simple_hybrid_search.py \
        main.py \
        cerebras_llm.py \
        requirements.txt \
        Procfile \
        runtime.txt

# Commit
git commit -m "Fix all deployment errors - remove invalid imports and add fault tolerance"

# Push to Railway
git push origin main
```

## 📋 Files Fixed

| File | Issue | Fix |
|------|-------|-----|
| `qdrant_manager.py` | ❌ ImportError: Query doesn't exist | ✅ Removed Query import |
| `simple_hybrid_search.py` | ❌ Crashes on import failure | ✅ Safe imports with try-catch |
| `main.py` | ❌ Crashes if services fail | ✅ Graceful initialization |
| `cerebras_llm.py` | ❌ AI instructions ignored | ✅ Custom instructions prioritized |
| `requirements.txt` | ❌ Invalid package versions | ✅ Compatible versions |

## 🎯 Expected Behavior After Deploy

### ✅ Success Case (All Services Work):
```
Starting hybrid search service...
Initializing search system...
Initializing QdrantManager...
QdrantManager initialized successfully
Initializing CerebrasLLM...
CerebrasLLM initialized successfully
Search system initialized successfully
Application startup complete
```

### ⚠️ Partial Success (Some Services Fail):
```
Starting hybrid search service...
Failed to import QdrantManager: [error]
Qdrant not available - using fallback search only
Initialized with 3 sample documents
Search system initialized successfully
Application startup complete  ← App still works!
```

## 🧪 Testing After Deployment

### 1. Wait for Deployment (2-3 minutes)

### 2. Check Railway Logs
Look for "Application startup complete" - this means app is running!

### 3. Test Health Endpoint
```bash
curl https://your-app.railway.app/health
```

Should return:
```json
{
  "status": "healthy" or "degraded",
  "services": {
    "qdrant": "healthy" or "not_initialized",
    "cerebras_llm": "healthy" or "unhealthy",
    "wordpress": "initialized"
  }
}
```

### 4. Test Search Endpoint
```bash
curl -X POST https://your-app.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "scs", "limit": 5}'
```

Should return results (even if from sample data)!

### 5. Test from WordPress
Go to `https://wtd.bg/?s=scs` and search should work!

## 🔍 If Still Issues

### Check Railway Logs for These Patterns:

**Good Signs:**
- ✅ "Application startup complete"
- ✅ "Search system initialized"
- ✅ "Initialized with 3 sample documents"

**Bad Signs:**
- ❌ "Traceback" or "Exception"
- ❌ "ImportError"
- ❌ "Connection refused"

### Specific Errors:

**If you see "Failed to import QdrantManager":**
- Check qdrant-client version in requirements.txt
- Check Railway logs for the specific import error
- App should still work with fallback search

**If you see "Qdrant connection failed":**
- Verify QDRANT_URL in Railway settings
- Verify QDRANT_API_KEY is correct
- Test Qdrant instance directly

**If you see "Cerebras API error":**
- Verify CEREBRAS_API_KEY in Railway settings
- Check if API key is valid
- Search will work, but no AI answers

## 📊 Performance Expectations

- **With full services**: 300-1000ms response time
- **With fallback**: 50-200ms response time  
- **Sample data**: 3 documents for testing
- **Real data**: After running /index endpoint

## ✨ Summary

All critical fixes applied:
1. ✅ Removed invalid `Query` import
2. ✅ Made all imports safe with try-catch
3. ✅ Added graceful degradation
4. ✅ Fixed AI instructions logic
5. ✅ Compatible dependency versions

**The app should now start and handle requests successfully!** 🚀

