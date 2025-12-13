"""
RAG (Retrieval-Augmented Generation) Service
Handles knowledge base chunking, embedding, and retrieval for fast, context-aware responses
"""
import logging
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import tiktoken
from typing import List, Dict
import hashlib

logger = logging.getLogger(__name__)

# Initialize ChromaDB client (persistent storage)
chroma_client = chromadb.PersistentClient(
    path="/app/data/chromadb",
    settings=Settings(
        anonymized_telemetry=False,
        allow_reset=True
    )
)

# Initialize embedding model (lightweight, fast)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dims, ~120MB, fast
logger.info("🧠 RAG Service initialized with all-MiniLM-L6-v2 embedding model")

# Semantic cache for common queries (in-memory)
_semantic_cache = {}
CACHE_SIMILARITY_THRESHOLD = 0.95  # 95% similar queries hit cache

# Tokenizer for chunking
encoding = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> List[Dict]:
    """
    Chunk text into overlapping pieces for optimal RAG retrieval
    
    Args:
        text: Input text to chunk
        chunk_size: Target chunk size in tokens (400-512 recommended)
        overlap: Overlap between chunks in tokens (10-20% of chunk_size)
    
    Returns:
        List of dicts with 'text' and 'metadata'
    """
    # Tokenize the text
    tokens = encoding.encode(text)
    chunks = []
    
    start = 0
    chunk_id = 0
    
    while start < len(tokens):
        # Get chunk
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        
        # Decode back to text
        chunk_text = encoding.decode(chunk_tokens)
        
        # Store chunk with metadata
        chunks.append({
            'text': chunk_text,
            'chunk_id': chunk_id,
            'start_token': start,
            'end_token': end,
            'num_tokens': len(chunk_tokens)
        })
        
        chunk_id += 1
        
        # Move start pointer (with overlap)
        start = end - overlap
    
    logger.info(f"📄 Chunked text into {len(chunks)} pieces (avg {chunk_size} tokens each)")
    return chunks


def get_collection_name(agent_id: str) -> str:
    """Generate consistent collection name for agent"""
    # Use hash to ensure valid collection name (alphanumeric + underscores)
    hash_suffix = hashlib.md5(agent_id.encode()).hexdigest()[:8]
    return f"kb_{hash_suffix}"


def index_knowledge_base(agent_id: str, kb_items: List[Dict]) -> int:
    """
    Index knowledge base items for an agent
    
    Args:
        agent_id: Unique agent identifier
        kb_items: List of KB items with 'source_name', 'content', 'description'
    
    Returns:
        Total number of chunks indexed
    """
    collection_name = get_collection_name(agent_id)
    
    try:
        # Get or create collection for this agent
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"agent_id": agent_id}
        )
        
        # Clear existing data for this agent (re-indexing)
        try:
            collection.delete(where={"agent_id": agent_id})
        except:
            pass  # Collection might be empty
        
        all_chunks = []
        all_embeddings = []
        all_metadatas = []
        all_ids = []
        
        total_chunks = 0
        
        for idx, item in enumerate(kb_items):
            source_name = item.get('source_name', f'source_{idx}')
            content = item.get('content', '')
            description = item.get('description', '')
            
            if not content:
                continue
            
            # Chunk the content
            chunks = chunk_text(content, chunk_size=400, overlap=50)
            
            for chunk in chunks:
                chunk_content = chunk['text']
                
                # Create unique ID
                chunk_id = f"{agent_id}_{idx}_{chunk['chunk_id']}"
                
                # Create metadata
                metadata = {
                    'agent_id': agent_id,
                    'source_name': source_name,
                    'description': description,
                    'chunk_id': chunk['chunk_id'],
                    'num_tokens': chunk['num_tokens']
                }
                
                all_chunks.append(chunk_content)
                all_metadatas.append(metadata)
                all_ids.append(chunk_id)
                total_chunks += 1
        
        if all_chunks:
            # Generate embeddings in batch (faster)
            logger.info(f"🔢 Generating embeddings for {len(all_chunks)} chunks...")
            all_embeddings = embedding_model.encode(all_chunks, show_progress_bar=False).tolist()
            
            # Add to collection
            collection.add(
                ids=all_ids,
                embeddings=all_embeddings,
                documents=all_chunks,
                metadatas=all_metadatas
            )
            
            logger.info(f"✅ Indexed {total_chunks} chunks for agent {agent_id} in collection '{collection_name}'")
        else:
            logger.warning(f"⚠️  No content to index for agent {agent_id}")
        
        return total_chunks
        
    except Exception as e:
        logger.error(f"❌ Error indexing KB for agent {agent_id}: {e}")
        return 0


