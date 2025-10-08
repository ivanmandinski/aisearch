# Indexing Improvements - All Post Types & Increased Limits

## 🐛 Issues Fixed

### Issue 1: Only 1,000 Posts Indexed
**Problem**: Page limit was set to 20 pages × 50 per page = 1,000 items max  
**Solution**: Increased to 100 pages × 50 per page = **5,000 items per post type**

### Issue 2: Not All Pages Fetched
**Problem**: Same pagination limit affecting pages  
**Solution**: Now fetches up to 5,000 pages

### Issue 3: Custom Post Types Not Indexed
**Problem**: Custom post types were being detected but not fetched correctly  
**Solutions**:
- Now checks for `rest_base` in post type info
- Uses correct REST API endpoint for each custom post type
- Better error handling for 404/401 errors
- Verifies `show_in_rest` is enabled

## ✅ What Was Improved

### 1. Increased Pagination Limits
```python
# Before:
if page > 20:  # Max 1,000 items per type

# After:
if page > 100:  # Max 5,000 items per type
```

### 2. Better Post Type Detection
```python
# Now checks:
- info.get('public', False)  ← Must be public
- info.get('rest_base')      ← Must have REST API endpoint
- info.get('show_in_rest')   ← Must be exposed to REST API
```

### 3. Correct Endpoint Usage
```python
# For custom post types, uses the correct REST base:
rest_base = type_info_map.get(post_type, {}).get('rest_base', post_type)
endpoint = f"{self.base_url}/{rest_base}"

# Examples:
# Post type: 'product'     → Endpoint: /wp-json/wp/v2/products
# Post type: 'portfolio'   → Endpoint: /wp-json/wp/v2/portfolio  
# Post type: 'team-member' → Endpoint: /wp-json/wp/v2/team-members
```

### 4. Enhanced Logging
Now shows:
- Which post types were discovered
- REST base for each post type
- Per-page fetch progress
- Total per post type
- Final breakdown by type
- 404/401 errors with helpful messages

## 📊 New Capacity

| Metric | Before | After |
|--------|--------|-------|
| Posts | 1,000 max | **5,000 max** |
| Pages | 1,000 max | **5,000 max** |
| Custom Types | Not working | **5,000 each** |
| Total Possible | ~2,000 | **100,000+** |

## 🧪 Testing Instructions

### 1. Deploy Updated Code
```bash
cd /Users/ivanm/Desktop/search
git add wordpress_client.py
git commit -m "Fix indexing - support all post types and increase limits to 5000 per type"
git push origin main
```

### 2. Wait for Railway to Deploy
Watch Railway logs for "Application startup complete"

### 3. Run Reindex
Go to WordPress Admin → Hybrid Search → Dashboard → Click "Reindex Content"

### 4. Check Railway Logs

You should see detailed logs like:

```
INFO: Found public post types: ['post', 'page', 'product', 'portfolio', ...]
INFO: Final public post types to index: ['post', 'page', 'product', 'portfolio', ...]

INFO: Starting to fetch 'post' items...
INFO: Fetching 'post' (page 1) from endpoint: https://www.scsengineers.com/wp-json/wp/v2/posts
INFO: Fetched 50 post items (page 1), type total: 50
INFO: Fetching 'post' (page 2) from endpoint: https://www.scsengineers.com/wp-json/wp/v2/posts
INFO: Fetched 50 post items (page 2), type total: 100
...
INFO: Completed fetching 'post': 1,247 items indexed

INFO: Starting to fetch 'page' items...
INFO: Fetching 'page' (page 1) from endpoint: https://www.scsengineers.com/wp-json/wp/v2/pages
INFO: Completed fetching 'page': 89 items indexed

INFO: Starting to fetch 'product' items...
INFO: Fetching 'product' (page 1) from endpoint: https://www.scsengineers.com/wp-json/wp/v2/products
INFO: Completed fetching 'product': 320 items indexed

INFO: Total items from all post types fetched: 1,656
INFO: Breakdown by type: {'post': 1247, 'page': 89, 'product': 320}
```

## 🔍 Troubleshooting Custom Post Types

### If a Custom Post Type Isn't Showing Up:

**1. Check if it's public and in REST API:**
```php
// In your theme/plugin where the post type is registered:
register_post_type('your_custom_type', [
    'public' => true,              // ← Must be true
    'show_in_rest' => true,        // ← Must be true (CRITICAL!)
    'rest_base' => 'your-custom-type', // ← Optional, defaults to post type name
]);
```

**2. Check Railway logs for:**
```
INFO: Including post type: 'your_custom_type' with REST base: 'your-custom-type'
```

**3. If you see:**
```
WARNING: Endpoint not found for 'your_custom_type': /wp-json/wp/v2/your-custom-type
```

This means the post type is NOT exposed to the REST API. You need to add `'show_in_rest' => true` to the post type registration.

**4. Test the REST API endpoint directly:**
```bash
curl https://www.scsengineers.com/wp-json/wp/v2/your-custom-type
```

Should return JSON data, not a 404 error.

## 🎯 Expected Results

After deploying and reindexing:

✅ **All posts indexed** (up to 5,000)
✅ **All pages indexed** (up to 5,000)  
✅ **All custom post types indexed** (5,000 each)
✅ **Detailed logs** showing what was indexed
✅ **Error messages** if any post type fails

## 📝 Summary of Changes

| File | Changes |
|------|---------|
| `wordpress_client.py` | - Increased page limit from 20 to 100<br>- Fixed post type detection to check `rest_base`<br>- Use correct REST endpoints for custom types<br>- Enhanced logging per post type<br>- Better error handling (404, 401)<br>- Final breakdown by type |

## 🚀 Deploy Now

All changes are ready to deploy. After deployment and reindexing, you should see ALL your content indexed, including all custom post types!

