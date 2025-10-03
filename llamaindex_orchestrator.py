"""
LlamaIndex orchestration for indexing and querying.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from llama_index import (
    Document, VectorStoreIndex, StorageContext, 
    Settings, SimpleDirectoryReader
)
from llama_index.node_parser import SentenceSplitter
from llama_index.retrievers import VectorIndexRetriever
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.schema import NodeWithScore
from llama_index.retrievers import BaseRetriever
from llama_index.query_engine import BaseQueryEngine
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from config import settings
from qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)


class HybridRetriever(BaseRetriever):
    """Custom hybrid retriever combining dense and sparse retrieval."""
    
    def __init__(
        self, 
        vector_store: QdrantVectorStore,
        qdrant_manager: QdrantManager,
        dense_weight: float = 0.7
    ):
        super().__init__()
        self.vector_store = vector_store
        self.qdrant_manager = qdrant_manager
        self.dense_weight = dense_weight
        self.sparse_weight = 1.0 - dense_weight
        
        # Initialize TF-IDF vectorizer for sparse retrieval
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.tfidf_matrix = None
        self.documents = []
    
    def _retrieve(self, query: str, **kwargs) -> List[NodeWithScore]:
        """Retrieve documents using hybrid approach."""
        try:
            # Get dense embedding for query
            query_embedding = self._get_query_embedding(query)
            
            # Get sparse vector for query
            sparse_vector = self._get_sparse_vector(query)
            
            # Perform hybrid search
            results = self.qdrant_manager.hybrid_search(
                query=query,
                dense_vector=query_embedding,
                sparse_vector=sparse_vector,
                limit=kwargs.get('limit', 10),
                alpha=self.dense_weight
            )
            
            # Convert to NodeWithScore format
            nodes = []
            for result in results:
                # Create document node
                doc = Document(
                    text=result['content'],
                    metadata={
                        'id': result['id'],
                        'title': result['title'],
                        'slug': result['slug'],
                        'type': result['type'],
                        'url': result['url'],
                        'date': result['date'],
                        'author': result['author'],
                        'categories': result['categories'],
                        'tags': result['tags'],
                        'excerpt': result['excerpt']
                    }
                )
                
                node = NodeWithScore(
                    node=doc,
                    score=result['score']
                )
                nodes.append(node)
            
            return nodes
            
        except Exception as e:
            logger.error(f"Error in hybrid retrieval: {e}")
            return []
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get dense embedding for query."""
        try:
            # Use OpenAI-compatible embedding
            embedding_model = OpenAIEmbedding(
                api_key=settings.cerebras_api_key,
                api_base=settings.cerebras_api_base,
                model="text-embedding-ada-002"
            )
            
            embedding = embedding_model.get_text_embedding(query)
            return embedding
            
        except Exception as e:
            logger.error(f"Error getting query embedding: {e}")
            return [0.0] * settings.embedding_dimension
    
    def _get_sparse_vector(self, query: str) -> Dict[int, float]:
        """Get sparse vector for query using TF-IDF."""
        try:
            if self.tfidf_matrix is None:
                return {}
            
            # Transform query using fitted TF-IDF
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Convert to dictionary format
            sparse_vector = {}
            for idx, value in zip(query_vector.indices, query_vector.data):
                sparse_vector[int(idx)] = float(value)
            
            return sparse_vector
            
        except Exception as e:
            logger.error(f"Error getting sparse vector: {e}")
            return {}
    
    def fit_tfidf(self, documents: List[str]):
        """Fit TF-IDF vectorizer on documents."""
        try:
            self.documents = documents
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
            logger.info(f"Fitted TF-IDF on {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error fitting TF-IDF: {e}")


