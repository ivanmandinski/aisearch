# Hybrid Search System for WordPress

A comprehensive hybrid search system that combines dense and sparse retrieval to replace WordPress's native search functionality. This system uses state-of-the-art vector search, LLM-powered query processing, and seamless WordPress integration.

## 🏗️ Architecture

- **Qdrant**: Vector database for hybrid (dense + sparse) retrieval
- **LlamaIndex**: Orchestration layer for indexing and querying
- **Cerebras**: OpenAI-compatible LLM for query rewriting and answering
- **FastAPI**: REST API service with comprehensive endpoints
- **Railway**: Cloud deployment platform
- **WordPress Plugin**: Frontend integration with custom UI

## ✨ Features

- **Hybrid Search**: Combines semantic (dense) and keyword (sparse) retrieval for optimal results
- **LLM-Powered Query Processing**: Query rewriting, expansion, and answer generation
- **Real-time Indexing**: Automatic indexing of WordPress posts and pages
- **Advanced Filtering**: Search by categories, tags, authors, and content types
- **Relevance Scoring**: Intelligent scoring with visual indicators
- **AI-Generated Answers**: Contextual answers based on search results
- **Responsive Design**: Mobile-friendly search interface
- **RESTful API**: Comprehensive API for custom integrations

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- WordPress site with REST API enabled
- Cerebras API key
- Railway account (for deployment)

### Local Development

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd search
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Run with Docker**
   ```bash
   docker-compose up -d
   ```

4. **Or Run Locally**
   ```bash
   uvicorn main:app --reload
   ```

### WordPress Plugin Installation

1. **Upload Plugin**
   - Copy the `wordpress-plugin` folder to your WordPress `wp-content/plugins/` directory
   - Rename it to `hybrid-search`

2. **Activate Plugin**
   - Go to WordPress Admin → Plugins
   - Activate "Hybrid Search"

3. **Configure Settings**
   - Go to Settings → Hybrid Search
   - Enter your API URL and configuration
   - Test the connection

## 🔧 Configuration

### Environment Variables

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key_here
QDRANT_COLLECTION_NAME=wordpress_content

# Cerebras LLM Configuration
CEREBRAS_API_BASE=https://api.cerebras.ai/v1
CEREBRAS_API_KEY=your_cerebras_api_key_here
CEREBRAS_MODEL=cerebras-llama-2-7b-chat

# WordPress Configuration
WORDPRESS_URL=https://your-wordpress-site.com
WORDPRESS_USERNAME=your_wp_username
WORDPRESS_PASSWORD=your_wp_app_password
WORDPRESS_API_URL=https://your-wordpress-site.com/wp-json/wp/v2

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
MAX_SEARCH_RESULTS=10
SEARCH_TIMEOUT=30
EMBEDDING_DIMENSION=1536
```

### WordPress Setup

1. **Enable REST API**
   - Ensure WordPress REST API is enabled
   - Create an Application Password for API access

2. **Plugin Configuration**
   - Set API URL to your deployed service
   - Configure search preferences
   - Test the connection

## 🌐 API Endpoints

### Search
```http
POST /search
Content-Type: application/json

{
  "query": "your search query",
  "limit": 10,
  "include_answer": true,
  "filters": {
    "type": "post",
    "categories": ["technology"]
  }
}
```

### Index Content
```http
POST /index
Content-Type: application/json

{
  "force_reindex": false
}
```

### Health Check
```http
GET /health
```

### Statistics
```http
GET /stats
```

### Query Suggestions
```http
GET /suggest?query=partial&limit=5
```

## 🚀 Deployment

### Railway Deployment

1. **Connect Repository**
   - Connect your GitHub repository to Railway
   - Railway will auto-detect the Python project
   - Railway uses `requirements.txt` automatically

2. **Set Environment Variables**
   - Add all required environment variables in Railway dashboard
   - Use the values from `scs-production.env` file
   - Ensure Cerebras API key is set

3. **Deploy**
   - Railway will automatically build and deploy
   - Get your API URL from the deployment
   - **Note**: No `railway.toml` file needed - Railway uses automatic detection

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale hybrid-search-api=3
```

## 📊 Usage Examples

### Basic Search
```python
import requests

response = requests.post('https://your-api.railway.app/search', json={
    'query': 'machine learning tutorials',
    'limit': 5
})

results = response.json()
```

### Search with AI Answer
```python
response = requests.post('https://your-api.railway.app/search', json={
    'query': 'how to optimize WordPress performance',
    'include_answer': True,
    'limit': 3
})

data = response.json()
print(f"Answer: {data['answer']}")
print(f"Sources: {len(data['results'])}")
```

### Filtered Search
```python
response = requests.post('https://your-api.railway.app/search', json={
    'query': 'python programming',
    'filters': {
        'type': 'post',
        'categories': ['programming', 'tutorials']
    }
})
```

## 🔍 Search Features

### Hybrid Retrieval
- **Dense Vectors**: Semantic similarity using embeddings
- **Sparse Vectors**: Keyword matching with TF-IDF
- **Combined Scoring**: Weighted combination for optimal results

### Query Processing
- **Query Rewriting**: LLM-powered query optimization
- **Query Expansion**: Related terms and synonyms
- **Intent Classification**: Understanding search intent

### Result Enhancement
- **Relevance Scoring**: Visual score indicators
- **Content Highlighting**: Query term highlighting
- **AI Answers**: Contextual answers based on results

## 🛠️ Development

### Project Structure
```
search/
├── main.py                 # FastAPI application
├── config.py              # Configuration management
├── wordpress_client.py    # WordPress API client
├── qdrant_manager.py      # Qdrant vector database
├── llamaindex_orchestrator.py # LlamaIndex integration
├── cerebras_llm.py        # Cerebras LLM client
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Local development setup
├── railway.json          # Railway deployment config
└── wordpress-plugin/     # WordPress plugin files
    ├── hybrid-search.php
    ├── templates/
    └── assets/
```

### Adding Custom Features

1. **Custom Retrievers**: Extend `HybridRetriever` class
2. **Additional Filters**: Modify `_apply_filters` function
3. **Custom Scoring**: Update scoring algorithms in `QdrantManager`
4. **New Endpoints**: Add routes to `main.py`

### Testing

```bash
# Run tests
python -m pytest tests/

# Test API endpoints
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

## 🔧 Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check Cerebras API key
   - Verify API URL configuration
   - Test with `/health` endpoint

2. **WordPress Integration Issues**
   - Ensure REST API is enabled
   - Check application password
   - Verify plugin activation

3. **Search Results Empty**
   - Run content indexing: `POST /index`
   - Check Qdrant connection
   - Verify WordPress content exists

4. **Performance Issues**
   - Adjust `MAX_SEARCH_RESULTS`
   - Optimize embedding dimensions
   - Consider caching strategies

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

## 📈 Performance Optimization

### Scaling Considerations
- **Horizontal Scaling**: Multiple API instances
- **Caching**: Redis for frequent queries
- **CDN**: Static asset delivery
- **Database**: Qdrant cluster for large datasets

### Monitoring
- **Health Checks**: Built-in endpoint monitoring
- **Metrics**: Response times and error rates
- **Logging**: Comprehensive logging for debugging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Qdrant**: Vector database for hybrid search
- **LlamaIndex**: LLM application framework
- **Cerebras**: High-performance LLM inference
- **FastAPI**: Modern Python web framework
- **Railway**: Developer-friendly deployment platform
