# WordPress Plugin Troubleshooting Guide

## 🔧 **Fixed Issues in the Plugin**

### **1. Missing AJAX Nonce**
- **Problem**: Security nonce was not being generated
- **Fix**: Added `wp_create_nonce('hybrid_search_nonce')` to script localization

### **2. Missing API Test Handler**
- **Problem**: No AJAX handler for testing API connection
- **Fix**: Added `handle_test_api()` method and AJAX action

### **3. Improved Error Handling**
- **Problem**: Generic error messages
- **Fix**: Added detailed error logging and better error messages

## 🧪 **Testing Steps**

### **Step 1: Update Plugin Files**
Upload the updated plugin files to your WordPress site:

```bash
# Upload updated plugin
scp -r wordpress-plugin/ user@scsengineers.com:/path/to/wp-content/plugins/scs-hybrid-search/
```

### **Step 2: Configure Plugin Settings**
1. Go to **WordPress Admin → Settings → SCS Hybrid Search**
2. Set **API URL**: `https://test-production-8297.up.railway.app`
3. Leave **API Key** empty (not required)
4. Set **Max Results**: `10`
5. Check **Include AI Answer** if desired
6. Click **Test API Connection**

### **Step 3: Check Browser Console**
Open browser developer tools (F12) and check the console for:
- Configuration logs
- AJAX request details
- Error messages

### **Step 4: Test Search**
1. Visit your WordPress search page
2. Enter a search query
3. Check console for any errors
4. Verify results display correctly

## 🐛 **Common Issues & Solutions**

### **Issue 1: "API connection failed: undefined"**
**Causes:**
- API URL not configured
- SSL certificate issues
- Network connectivity problems

**Solutions:**
```bash
# Test API directly
curl https://test-production-8297.up.railway.app/health

# Check WordPress SSL settings
# In wp-config.php, add:
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
```

### **Issue 2: "Network error"**
**Causes:**
- CORS issues
- AJAX nonce problems
- Plugin not properly activated

**Solutions:**
1. **Check Plugin Activation:**
   - Go to Plugins → Installed Plugins
   - Ensure "SCS Engineers Hybrid Search" is activated

2. **Check AJAX URL:**
   - Verify `hybridSearch.ajaxUrl` in browser console
   - Should be: `https://yoursite.com/wp-admin/admin-ajax.php`

3. **Check Nonce:**
   - Verify `hybridSearch.nonce` exists in browser console
   - Should be a long string of characters

### **Issue 3: "Search failed"**
**Causes:**
- API not responding
- Content not indexed
- Invalid search parameters

**Solutions:**
1. **Test API directly:**
   ```bash
   curl -X POST https://test-production-8297.up.railway.app/search \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "limit": 5}'
   ```

2. **Index content:**
   ```bash
   curl -X POST https://test-production-8297.up.railway.app/index \
     -H "Content-Type: application/json" \
     -d '{"force_reindex": true}'
   ```

## 🔍 **Debug Information**

### **Browser Console Logs**
Look for these messages:
```
Hybrid Search initialized with config: {
  ajaxUrl: "https://yoursite.com/wp-admin/admin-ajax.php",
  apiUrl: "https://test-production-8297.up.railway.app",
  maxResults: 10,
  includeAnswer: false,
  hasNonce: true
}
```

### **Network Tab**
Check the Network tab for:
- AJAX requests to `admin-ajax.php`
- Response status codes
- Response content

### **WordPress Debug Log**
Check `/wp-content/debug.log` for PHP errors:
```bash
tail -f /path/to/wp-content/debug.log
```

## 🚀 **Quick Fixes**

### **Fix 1: Clear Cache**
```bash
# Clear WordPress cache
wp cache flush

# Clear browser cache
Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
```

### **Fix 2: Re-activate Plugin**
1. Deactivate "SCS Engineers Hybrid Search"
2. Reactivate the plugin
3. Test again

### **Fix 3: Check File Permissions**
```bash
# Ensure plugin files are readable
chmod -R 755 /path/to/wp-content/plugins/scs-hybrid-search/
```

## 📞 **Support**

If issues persist:
1. Check Railway deployment logs
2. Verify API is responding: https://test-production-8297.up.railway.app/health
3. Test API endpoints directly
4. Check WordPress error logs
5. Verify plugin configuration

## ✅ **Success Indicators**

When working correctly, you should see:
- ✅ API connection test passes
- ✅ Search results display with relevance scores
- ✅ No console errors
- ✅ AJAX requests return 200 status
- ✅ Results link to correct WordPress pages