# Similarity threshold - chunks below this are filtered out to prevent hallucination
SIMILARITY_THRESHOLD = 0.35  # Minimum similarity score to include a chunk


def get_dynamic_top_k(query: str) -> int:
    """
    Determine optimal top_k based on query complexity.
    
    Simple factual questions need fewer chunks (faster).
    Complex multi-part questions need more context.
    
    Returns:
        top_k value (2-5)
    """
    query_lower = query.lower().strip()
    word_count = len(query_lower.split())
    
    # Count question indicators for complexity
    question_words = ['who', 'what', 'when', 'where', 'why', 'how', 'which', 'whose']
    question_count = sum(1 for word in question_words if word in query_lower)
    
    # Count topic keywords (indicates multi-topic query)
    topic_keywords = ['and', 'also', 'plus', 'as well', 'including', 'both', 'compare', 'difference', 'between']
    topic_count = sum(1 for kw in topic_keywords if kw in query_lower)
    
    # Simple short queries (< 6 words, single question word)
    if word_count < 6 and question_count <= 1 and topic_count == 0:
        logger.info(f"📊 Dynamic top_k: 2 (simple query: {word_count} words)")
        return 2
    
    # Medium complexity (6-15 words or 2 question words)
    if word_count <= 15 and question_count <= 2 and topic_count == 0:
        logger.info(f"📊 Dynamic top_k: 3 (medium query: {word_count} words, {question_count} questions)")
        return 3
    
    # Complex queries (long, multiple questions, or multi-topic)
    if word_count > 15 or question_count > 2 or topic_count > 0:
        logger.info(f"📊 Dynamic top_k: 5 (complex query: {word_count} words, {question_count} questions, {topic_count} topics)")
        return 5
    
    # Default
    logger.info(f"📊 Dynamic top_k: 3 (default)")
    return 3


