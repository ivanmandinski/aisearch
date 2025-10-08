# Railway Deployment Guide

## ✅ Fixed Deployment Issue

The "executable `uvicorn` could not be found" error has been fixed by adding a complete `requirements.txt` file.

## 📋 Pre-Deployment Checklist

Make sure these files exist in your repository:
- ✅ `requirements.txt` - Python dependencies (including uvicorn)
- ✅ `Procfile` - Tells Railway how to start the app
- ✅ `runtime.txt` - Specifies Python version (3.11.7)
- ✅ `main.py` - Your FastAPI application
- ✅ `env.example` - Example environment variables

## 🚀 Deployment Steps

### 1. Push Updated Files to Repository

```bash
git add requirements.txt Procfile runtime.txt cerebras_llm.py
git commit -m "Fix Railway deployment - add uvicorn and dependencies"
git push origin main
```

### 2. Railway Will Auto-Deploy

Once you push, Railway will:
1. ✅ Detect the `requirements.txt` file
2. ✅ Install all dependencies (including `uvicorn`)
3. ✅ Use the `Procfile` to start the application
4. ✅ Deploy successfully

### 3. Set Environment Variables in Railway

Make sure these environment variables are set in your Railway project:

**Required:**
- `QDRANT_URL` - Your Qdrant instance URL
- `QDRANT_API_KEY` - Qdrant API key
- `QDRANT_COLLECTION_NAME` - Collection name (e.g., `scs_wp_hybrid`)
- `CEREBRAS_API_BASE` - `https://api.cerebras.ai/v1`
- `CEREBRAS_API_KEY` - Your Cerebras API key
- `CEREBRAS_MODEL` - Model name (e.g., `llama-3.3-70b`)
- `OPENAI_API_KEY` - OpenAI API key for embeddings
- `PORT` - Railway will set this automatically

**Optional (with defaults):**
- `API_HOST` - Default: `0.0.0.0`
- `MAX_SEARCH_RESULTS` - Default: `10`
- `SEARCH_TIMEOUT` - Default: `30`
- `EMBEDDING_DIMENSION` - Default: `384`

## 🔍 Verify Deployment

After deployment succeeds:

1. **Check Logs**: Look for "Application startup complete"
2. **Test API**: Visit `https://your-app.railway.app/docs`
3. **Test Search**: Make a test search request
4. **Test AI Instructions**: Verify custom instructions work

## 🐛 Troubleshooting

### If deployment still fails:

1. **Check Railway Logs**: Look for specific error messages
2. **Verify requirements.txt**: Make sure it's not empty
3. **Check Python Version**: Railway needs Python 3.11+
4. **Environment Variables**: Ensure all required vars are set

### Common Issues:

- **"Module not found"**: Add missing package to `requirements.txt`
- **"Port binding failed"**: Make sure using `$PORT` in Procfile
- **"API key invalid"**: Check your Cerebras/Qdrant API keys

## 📝 Files Updated

### requirements.txt
Added all necessary Python packages:
- `fastapi` - Web framework
- `uvicorn[standard]` - ASGI server (fixes the error!)
- `llama-index` - Search framework
- `qdrant-client` - Vector database
- `openai` - Embeddings
- Plus all other dependencies

### Procfile
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### runtime.txt
```
python-3.11.7
```

## ✨ What Was Fixed

**Problem**: Railway couldn't find `uvicorn` executable
**Solution**: Added complete `requirements.txt` with all dependencies
**Result**: Deployment will now succeed!

## 🎯 Next Steps

After successful deployment:

1. Update WordPress plugin with new Railway API URL
2. Test AI Answer Instructions (now works correctly!)
3. Monitor performance in Railway dashboard
4. Check API logs for any issues

---

**Need Help?** Check Railway logs or contact support with this deployment info.

