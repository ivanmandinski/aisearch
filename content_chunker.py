"""
Content Chunking Module
Splits long documents into smaller chunks for better retrieval.
"""
import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)


class ContentChunker:
    """Split long documents into manageable chunks."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target chunk size in words
            overlap: Number of words to overlap between chunks (for context)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_document(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a document into chunks.
        
        Args:
            doc: Document dictionary with 'content', 'title', etc.
            
        Returns:
            List of chunk documents
        """
        try:
            content = doc.get('content', '')
            
            # If content is short enough, return as-is
            words = content.split()
            if len(words) <= self.chunk_size:
                return [doc]
            
            logger.info(f"Chunking document '{doc.get('title', 'unknown')}' ({len(words)} words)")
            
            chunks = []
            chunk_index = 0
            position = 0
            
            while position < len(words):
                # Extract chunk with overlap
                chunk_end = min(position + self.chunk_size, len(words))
                chunk_words = words[position:chunk_end]
                chunk_text = ' '.join(chunk_words)
                
                # Create chunk document
                chunk_doc = doc.copy()
                chunk_doc['id'] = f"{doc['id']}_chunk_{chunk_index}"
                chunk_doc['content'] = chunk_text
                chunk_doc['word_count'] = len(chunk_words)
                
                # Create context-aware excerpt
                chunk_doc['excerpt'] = self._create_chunk_excerpt(chunk_text, doc['title'])
                
                # Add chunk metadata
                chunk_doc['is_chunk'] = True
                chunk_doc['parent_id'] = doc['id']
                chunk_doc['chunk_index'] = chunk_index
                chunk_doc['total_chunks'] = (len(words) + self.chunk_size - 1) // self.chunk_size
                chunk_doc['chunk_start'] = position
                chunk_doc['chunk_end'] = chunk_end
                
                chunks.append(chunk_doc)
                
                # Move to next chunk with overlap
                position += self.chunk_size - self.overlap
                chunk_index += 1
            
            logger.info(f"Created {len(chunks)} chunks for document '{doc.get('title', 'unknown')}'")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking document: {e}")
            return [doc]  # Return original if chunking fails
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk multiple documents.
        
        Args:
            documents: List of documents
            
        Returns:
            List of documents and chunks
        """
        chunked_docs = []
        
        for doc in documents:
            chunks = self.chunk_document(doc)
            chunked_docs.extend(chunks)
        
        logger.info(f"Chunked {len(documents)} documents into {len(chunked_docs)} total chunks")
        return chunked_docs
    
    def _create_chunk_excerpt(self, chunk_text: str, title: str, max_length: int = 200) -> str:
        """Create a meaningful excerpt for a chunk."""
        # Try to find first complete sentence
        sentences = re.split(r'[.!?]+', chunk_text)
        
        excerpt = ''
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(excerpt) + len(sentence) < max_length:
                excerpt += sentence + '. '
            elif excerpt:
                break
        
        # If no complete sentences fit, just truncate
        if not excerpt:
            excerpt = chunk_text[:max_length]
        
        return excerpt.strip()
    
    def merge_chunk_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge chunks from the same parent document.
        
        Args:
            results: Search results that may include chunks
            
        Returns:
            Merged results with highest-scoring chunk per document
        """
        try:
            # Group by parent_id
            by_parent = {}
            standalone = []
            
            for result in results:
                if result.get('is_chunk'):
                    parent_id = result.get('parent_id', result['id'])
                    if parent_id not in by_parent:
                        by_parent[parent_id] = []
                    by_parent[parent_id].append(result)
                else:
                    standalone.append(result)
            
            # For each parent, keep only the highest-scoring chunk
            merged = standalone.copy()
            
            for parent_id, chunks in by_parent.items():
                # Sort chunks by score
                chunks.sort(key=lambda x: x.get('score', 0), reverse=True)
                best_chunk = chunks[0]
                
                # Modify to indicate it's from a chunked document
                best_chunk['chunk_info'] = {
                    'total_chunks': len(chunks),
                    'chunk_index': best_chunk.get('chunk_index', 0),
                    'all_chunks': [c['id'] for c in chunks]
                }
                
                merged.append(best_chunk)
            
            # Re-sort by score
            merged.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return merged
            
        except Exception as e:
            logger.error(f"Error merging chunks: {e}")
            return results  # Return original if merging fails
    
    def get_surrounding_chunks(
        self, 
        chunk_id: str, 
        all_results: List[Dict[str, Any]], 
        context_size: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Get surrounding chunks for context.
        
        Args:
            chunk_id: ID of the target chunk
            all_results: All search results
            context_size: Number of chunks before/after to include
            
        Returns:
            List of surrounding chunks in order
        """
        try:
            # Find the target chunk
            target = next((r for r in all_results if r['id'] == chunk_id), None)
            if not target or not target.get('is_chunk'):
                return []
            
            parent_id = target.get('parent_id')
            chunk_index = target.get('chunk_index', 0)
            
            # Find all chunks from same parent
            siblings = [
                r for r in all_results 
                if r.get('parent_id') == parent_id and r.get('is_chunk')
            ]
            
            # Sort by chunk_index
            siblings.sort(key=lambda x: x.get('chunk_index', 0))
            
            # Get surrounding chunks
            start_idx = max(0, chunk_index - context_size)
            end_idx = min(len(siblings), chunk_index + context_size + 1)
            
            return siblings[start_idx:end_idx]
            
        except Exception as e:
            logger.error(f"Error getting surrounding chunks: {e}")
            return []