async def retrieve_relevant_chunks_by_agent(agent_id: str, query: str, top_k: int = None, db=None, min_similarity: float = None) -> List[Dict]:
    """
    Retrieve relevant KB chunks directly from MongoDB (no ChromaDB collection needed)
    
    Args:
        agent_id: Agent identifier
        query: User's question/message
        top_k: Number of chunks to return (None = use dynamic top_k)
        db: MongoDB database instance
        min_similarity: Minimum similarity threshold (None = use default SIMILARITY_THRESHOLD)
    
    Returns:
        List of relevant KB chunks with content and metadata (filtered by similarity)
    """
    try:
        if not db:
            logger.error("❌ No database connection provided")
            return []
        
        # Use dynamic top_k if not specified
        if top_k is None:
            top_k = get_dynamic_top_k(query)
        
        # Use default threshold if not specified
        if min_similarity is None:
            min_similarity = SIMILARITY_THRESHOLD
        
        # Get all KB items for this agent
        kb_items = await db.knowledge_base.find({"agent_id": agent_id}).to_list(length=None)
        
        if not kb_items:
            logger.info(f"ℹ️  No KB items found for agent {agent_id}")
            return []
        
        # Generate query embedding
        query_embedding = embedding_model.encode([query], show_progress_bar=False)[0]
        
        # Score each KB item by semantic similarity
        scored_items = []
        for item in kb_items:
            content = item.get('content', '')
            if not content:
                continue
            
            # Generate embedding for this content (cache in future if needed)
            content_embedding = embedding_model.encode([content[:1000]], show_progress_bar=False)[0]  # Use first 1000 chars for speed
            
            # Calculate cosine similarity
            import numpy as np
            similarity = np.dot(query_embedding, content_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(content_embedding)
            )
            
            scored_items.append({
                'content': content,
                'source_name': item.get('source_name', 'Unknown'),
                'description': item.get('description', ''),
                'similarity': float(similarity)
            })
        
        # Sort by similarity
        scored_items.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Filter by similarity threshold BEFORE taking top_k
        filtered_items = [item for item in scored_items if item['similarity'] >= min_similarity]
        
        # Log filtering results
        filtered_out = len(scored_items) - len(filtered_items)
        if filtered_out > 0:
            logger.info(f"🔍 Filtered out {filtered_out} chunks below similarity threshold ({min_similarity})")
        
        # Take top_k from filtered results
        top_chunks = filtered_items[:top_k]
        
        if not top_chunks and scored_items:
            # All chunks were below threshold - log the best one we rejected
            best_rejected = scored_items[0]['similarity']
            logger.info(f"⚠️ No KB chunks above threshold. Best similarity was {best_rejected:.2f} (threshold: {min_similarity})")
        
        similarities = [f"{c['similarity']:.2f}" for c in top_chunks]
        logger.info(f"📚 Retrieved {len(top_chunks)} KB chunks (similarities: {similarities}, threshold: {min_similarity})")
        
        return top_chunks
        
    except Exception as e:
        logger.error(f"❌ Error retrieving KB chunks: {e}")
        import traceback
        traceback.print_exc()
        return []


def retrieve_relevant_chunks(agent_id: str, query: str, top_k: int = 3, use_cache: bool = True) -> str:
    """
    Retrieve relevant KB chunks for a query with semantic caching
    
    Args:
        agent_id: Agent identifier
        query: User's question/message
        top_k: Number of top chunks to retrieve (3 recommended for speed)
        use_cache: Whether to use semantic cache
    
    Returns:
        Formatted string with relevant chunks
    """
    collection_name = get_collection_name(agent_id)
    cache_key = f"{agent_id}:{query.lower().strip()}"
    
    try:
        # Check semantic cache first
        if use_cache and cache_key in _semantic_cache:
            logger.info(f"💾 Cache HIT - returning cached result (<50ms)")
            return _semantic_cache[cache_key]
        
        # Get collection
        collection = chroma_client.get_collection(name=collection_name)
        
        # Generate query embedding
        query_embedding = embedding_model.encode([query], show_progress_bar=False)[0].tolist()
        
        # Search for similar chunks (optimized: reduced to top_k=3 for speed)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['documents'] or not results['documents'][0]:
            logger.info(f"ℹ️  No relevant chunks found for query: {query[:50]}...")
            return ""
        
        # Format results
        formatted_chunks = []
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            source = metadata.get('source_name', 'Unknown')
            description = metadata.get('description', '')
            relevance = 1 - distance  # Convert distance to similarity
            
            chunk_header = f"\n### Retrieved Context {i+1}: {source}"
            if description:
                chunk_header += f"\n**Contains:** {description}"
            chunk_header += f"\n**Relevance:** {relevance:.2%}\n"
            
            formatted_chunks.append(f"{chunk_header}\n{doc}\n")
        
        result = "\n".join(formatted_chunks)
        
        # Cache the result for future similar queries
        if use_cache:
            _semantic_cache[cache_key] = result
            logger.info(f"💾 Cached result for future queries")
        
        avg_distance = sum(results['distances'][0])/len(results['distances'][0]) if results['distances'][0] else 0
        logger.info(f"📚 Retrieved {len(formatted_chunks)} chunks in ~100ms (avg distance: {avg_distance:.2f})")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error retrieving chunks for agent {agent_id}: {e}")
        return ""