class LlamaIndexOrchestrator:
    """Orchestrates LlamaIndex operations for indexing and querying."""
    
    def __init__(self):
        self.qdrant_manager = QdrantManager()
        self.vector_store = None
        self.index = None
        self.query_engine = None
        self.hybrid_retriever = None
        
        # Configure LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(
            api_key=settings.cerebras_api_key,
            api_base=settings.cerebras_api_base,
            model="text-embedding-ada-002"
        )
        
        Settings.llm = OpenAI(
            api_key=settings.cerebras_api_key,
            api_base=settings.cerebras_api_base,
            model=settings.cerebras_model,
            temperature=0.1
        )
    
    def setup_vector_store(self) -> bool:
        """Set up Qdrant vector store."""
        try:
            # Create collection if it doesn't exist
            self.qdrant_manager.create_collection()
            
            # Initialize vector store
            self.vector_store = QdrantVectorStore(
                client=self.qdrant_manager.client,
                collection_name=self.qdrant_manager.collection_name
            )
            
            logger.info("Vector store setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up vector store: {e}")
            return False
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Index documents using LlamaIndex."""
        try:
            if not self.vector_store:
                self.setup_vector_store()
            
            # Convert WordPress documents to LlamaIndex documents
            llama_docs = []
            document_texts = []
            
            for doc in documents:
                # Create LlamaIndex document
                llama_doc = Document(
                    text=f"{doc['title']}\n\n{doc['content']}",
                    metadata={
                        'id': doc['id'],
                        'title': doc['title'],
                        'slug': doc['slug'],
                        'type': doc['type'],
                        'url': doc['url'],
                        'date': doc['date'],
                        'modified': doc['modified'],
                        'author': doc['author'],
                        'categories': doc['categories'],
                        'tags': doc['tags'],
                        'excerpt': doc['excerpt'],
                        'word_count': doc['word_count']
                    }
                )
                llama_docs.append(llama_doc)
                document_texts.append(f"{doc['title']} {doc['content']}")
            
            # Create storage context
            storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
            
            # Create index
            self.index = VectorStoreIndex.from_documents(
                llama_docs,
                storage_context=storage_context,
                show_progress=True
            )
            
            # Set up hybrid retriever
            self.hybrid_retriever = HybridRetriever(
                vector_store=self.vector_store,
                qdrant_manager=self.qdrant_manager
            )
            
            # Fit TF-IDF for sparse retrieval
            self.hybrid_retriever.fit_tfidf(document_texts)
            
            # Create query engine
            self.query_engine = RetrieverQueryEngine.from_args(
                retriever=self.hybrid_retriever,
                response_mode="compact"
            )
            
            logger.info(f"Successfully indexed {len(documents)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            return False
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents using hybrid retrieval."""
        try:
            if not self.hybrid_retriever:
                logger.error("Hybrid retriever not initialized")
                return []
            
            # Perform hybrid search
            nodes = self.hybrid_retriever.retrieve(query, limit=limit)
            
            # Format results
            results = []
            for node in nodes:
                result = {
                    'id': node.node.metadata['id'],
                    'title': node.node.metadata['title'],
                    'slug': node.node.metadata['slug'],
                    'type': node.node.metadata['type'],
                    'url': node.node.metadata['url'],
                    'date': node.node.metadata['date'],
                    'author': node.node.metadata['author'],
                    'categories': node.node.metadata['categories'],
                    'tags': node.node.metadata['tags'],
                    'excerpt': node.node.metadata['excerpt'],
                    'content': node.node.text,
                    'score': node.score,
                    'relevance': self._calculate_relevance(node.score)
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def query_with_answer(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Query documents and generate an answer using LLM."""
        try:
            if not self.query_engine:
                logger.error("Query engine not initialized")
                return {}
            
            # Get search results
            search_results = self.search(query, limit=limit)
            
            # Generate answer using LLM
            response = self.query_engine.query(query)
            
            return {
                'query': query,
                'answer': str(response),
                'sources': search_results,
                'source_count': len(search_results)
            }
            
        except Exception as e:
            logger.error(f"Error querying with answer: {e}")
            return {}
    
    def _calculate_relevance(self, score: float) -> str:
        """Calculate relevance level based on score."""
        if score >= 0.8:
            return "high"
        elif score >= 0.6:
            return "medium"
        elif score >= 0.4:
            return "low"
        else:
            return "very_low"
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        try:
            collection_info = self.qdrant_manager.get_collection_info()
            return {
                'collection_name': self.qdrant_manager.collection_name,
                'total_documents': collection_info.get('points_count', 0),
                'indexed_vectors': collection_info.get('indexed_vectors_count', 0),
                'status': collection_info.get('status', 'unknown')
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {}
    
    def close(self):
        """Close the orchestrator."""
        if self.qdrant_manager:
            self.qdrant_manager.close()
