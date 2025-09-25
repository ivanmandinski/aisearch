# Hybrid Search System - Setup Guide

This guide will walk you through setting up the complete hybrid search system for WordPress.

## Prerequisites

Before starting, ensure you have:

- **Python 3.11+** installed
- **Docker** and **Docker Compose** (for local development)
- **WordPress site** with REST API enabled
- **Cerebras API key** (sign up at [Cerebras](https://www.cerebras.net/))
- **Railway account** (for deployment)
- **Git** for version control

## Step 1: Local Development Setup

### 1.1 Clone and Install

```bash
# Clone the repository
git clone <your-repository-url>
cd search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

Required environment variables:

```bash
# Cerebras Configuration (Required)
CEREBRAS_API_KEY=your_cerebras_api_key_here
CEREBRAS_API_BASE=https://api.cerebras.ai/v1
CEREBRAS_MODEL=cerebras-llama-2-7b-chat

# WordPress Configuration (Required)
WORDPRESS_URL=https://your-wordpress-site.com
WORDPRESS_USERNAME=your_wp_username
WORDPRESS_PASSWORD=your_wp_app_password
WORDPRESS_API_URL=https://your-wordpress-site.com/wp-json/wp/v2

# Qdrant Configuration (Optional - defaults provided)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=wordpress_content

# API Configuration (Optional - defaults provided)
API_HOST=0.0.0.0
API_PORT=8000
MAX_SEARCH_RESULTS=10
SEARCH_TIMEOUT=30
EMBEDDING_DIMENSION=1536
```

### 1.3 Run Locally

**Option A: Using Docker (Recommended)**

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Option B: Direct Python**

```bash
# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 1.4 Test the Setup

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test search endpoint
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "limit": 5}'
```

## Step 2: WordPress Plugin Setup

### 2.1 Install Plugin

1. **Upload Plugin Files**
   ```bash
   # Copy plugin to WordPress
   cp -r wordpress-plugin /path/to/wordpress/wp-content/plugins/hybrid-search
   ```

2. **Activate Plugin**
   - Go to WordPress Admin → Plugins
   - Find "Hybrid Search" and click "Activate"

### 2.2 Configure Plugin

1. **Access Settings**
   - Go to Settings → Hybrid Search

2. **Configure API Connection**
   - **API URL**: `http://localhost:8000` (for local development)
   - **API Key**: Leave empty if no authentication required
   - **Max Results**: Set to 10 (or your preference)
   - **Include AI Answer**: Check if you want AI-generated answers

3. **Test Connection**
   - Click "Test API Connection"
   - Should show "✓ API connection successful"

### 2.3 WordPress REST API Setup

1. **Enable REST API**
   - Ensure WordPress REST API is enabled (default in modern WordPress)

2. **Create Application Password**
   - Go to Users → Profile
   - Scroll to "Application Passwords"
   - Create new password for API access
   - Use this password in your `.env` file

## Step 3: Content Indexing

### 3.1 Index WordPress Content

```bash
# Index all WordPress content
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"force_reindex": false}'
```

### 3.2 Verify Indexing

```bash
# Check indexing statistics
curl http://localhost:8000/stats
```

Expected response:
```json
{
  "index_stats": {
    "collection_name": "wordpress_content",
    "total_documents": 150,
    "indexed_vectors": 150,
    "status": "green"
  }
}
```

## Step 4: Test Search Functionality

### 4.1 Test via API

```bash
# Basic search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "limit": 5}'

# Search with AI answer
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to optimize WordPress", "include_answer": true}'

# Filtered search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "tutorials",
    "filters": {
      "type": "post",
      "categories": ["technology"]
    }
  }'
```

### 4.2 Test via WordPress

1. **Visit Search Page**
   - Go to your WordPress site
   - Use the search functionality
   - Should see hybrid search results

2. **Verify Features**
   - Results show relevance scores
   - AI answers appear (if enabled)
   - Filtering works correctly
   - Mobile responsiveness

## Step 5: Railway Deployment

### 5.1 Prepare for Deployment

1. **Create Railway Project**
   - Sign up at [Railway](https://railway.app/)
   - Create new project
   - Connect your GitHub repository

2. **Configure Environment Variables**
   - Add all environment variables from your `.env` file
   - Ensure `CEREBRAS_API_KEY` is set
   - Update `WORDPRESS_API_URL` to your production WordPress

### 5.2 Deploy

1. **Automatic Deployment**
   - Railway will detect the Python project
   - Build and deploy automatically
   - Get your API URL from the deployment

2. **Update WordPress Plugin**
   - Go to Settings → Hybrid Search
   - Update API URL to your Railway deployment URL
   - Test the connection

### 5.3 Production Indexing

```bash
# Index production content
curl -X POST https://your-api.railway.app/index \
  -H "Content-Type: application/json" \
  -d '{"force_reindex": true}'
```

## Step 6: Monitoring and Maintenance

### 6.1 Health Monitoring

```bash
# Check API health
curl https://your-api.railway.app/health

# Check statistics
curl https://your-api.railway.app/stats
```

### 6.2 Regular Maintenance

1. **Reindex Content**
   - Run indexing periodically to include new content
   - Consider automated scheduling

2. **Monitor Performance**
   - Check response times
   - Monitor error rates
   - Review search analytics

3. **Update Dependencies**
   - Keep Python packages updated
   - Monitor security advisories

## Troubleshooting

### Common Issues

**1. API Connection Failed**
```bash
# Check if API is running
curl http://localhost:8000/health

# Check logs
docker-compose logs hybrid-search-api
```

**2. WordPress Plugin Not Working**
- Verify plugin activation
- Check API URL configuration
- Test API connection in plugin settings

**3. Empty Search Results**
```bash
# Check if content is indexed
curl http://localhost:8000/stats

# Reindex if needed
curl -X POST http://localhost:8000/index -d '{"force_reindex": true}'
```

**4. Cerebras API Issues**
- Verify API key is correct
- Check API quota and limits
- Test with simple query

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

### Performance Optimization

1. **Adjust Search Parameters**
   - Reduce `MAX_SEARCH_RESULTS` for faster responses
   - Increase `SEARCH_TIMEOUT` for complex queries

2. **Optimize Embeddings**
   - Consider smaller embedding dimensions
   - Use cached embeddings for common queries

3. **Scale Infrastructure**
   - Use Railway's scaling features
   - Consider CDN for static assets

## Next Steps

Once your hybrid search system is running:

1. **Customize Search Experience**
   - Modify search templates
   - Add custom filters
   - Implement search analytics

2. **Advanced Features**
   - Add search suggestions
   - Implement search history
   - Add advanced filtering options

3. **Integration**
   - Connect with other WordPress plugins
   - Add custom post type support
   - Implement search API for mobile apps

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review API documentation at `/docs` endpoint
3. Check logs for error messages
4. Test individual components separately

The system is designed to be robust and self-healing, but proper monitoring ensures optimal performance.