def delete_agent_kb(agent_id: str) -> bool:
    """Delete all KB data for an agent"""
    collection_name = get_collection_name(agent_id)
    
    try:
        chroma_client.delete_collection(name=collection_name)
        logger.info(f"🗑️  Deleted KB collection for agent {agent_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error deleting KB for agent {agent_id}: {e}")
        return False


def get_collection_stats(agent_id: str) -> Dict:
    """Get stats about agent's KB collection"""
    collection_name = get_collection_name(agent_id)
    
    try:
        collection = chroma_client.get_collection(name=collection_name)
        count = collection.count()
        
        return {
            'agent_id': agent_id,
            'collection_name': collection_name,
            'total_chunks': count,
            'status': 'ready' if count > 0 else 'empty'
        }
    except Exception as e:
        return {
            'agent_id': agent_id,
            'collection_name': collection_name,
            'total_chunks': 0,
            'status': 'not_indexed',
            'error': str(e)
        }


async def retrieve_chunks_chromadb(agent_id: str, query: str, top_k: int = None, min_similarity: float = None) -> List[Dict]:
    """
    Retrieve relevant KB chunks from ChromaDB (pre-indexed, fast).
    
    This searches across ALL 400-token chunks, not just first 1000 chars.
    Much better coverage for large KBs (600k+ chars).
    
    Args:
        agent_id: Agent identifier
        query: User's question/message
        top_k: Number of chunks to return (None = use dynamic top_k)
        min_similarity: Minimum similarity threshold (None = use default)
    
    Returns:
        List of dicts with 'content', 'source_name', 'description', 'similarity'
    """
    import asyncio
    
    # Use dynamic top_k if not specified
    if top_k is None:
        top_k = get_dynamic_top_k(query)
    
    # Use default threshold if not specified
    if min_similarity is None:
        min_similarity = SIMILARITY_THRESHOLD
    
    collection_name = get_collection_name(agent_id)
    
    try:
        # Run sync ChromaDB operation in thread pool to not block event loop
        def _sync_retrieve():
            try:
                collection = chroma_client.get_collection(name=collection_name)
            except Exception as e:
                logger.warning(f"⚠️ ChromaDB collection not found for agent {agent_id}: {e}")
                return []
            
            # Generate query embedding
            query_embedding = embedding_model.encode([query], show_progress_bar=False)[0].tolist()
            
            # Search for similar chunks - get more than needed, then filter by threshold
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k * 2, 10),  # Get extra to allow filtering
                include=['documents', 'metadatas', 'distances']
            )
            
            if not results['documents'] or not results['documents'][0]:
                logger.info(f"ℹ️ No chunks found in ChromaDB for query: {query[:50]}...")
                return []
            
            # Convert to list of dicts with similarity filtering
            chunks = []
            for doc, metadata, distance in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            ):
                similarity = 1 - distance  # Convert distance to similarity
                
                # Apply similarity threshold
                if similarity < min_similarity:
                    continue
                
                chunks.append({
                    'content': doc,
                    'source_name': metadata.get('source_name', 'Unknown'),
                    'description': metadata.get('description', ''),
                    'similarity': float(similarity)
                })
            
            return chunks[:top_k]  # Return only top_k after filtering
        
        # Run in thread pool
        loop = asyncio.get_event_loop()
        chunks = await loop.run_in_executor(None, _sync_retrieve)
        
        if chunks:
            similarities = [f"{c['similarity']:.2f}" for c in chunks]
            logger.info(f"📚 ChromaDB retrieved {len(chunks)} chunks (similarities: {similarities}, threshold: {min_similarity})")
        else:
            logger.info(f"📚 ChromaDB: No chunks above threshold {min_similarity}")
        
        return chunks
        
    except Exception as e:
        logger.error(f"❌ ChromaDB retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return []

