# Hybrid Search - AI-Powered Semantic Search for WordPress

<div align="center">

![Version](https://img.shields.io/badge/version-2.15.1-blue)
![Python](https://img.shields.io/badge/python-3.9+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-orange)
![License](https://img.shields.io/badge/license-GPL%20v2-blue)

**Enterprise-grade AI-powered search combining traditional keyword matching with modern semantic understanding**

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [API Reference](#api-reference) • [Contributing](#contributing)

</div>

---

## 🌟 Features

### Core Capabilities

- **🔍 Hybrid Search**: Combines TF-IDF keyword search with semantic vector search
- **🤖 AI Reranking**: Uses Cerebras LLM to intelligently rerank results based on relevance
- **💬 AI Answer Generation**: Generates comprehensive answers from search results
- **🔄 Query Expansion**: Automatically expands queries with synonyms and related terms
- **⚡ Real-time Indexing**: Supports instant document indexing and updates
- **🎯 Advanced Filtering**: Filter by post type, author, categories, and tags
- **📊 Analytics**: Built-in search analytics and click-through rate tracking
- **🚀 Performance**: Smart caching with variable TTL and gzip compression

### Technical Highlights

- **FastAPI Backend**: High-performance async API with automatic documentation
- **Qdrant Vector DB**: Scalable vector similarity search
- **Sentence Transformers**: Semantic embeddings for intelligent search
- **WordPress Integration**: Seamless WordPress plugin with real-time sync
- **Docker Support**: Containerized deployment ready for production
- **Comprehensive Error Handling**: Standardized error responses with detailed messages
- **Type Safety**: Full Python type hints for better code quality

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [WordPress Plugin](#wordpress-plugin)
- [Development](#development)
- [Deployment](#deployment)
- [Testing](#testing)
- [Performance](#performance)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🏗️ Architecture

```
┌─────────────────┐
│  WordPress Site │
│   (Frontend)    │
└────────┬────────┘
         │ REST API
         ▼
┌─────────────────┐
│  WordPress      │
│  Plugin         │────┐
└────────┬────────┘    │
         │ AJAX        │ Auto-Index
         ▼             │
┌─────────────────┐    │
│  FastAPI        │◄───┘
│  Backend        │
└────┬────────┬───┘
     │        │
     │        └──────────┐
     ▼                   ▼
┌──────────┐      ┌───────────┐
│ Qdrant   │      │ Cerebras  │
│ Vector DB│      │    LLM    │
└──────────┘      └───────────┘
```

### Components

1. **FastAPI Backend** (`main.py`): Handles search requests, indexing, and LLM operations
2. **WordPress Plugin** (`wordpress-plugin/`): Provides search UI and admin interface
3. **Qdrant Manager** (`qdrant_manager.py`): Manages vector database operations
4. **Cerebras LLM** (`cerebras_llm.py`): AI-powered query processing and answer generation
5. **Search Engine** (`simple_hybrid_search.py`): Core hybrid search logic

---

## 💻 Requirements

### Backend

- **Python**: 3.9 or higher
- **Dependencies**: See `requirements.txt`
  - FastAPI 0.104.1+
  - Qdrant Client 1.15.1+
  - OpenAI SDK 1.3.7+
  - scikit-learn 1.4.0+
  - httpx 0.25.2+

### WordPress

- **WordPress**: 5.0 or higher
- **PHP**: 7.4 or higher
- **MySQL**: 5.7+ or MariaDB 10.2+

### External Services

- **Qdrant**: Vector database (self-hosted or cloud)
- **Cerebras**: LLM API for AI features

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/hybrid-search.git
cd hybrid-search
```

### 2. Set Up Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your configuration
nano .env
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Qdrant (Docker)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 5. Run the API

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### 6. Install WordPress Plugin

1. Copy `wordpress-plugin/` to `wp-content/plugins/hybrid-search/`
2. Activate the plugin in WordPress admin
3. Configure API URL in plugin settings

### 7. Index Your Content

```bash
curl -X POST http://localhost:8000/index
```

### 8. Test Search

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test search", "limit": 10}'
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_COLLECTION_NAME=wordpress_content

# Cerebras LLM Configuration
CEREBRAS_API_KEY=your-cerebras-api-key
CEREBRAS_API_BASE=https://api.cerebras.ai/v1
CEREBRAS_MODEL=cerebras-llama-2-7b-chat

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your-openai-api-key

# WordPress Configuration
WORDPRESS_URL=https://your-site.com
WORDPRESS_USERNAME=your_wp_username
WORDPRESS_PASSWORD=your_wp_app_password
WORDPRESS_API_URL=https://your-site.com/wp-json/wp/v2

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_TITLE=Hybrid Search API
API_VERSION=2.15.1

# Search Configuration
MAX_SEARCH_RESULTS=100
SEARCH_TIMEOUT=30
EMBEDDING_DIMENSION=384
CHUNK_SIZE=1000

# AI Configuration
AI_INSTRUCTIONS=Provide comprehensive and accurate answers
STRICT_AI_ANSWER_MODE=true
```

### WordPress Plugin Settings

Navigate to **WordPress Admin → Settings → Hybrid Search**:

1. **API URL**: Your FastAPI backend URL
2. **Max Results**: Number of results to display (default: 10)
3. **Enable AI Answers**: Toggle AI-generated answers
4. **AI Instructions**: Custom instructions for AI
5. **Auto-Index**: Enable automatic indexing on post publish/update

---

## 📚 API Documentation

Full API documentation is available at:
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`
- **Detailed Guide**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

### Quick API Examples

**Search**:
```bash
POST /search
Content-Type: application/json

{
  "query": "wordpress plugins",
  "limit": 10,
  "include_answer": true,
  "enable_ai_reranking": true
}
```

**Index Content**:
```bash
POST /index
Content-Type: application/json

{
  "force_reindex": false,
  "post_types": ["post", "page"]
}
```

**Health Check**:
```bash
GET /health
```

---

## 🔧 Development

### Project Structure

```
hybrid-search/
├── main.py                     # FastAPI application entry point
├── config.py                   # Configuration management
├── constants.py                # Application constants
├── error_responses.py          # Error handling utilities
├── simple_hybrid_search.py     # Core search engine
├── cerebras_llm.py            # LLM integration
├── qdrant_manager.py          # Vector DB management
├── wordpress_client.py        # WordPress API client
├── input_validator.py         # Request validation
├── structured_logger.py       # Logging utilities
├── health_checker.py          # Health check utilities
├── content_chunker.py         # Document chunking
├── query_expander.py          # Query expansion
├── zero_result_handler.py     # Zero-result handling
├── suggestions.py             # Search suggestions
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── docker-compose.yml         # Docker Compose setup
└── wordpress-plugin/          # WordPress plugin
    ├── hybrid-search.php      # Plugin entry point
    ├── includes/              # PHP classes
    │   ├── API/              # API clients
    │   ├── Admin/            # Admin UI
    │   ├── AJAX/             # AJAX handlers
    │   ├── Core/             # Core functionality
    │   ├── Database/         # Database operations
    │   ├── Frontend/         # Frontend UI
    │   └── Services/         # Business logic
    ├── assets/               # CSS/JS assets
    └── templates/            # PHP templates
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest --cov=. tests/
```

### Code Quality

```bash
# Format code
black *.py

# Type checking
mypy *.py

# Linting
ruff check .
```

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build image
docker build -t hybrid-search:latest .

# Run container
docker run -d \
  --name hybrid-search \
  -p 8000:8000 \
  --env-file .env \
  hybrid-search:latest
```

### Docker Compose

```bash
docker-compose up -d
```

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Add environment variables in Railway dashboard
3. Deploy automatically on git push

### Production Checklist

- [ ] Set `API_HOST=0.0.0.0` for external access
- [ ] Configure proper CORS origins (not `*`)
- [ ] Enable HTTPS with SSL/TLS certificates
- [ ] Set up rate limiting
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerts
- [ ] Enable automatic backups
- [ ] Test disaster recovery procedures

---

## 🔐 Security

### Best Practices

1. **API Keys**: Store securely in environment variables
2. **CORS**: Restrict to specific domains
3. **Rate Limiting**: Implement per-IP rate limits
4. **Input Validation**: All inputs are validated and sanitized
5. **SQL Injection**: Use parameterized queries only
6. **XSS Protection**: HTML escaping on all output
7. **HTTPS**: Always use HTTPS in production

### Reporting Security Issues

Please report security vulnerabilities to: security@your-domain.com

---

## 🐛 Troubleshooting

### Common Issues

**Problem**: Search returns no results
- **Solution**: Check if content is indexed: `GET /stats`
- **Solution**: Verify Qdrant is running: `GET /health`

**Problem**: Slow search performance
- **Solution**: Enable caching in WordPress plugin settings
- **Solution**: Reduce `limit` parameter in search requests
- **Solution**: Disable AI reranking for faster results

**Problem**: API connection timeout
- **Solution**: Increase `SEARCH_TIMEOUT` in `.env`
- **Solution**: Check network connectivity to Qdrant and Cerebras

**Problem**: WordPress plugin not connecting to API
- **Solution**: Verify API URL in plugin settings
- **Solution**: Check CORS configuration in `main.py`
- **Solution**: Ensure API is accessible from WordPress server

### Debug Mode

Enable debug logging:

```python
# main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Logs

Check logs for errors:

```bash
# Application logs
tail -f logs/hybrid-search.log

# Docker logs
docker logs hybrid-search

# WordPress logs
wp-content/debug.log
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `pytest tests/`
5. Commit changes: `git commit -m "Add feature"`
6. Push to branch: `git push origin feature-name`
7. Open a Pull Request

### Code Standards

- Follow PEP 8 for Python code
- Use type hints for all functions
- Write comprehensive docstrings
- Add unit tests for new features
- Update documentation

---

## 📄 License

This project is licensed under the GPL v2 License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Qdrant**: Vector database engine
- **Cerebras**: Fast LLM inference
- **FastAPI**: Modern Python web framework
- **WordPress**: Content management system
- **Sentence Transformers**: Semantic embeddings

---

## 📞 Support

- **Documentation**: https://docs.hybrid-search.com
- **GitHub Issues**: https://github.com/your-org/hybrid-search/issues
- **Email**: support@your-domain.com
- **Discord**: https://discord.gg/hybrid-search

---

## 🗺️ Roadmap

### Version 2.16.0 (Q1 2024)

- [ ] Multi-language support
- [ ] Custom embedding models
- [ ] GraphQL API
- [ ] WebSocket support for real-time updates

### Version 3.0.0 (Q2 2024)

- [ ] Distributed architecture
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework
- [ ] Machine learning model fine-tuning

---

<div align="center">

**Made with ❤️ by the Hybrid Search Team**

[Website](https://hybrid-search.com) • [Twitter](https://twitter.com/hybridsearch) • [LinkedIn](https://linkedin.com/company/hybridsearch)

</div>

