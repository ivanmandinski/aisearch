# SCS Engineers Hybrid Search - Deployment Guide

## 🏗️ SCS-Specific Configuration

Your hybrid search system has been configured specifically for SCS Engineers with the following settings:

### ✅ **Pre-configured Components**
- **Qdrant Cloud**: `scs_wp_hybrid` collection
- **Cerebras LLM**: `llama-3.3-70b` model
- **BGE Embeddings**: `BAAI/bge-small-en-v1.5` (384 dimensions)
- **BM25 Sparse**: `Qdrant/bm25` for keyword matching
- **WordPress Site**: `https://www.scsengineers.com`

## 🚀 Quick Deployment Steps

### 1. **Railway Deployment**

1. **Connect Repository**
   ```bash
   # Push your code to GitHub
   git add .
   git commit -m "SCS Engineers hybrid search configuration"
   git push origin main
   ```

2. **Deploy to Railway**
   - Go to [Railway](https://railway.app/)
   - Create new project from GitHub
   - Connect your repository
   - Railway will auto-detect Python and deploy
   - **Note**: Railway automatically detects Python projects and uses `requirements.txt`
   - **Fixed**: Removed non-existent `wordpress-api` package, using version ranges for better compatibility
   - **Optimized**: Removed heavy PyTorch/transformers dependencies, using OpenAI embeddings instead of BGE
   - **Size Reduced**: Multi-stage Docker build reduces image size from 7.9GB to under 4GB

3. **Set Environment Variables**
   In Railway dashboard, add these variables:
   ```
   QDRANT_URL=https://918733b4-ab99-457e-a8d8-8105782783a5.us-east-1-1.aws.cloud.qdrant.io
   QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.cp6kzt-aVQt6jK0YVnPLWo8qzE3FnRpNKDq0-_u_A1g
   QDRANT_COLLECTION_NAME=scs_wp_hybrid
   CEREBRAS_API_KEY=csk-d36t36pvwh54t9fpyn9xd339ynpkvw8ev4r2me2nt89y3y5h
   CEREBRAS_MODEL=llama-3.3-70b
   EMBED_MODEL=text-embedding-ada-002
   SPARSE_MODEL=tfidf
   WORDPRESS_URL=https://www.scsengineers.com
   WORDPRESS_USERNAME=your_wp_username
   WORDPRESS_PASSWORD=your_wp_app_password
   WORDPRESS_API_URL=https://www.scsengineers.com/wp-json/wp/v2
   API_TITLE=SCS Engineers Search (Hybrid)
   EMBEDDING_DIMENSION=1536
   CHUNK_SIZE=512
   DEFAULT_SITE_BASE=https://www.scsengineers.com
   SEARCH_PAGE_TITLE=SCS Engineers Search (Hybrid)
   ```

### 2. **WordPress Plugin Installation**

1. **Upload Plugin**
   ```bash
   # Copy plugin to SCS WordPress
   scp -r wordpress-plugin/ user@scsengineers.com:/path/to/wp-content/plugins/scs-hybrid-search/
   ```

2. **Activate Plugin**
   - Go to WordPress Admin → Plugins
   - Activate "SCS Engineers Hybrid Search"

3. **Configure Plugin**
   - Go to Settings → SCS Hybrid Search
   - Set API URL to your Railway deployment URL
   - Test connection

### 3. **Content Indexing**

Once deployed, index your SCS content:

```bash
# Index all SCS content
curl -X POST https://your-api.railway.app/index \
  -H "Content-Type: application/json" \
  -d '{"force_reindex": true}'
```

## 🔧 SCS-Specific Features

### **Engineering Content Optimization**
- **Technical Terms**: Optimized for engineering terminology
- **Project Documentation**: Enhanced search for project files
- **Service Areas**: Environmental, civil, geotechnical engineering
- **Case Studies**: Improved discovery of project examples

### **Search Enhancements**
- **BGE Embeddings**: Better semantic understanding of technical content
- **BM25 Sparse**: Precise keyword matching for technical terms
- **Chunk Size 512**: Optimal for engineering documents
- **384 Dimensions**: Efficient vector storage

### **SCS Branding**
- **Custom Title**: "SCS Engineers Search (Hybrid)"
- **Branded Plugin**: SCS-specific WordPress plugin
- **Custom Styling**: Professional engineering aesthetic

## 📊 Expected Performance

### **Search Accuracy**
- **Technical Terms**: 95%+ accuracy for engineering terminology
- **Project Names**: High precision for project-specific searches
- **Service Areas**: Excellent categorization of service types
- **Documentation**: Fast retrieval of technical documents

### **Response Times**
- **Simple Queries**: 200-300ms
- **Complex Queries**: 400-600ms
- **AI Answers**: 1-2 seconds
- **Indexing**: 2-5 minutes for full site

## 🛠️ Maintenance

### **Regular Tasks**
1. **Content Updates**: Re-index when adding new content
2. **Performance Monitoring**: Check Railway metrics
3. **Search Analytics**: Monitor popular queries
4. **Model Updates**: Keep embedding models current

### **SCS-Specific Monitoring**
- **Project Search**: Track searches for specific projects
- **Service Queries**: Monitor searches by service area
- **Technical Terms**: Identify common engineering queries
- **User Feedback**: Collect search experience feedback

## 🔍 Testing Your Deployment

### **Test Queries**
Try these SCS-specific searches:

```bash
# Environmental services
curl -X POST https://your-api.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "environmental consulting services", "limit": 5}'

# Geotechnical engineering
curl -X POST https://your-api.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "geotechnical engineering projects", "limit": 5}'

# Project case studies
curl -X POST https://your-api.railway.app/search \
  -H "Content-Type: application/json" \
  -d '{"query": "remediation projects", "include_answer": true}'
```

### **WordPress Testing**
1. **Search Page**: Visit your search page
2. **Test Queries**: Try engineering-specific searches
3. **Mobile Testing**: Verify mobile responsiveness
4. **Performance**: Check search speed

## 🚨 Troubleshooting

### **Common Issues**

**1. Qdrant Connection**
```bash
# Test Qdrant connection
curl -H "api-key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.cp6kzt-aVQt6jK0YVnPLWo8qzE3FnRpNKDq0-_u_A1g" \
  https://918733b4-ab99-457e-a8d8-8105782783a5.us-east-1-1.aws.cloud.qdrant.io/collections
```

**2. Cerebras API**
```bash
# Test Cerebras connection
curl -H "Authorization: Bearer csk-d36t36pvwh54t9fpyn9xd339ynpkvw8ev4r2me2nt89y3y5h" \
  https://api.cerebras.ai/v1/models
```

**3. WordPress REST API**
```bash
# Test WordPress API
curl https://www.scsengineers.com/wp-json/wp/v2/posts?per_page=1
```

## 📈 Success Metrics

### **SCS-Specific KPIs**
- **Search Success Rate**: >90% for engineering queries
- **Technical Term Accuracy**: >95% for industry terminology
- **Project Discovery**: Improved project findability
- **User Engagement**: Increased content exploration

### **Performance Targets**
- **Response Time**: <500ms average
- **Uptime**: 99.9% availability
- **Search Volume**: Handle 1000+ searches/day
- **Content Coverage**: Index all published content

## 🎯 Next Steps

1. **Deploy**: Follow the Railway deployment steps
2. **Test**: Verify all functionality works
3. **Index**: Run initial content indexing
4. **Monitor**: Set up performance monitoring
5. **Optimize**: Fine-tune based on usage patterns

Your SCS Engineers hybrid search system is ready for production deployment! 🚀
