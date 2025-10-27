# WordPress Plugin Showing 0 Results - Troubleshooting Guide

## Problem
Search from WordPress plugin returns 0 results, but API is working correctly.

## Root Cause
The WordPress plugin is likely not configured correctly or hitting an error.

## Quick Checks

### 1. Verify API URL Configuration
Go to WordPress Admin → Settings → Hybrid Search

Check that:
- API URL is set to: `https://aisearch-production-fab7.up.railway.app`
- No trailing slash
- Save the settings

### 2. Check WordPress Debug Log
Enable WordPress debug logging:
```php
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
define('WP_DEBUG_DISPLAY', false);
```

Then search from WordPress and check `wp-content/debug.log` for:
- `Hybrid Search: Request data being sent to Railway API: ...`
- Any error messages

### 3. Test API Connection
Open WordPress admin → Search for "Hybrid Search Diagnostics"

Or run manually:
```bash
curl -X GET https://aisearch-production-fab7.up.railway.app/health
```

### 4. Check Plugin Logs
Look for these in error logs:
```
Hybrid Search: Request data being sent to Railway API
Hybrid Search: API response received
Hybrid Search: Search completed successfully
```

## Common Issues

### Issue 1: API URL Not Set
**Symptom:** No API URL in settings
**Fix:** Enter `https://aisearch-production-fab7.up.railway.app` in WordPress settings

### Issue 2: SSL Verification Failing  
**Symptom:** Connection error or SSL error
**Fix:** Check if Railway SSL certificate is valid

### Issue 3: Timeout Issues
**Symptom:** Request times out after 30 seconds
**Fix:** The timeout was increased to 30 minutes for indexing, should be fine for search

### Issue 4: Response Format Mismatch
**Symptom:** Results array is empty but response code is 200
**Fix:** Check if API response structure matches plugin expectations

## Code Changes Made

### What I Changed:
1. Added `generate_content_based_alternative_queries()` method in `simple_hybrid_search.py`
2. Updated `main.py` to generate content-based alternatives after search
3. Fixed `get_stats()` to use `vectors_count` instead of `indexed_vectors_count`
4. Fixed Qdrant point ID format (string → integer)

### Commits Ready to Deploy:
- `9916cbf` - Vector stats fix
- `c069263` - Content-based alternatives
- `5ba664c` - Integer IDs
- `77d1efd` - Use existing qdrant_manager
- `408c3b6` - VectorParams fix

## Next Steps

1. **Deploy the code changes** to Railway (upload files or push to GitHub)
2. **Check WordPress settings** - ensure API URL is correct
3. **Enable debug logging** in WordPress
4. **Test search** and check logs
5. **Check for errors** in Railway logs via Railway dashboard

## Verify Fix Works

After deploying, check stats:
```bash
curl https://aisearch-production-fab7.up.railway.app/stats
```

Should show:
```json
{
  "indexed_vectors": 2836  // ✅ Should be > 0 now!
}
```

