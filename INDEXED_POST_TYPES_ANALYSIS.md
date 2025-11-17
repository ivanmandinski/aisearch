# Indexed Post Types Analysis

## Summary

This document provides a comprehensive analysis of which post types are being indexed in the Hybrid Search system.

## Configuration

### WordPress Plugin Settings

**Option Name:** `hybrid_search_index_post_types`  
**Default Value:** `['post', 'page']`  
**Location:** WordPress Admin → Hybrid Search → Settings → "Post Types to Index"

**How it's set:**
- Stored in WordPress database as an array
- Can be configured via admin UI (checkboxes for each public post type)
- Defaults to `['post', 'page']` if not set or empty

**Code Reference:**
```php
// wordpress-plugin/includes/Admin/AdminManager.php:956
$selected_types = get_option('hybrid_search_index_post_types', ['post', 'page']);

// wordpress-plugin/includes/AJAX/AJAXManager.php:1499
$selected_post_types = get_option('hybrid_search_index_post_types', ['post', 'page']);
```

## Indexing Flow

### 1. WordPress Plugin → API Request

When reindexing is triggered from WordPress admin:

**File:** `wordpress-plugin/includes/AJAX/AJAXManager.php:1498-1509`

```php
// Get selected post types from settings
$selected_post_types = get_option('hybrid_search_index_post_types', ['post', 'page']);
if (!is_array($selected_post_types) || empty($selected_post_types)) {
    $selected_post_types = ['post', 'page']; // Default to posts and pages
}

// Send to API
$request_data = [
    'force_reindex' => true,
    'post_types' => $selected_post_types  // ← Post types sent here
];
```

### 2. API Endpoint Receives Request

**File:** `main.py:388-407`

```python
@app.post("/index")
async def index_endpoint(request: IndexRequest, background_tasks: BackgroundTasks):
    # request.post_types contains the selected post types
    # BUT: This endpoint currently just returns "queued" status
    # The actual indexing logic is not implemented here!
```

**⚠️ ISSUE FOUND:** The `/index` endpoint accepts `post_types` but doesn't actually use them. It just returns a "queued" status.

### 3. WordPress Client Fetches Content

**File:** `wordpress_client.py:462-663`

The `fetch_all_post_types()` method:

1. **Discovers all available post types:**
   - Queries WordPress REST API: `GET /wp-json/wp/v2/types`
   - Gets all post types registered in WordPress

2. **Filters by REST API availability:**
   ```python
   # Include if it has a rest_base OR show_in_rest
   if info.get('rest_base') or info.get('show_in_rest'):
       public_types.append(post_type)
   ```

3. **Ensures 'post' and 'page' are always included:**
   ```python
   if 'post' not in public_types:
       public_types.append('post')
   if 'page' not in public_types:
       public_types.append('page')
   ```

4. **Filters by selected_types if provided:**
   ```python
   if selected_types:
       # Only include post types that are in the selected list
       filtered_types = [pt for pt in public_types if pt in selected_types]
       public_types = filtered_types
   ```

5. **If selected_types is None:**
   - Fetches **ALL** public post types with REST API support
   - This could be a problem if not intended!

## Current Behavior

### What Actually Gets Indexed?

Based on the code analysis:

1. **If `selected_types` is passed to `fetch_all_post_types()`:**
   - Only those post types are indexed
   - Must have REST API support (`rest_base` or `show_in_rest`)

2. **If `selected_types` is `None`:**
   - **ALL** public post types with REST API support are indexed
   - This includes any custom post types that are public and have REST API enabled

3. **Always included (fallback):**
   - `post` (even if not in WordPress types API)
   - `page` (even if not in WordPress types API)

### Logging

The code logs detailed information about post types:

```python
# wordpress_client.py:480-493
logger.info(f"Analyzing {len(types_data)} post types from WordPress API...")
for post_type, info in types_data.items():
    logger.info(f"Checking post type '{post_type}': public={info.get('public')}, show_in_rest={info.get('show_in_rest')}, rest_base={info.get('rest_base')}")
    
    if info.get('rest_base') or info.get('show_in_rest'):
        logger.info(f"✅ INCLUDING post type: '{post_type}' with REST base: '{rest_base}'")
    else:
        logger.info(f"⏭️  SKIPPING post type: '{post_type}' (no REST API support)")

# Final list
logger.info(f"✨ FINAL POST TYPES TO INDEX: {public_types}")
```

## Issues Found

### 1. Index Endpoint Doesn't Use post_types

**Location:** `main.py:388-407`

The `/index` endpoint accepts `post_types` in the request but doesn't pass them to the indexing logic. It just returns a "queued" status.

**Impact:** The post types sent from WordPress plugin may not be respected.

### 2. Missing Indexing Implementation

The actual indexing logic that calls `wp_client.get_all_content(selected_types)` is not visible in the `/index` endpoint. It may be:
- Implemented elsewhere (background task?)
- Missing entirely
- Handled by a different system

### 3. Auto-Indexing Uses Different Logic

**File:** `wordpress-plugin/includes/Services/AutoIndexService.php:79`

Auto-indexing checks the same option but only indexes if the post type is in the selected list:

```php
$selected_types = get_option('hybrid_search_index_post_types', ['post', 'page']);
if (!in_array($post->post_type, $selected_types)) {
    return; // Skip this post type
}
```

## Recommendations

### To Check What's Actually Indexed:

1. **Check the logs** when indexing runs:
   - Look for: `"✨ FINAL POST TYPES TO INDEX:"`
   - Look for: `"Breakdown by type:"` (shows counts per type)

2. **Check the WordPress settings:**
   ```php
   $selected = get_option('hybrid_search_index_post_types', ['post', 'page']);
   // This shows what's configured
   ```

3. **Query the search index:**
   - Use `/stats` endpoint to see what's indexed
   - Check Qdrant collection for document types

### To Fix the Issues:

1. **Update `/index` endpoint** to actually use `request.post_types`:
   ```python
   @app.post("/index")
   async def index_endpoint(request: IndexRequest, background_tasks: BackgroundTasks):
       # ... existing code ...
       
       # Actually trigger indexing with selected post types
       if wp_client:
           content = await wp_client.get_all_content(selected_types=request.post_types)
           # Index the content...
   ```

2. **Ensure post_types are always passed** from WordPress plugin to API

3. **Add validation** to ensure only allowed post types are indexed

## Current Default Behavior

**If nothing is configured:**
- Defaults to: `['post', 'page']`
- But if `selected_types=None` is passed to `fetch_all_post_types()`, it will index **ALL** public post types

**If configured in WordPress:**
- Only the selected post types should be indexed
- But this depends on the `/index` endpoint actually using the `post_types` parameter

## Conclusion

The system is designed to index only selected post types, but there's a gap between:
1. What WordPress plugin sends (`post_types` in request)
2. What the API endpoint does with it (currently nothing)
3. What actually gets indexed (depends on how indexing is triggered)

**To determine what's actually indexed, check:**
- Application logs during indexing
- The `/stats` endpoint response
- The Qdrant collection directly



